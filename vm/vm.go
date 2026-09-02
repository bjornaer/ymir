package vm

import (
	"fmt"
	"io"
	"strings"

	"github.com/bjornaer/ymir/compiler/bytecode"
)

// The machine.
//
// A stack of Values, a stack of frames, and a switch. Nothing clever: Phase 3
// exists to make the semantics real, and every trick makes a divergence between
// what the spec says and what runs harder to see.

// A Panic is a runtime failure that chapter 06 §panic enumerates: an index out
// of range, a map miss, integer division by zero, an overflow (R5), a send on a
// closed channel. It is not catchable — Ymir has no recover.
type Panic struct {
	Msg   string
	Trace []Frame
}

func (p *Panic) Error() string { return p.Msg }

// A Frame names one level of a stack trace.
type Frame struct {
	Func string
	Line int32
}

// Report writes the message and the stack trace the way the runtime does.
//
// "A panic MUST write the message and a stack trace to stderr and exit with a
// non-zero status." Legacy's CLI exited 0 unconditionally, which made its CI
// structurally incapable of failing; this is the machinery that forecloses it.
func (p *Panic) Report(w io.Writer, file string) {
	var b strings.Builder
	fmt.Fprintf(&b, "panic: %s\n", p.Msg)
	for _, f := range p.Trace {
		fmt.Fprintf(&b, "\t%s (%s:%d)\n", f.Func, file, f.Line)
	}
	io.WriteString(w, b.String())
}

// A frame is one active call.
type frame struct {
	fn   *bytecode.Function
	pc   int
	base int // index in the value stack of this frame's slot 0
}

// VM executes one program.
type VM struct {
	prog    *bytecode.Program
	stack   []Value
	frames  []frame
	globals []Value
	out     io.Writer
}

// New returns a VM that writes program output to out.
func New(prog *bytecode.Program, out io.Writer) *VM {
	return &VM{
		prog:    prog,
		stack:   make([]Value, 0, 256),
		globals: make([]Value, len(prog.Globals)),
		out:     out,
	}
}

// Run executes the program's entry point.
//
// The returned Value is main's error result under resolved question R9's second
// form, and Nil otherwise. A *Panic means the program failed at runtime.
func (v *VM) Run() (Value, error) {
	if v.prog.Main < 0 {
		return Nil(), fmt.Errorf("no main function in module %s", v.prog.File)
	}

	// Module-level `var` initializers run before main. Without this a global
	// holds the zero Value and a program can look correct while its initializer
	// never ran.
	if v.prog.Init >= 0 {
		v.frames = append(v.frames, frame{fn: v.prog.Funcs[v.prog.Init], base: 0})
		if err := v.run(); err != nil {
			return Nil(), err
		}
		v.stack = v.stack[:0]
	}

	main := v.prog.Funcs[v.prog.Main]
	v.frames = append(v.frames, frame{fn: main, base: 0})

	if err := v.run(); err != nil {
		return Nil(), err
	}

	// `func main() -> ?error` leaves its result on the stack; `func main()`
	// leaves nothing.
	if v.prog.MainReturnsError && len(v.stack) > 0 {
		return v.stack[len(v.stack)-1], nil
	}
	return Nil(), nil
}

func (v *VM) run() error {
	for {
		f := &v.frames[len(v.frames)-1]
		if f.pc >= len(f.fn.Chunk.Code) {
			// Falling off the end of a chunk is a compiler bug: every function
			// is emitted with a trailing Return.
			return v.panicf("internal: ran past the end of %s", f.fn.Name)
		}

		in := f.fn.Chunk.Code[f.pc]
		f.pc++

		switch in.Op {
		case bytecode.OpNop:
			// nothing

		case bytecode.OpConst:
			v.push(valueOf(f.fn.Chunk.Consts[in.A]))

		case bytecode.OpNil:
			v.push(Nil())
		case bytecode.OpTrue:
			v.push(Bool(true))
		case bytecode.OpFalse:
			v.push(Bool(false))

		case bytecode.OpPop:
			v.pop()

		case bytecode.OpGetLocal:
			v.push(v.stack[f.base+int(in.A)])

		case bytecode.OpSetLocal:
			v.stack[f.base+int(in.A)] = v.pop()

		case bytecode.OpGetGlobal:
			v.push(v.globals[in.A])

		case bytecode.OpSetGlobal:
			v.globals[in.A] = v.pop()

		case bytecode.OpJump:
			f.pc = int(in.A)

		case bytecode.OpJumpIfFalse:
			if !v.pop().IsTrue() {
				f.pc = int(in.A)
			}

		case bytecode.OpJumpIfTrue:
			if v.pop().IsTrue() {
				f.pc = int(in.A)
			}

		case bytecode.OpPrint:
			if err := v.doPrint(int(in.A)); err != nil {
				return err
			}

		case bytecode.OpPanic:
			msg := v.pop()
			return v.newPanic(msg.Display())

		case bytecode.OpCall:
			callee := v.prog.Funcs[in.A]
			// Arguments are already on the stack, in order, and become the
			// callee's first slots. Later locals push themselves as they are
			// declared, so the stack always holds exactly the frame's live
			// locals — the invariant the compiler's endScope maintains.
			base := len(v.stack) - callee.Arity
			v.frames = append(v.frames, frame{fn: callee, base: base})

		case bytecode.OpReturn:
			if done, err := v.doReturn(int(in.A)); done || err != nil {
				return err
			}

		case bytecode.OpHalt:
			return nil

		default:
			// Arithmetic, comparison and logic live in arith.go, which reports
			// whether it recognized the opcode.
			handled, err := v.arith(in.Op)
			if err != nil {
				return err
			}
			if !handled {
				return v.panicf("internal: unimplemented opcode %s", in.Op)
			}
		}
	}
}

// doReturn pops the frame, moving the returned values down over its slots.
// It reports done when the outermost frame returned.
func (v *VM) doReturn(n int) (bool, error) {
	f := v.frames[len(v.frames)-1]
	v.frames = v.frames[:len(v.frames)-1]

	results := make([]Value, n)
	copy(results, v.stack[len(v.stack)-n:])

	// Discard the whole frame, arguments and locals alike, then push results.
	v.stack = v.stack[:f.base]
	v.stack = append(v.stack, results...)

	return len(v.frames) == 0, nil
}

func (v *VM) doPrint(argc int) error {
	args := v.stack[len(v.stack)-argc:]
	parts := make([]string, argc)
	for i, a := range args {
		parts[i] = a.Display()
	}
	v.stack = v.stack[:len(v.stack)-argc]

	// print is variadic and separates with a space, which chapter 04 calls a
	// wart to be removed once generics land.
	if _, err := fmt.Fprintln(v.out, strings.Join(parts, " ")); err != nil {
		return err
	}
	return nil
}

// ---------------------------------------------------------------------------
// Stack

func (v *VM) push(x Value) { v.stack = append(v.stack, x) }

func (v *VM) pop() Value {
	x := v.stack[len(v.stack)-1]
	v.stack = v.stack[:len(v.stack)-1]
	return x
}

// ---------------------------------------------------------------------------
// Panics

func (v *VM) panicf(format string, args ...any) error {
	return v.newPanic(fmt.Sprintf(format, args...))
}

// newPanic captures the stack trace at the point of failure.
func (v *VM) newPanic(msg string) error {
	p := &Panic{Msg: msg}
	for i := len(v.frames) - 1; i >= 0; i-- {
		f := v.frames[i]
		// pc has already advanced past the failing instruction.
		p.Trace = append(p.Trace, Frame{
			Func: f.fn.Name,
			Line: f.fn.Chunk.LineAt(f.pc - 1),
		})
	}
	return p
}

// valueOf converts a compile-time constant into a runtime value. This is the
// one place the two representations meet.
func valueOf(k bytecode.Const) Value {
	switch k.Kind {
	case bytecode.ConstInt:
		return Int(k.I)
	case bytecode.ConstFloat:
		return Float(k.F)
	case bytecode.ConstComplex:
		return Complex(k.F, k.G)
	case bytecode.ConstString:
		return Str(k.S)
	case bytecode.ConstBool:
		return Bool(k.B)
	}
	return Nil()
}
