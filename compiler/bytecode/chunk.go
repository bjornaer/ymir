package bytecode

import "strconv"

// An Instr is one instruction. A is the operand, meaningful only for the
// opcodes Op.HasOperand reports.
//
// A struct rather than a packed byte stream: Go makes the struct as fast to
// dispatch on, and a listing that reads like the source is worth more in Phase 3
// than a compact encoding. Nothing serializes this — bytecode is produced and
// consumed in the same process.
type Instr struct {
	Op Op
	A  int32
}

// ConstKind tags a compile-time constant.
//
// Deliberately not vm.Value. The dependency runs vm -> bytecode, so the
// runtime's representation (resolved question R10) is the runtime's business;
// the VM converts a Const to a Value when it loads a program.
type ConstKind uint8

const (
	ConstInt ConstKind = iota
	ConstFloat
	ConstComplex
	ConstString
	ConstBool
)

// A Const is one entry in a chunk's constant pool.
type Const struct {
	Kind ConstKind
	I    int64   // ConstInt
	F    float64 // ConstFloat, and the real part of ConstComplex
	G    float64 // the imaginary part of ConstComplex
	S    string  // ConstString
	B    bool    // ConstBool
}

func (c Const) String() string {
	switch c.Kind {
	case ConstInt:
		return strconv.FormatInt(c.I, 10)
	case ConstFloat:
		return strconv.FormatFloat(c.F, 'g', -1, 64)
	case ConstComplex:
		return strconv.FormatFloat(c.F, 'g', -1, 64) + "+" +
			strconv.FormatFloat(c.G, 'g', -1, 64) + "i"
	case ConstString:
		return strconv.Quote(c.S)
	case ConstBool:
		return strconv.FormatBool(c.B)
	}
	return "?"
}

// A Chunk is a function's code, the lines it came from, and its constants.
//
// Lines is parallel to Code: Lines[i] is the source line of Code[i]. A panic
// walks it to build a stack trace, which chapter 06 §panic requires — legacy's
// CLI exited 0 and printed nothing, and this is the machinery that forecloses
// that.
type Chunk struct {
	Code   []Instr
	Lines  []int32
	Consts []Const
}

// Emit appends an instruction and returns its pc, which a caller patching a
// forward jump keeps.
func (c *Chunk) Emit(op Op, a int32, line int32) int {
	c.Code = append(c.Code, Instr{Op: op, A: a})
	c.Lines = append(c.Lines, line)
	return len(c.Code) - 1
}

// Patch rewrites the operand of an already-emitted instruction, for a forward
// jump whose target was not known when it was emitted.
func (c *Chunk) Patch(pc int, a int32) { c.Code[pc].A = a }

// Len is the number of instructions, and so the pc of the next one emitted.
func (c *Chunk) Len() int { return len(c.Code) }

// LineAt returns the source line of an instruction, or 0 when pc is out of
// range — which happens only for a corrupt frame, and reporting line 0 beats
// panicking inside a panic handler.
func (c *Chunk) LineAt(pc int) int32 {
	if pc < 0 || pc >= len(c.Lines) {
		return 0
	}
	return c.Lines[pc]
}

// AddConst interns a constant and returns its index. Interning keeps the pool
// small and makes a disassembly stable, which the tests depend on.
func (c *Chunk) AddConst(k Const) int32 {
	for i, existing := range c.Consts {
		if existing == k {
			return int32(i)
		}
	}
	c.Consts = append(c.Consts, k)
	return int32(len(c.Consts) - 1)
}

// A Function is one compiled function.
//
// Slots is how many local slots the frame needs, parameters included. Arity is
// fixed at compile time, so a call site does not encode it.
type Function struct {
	Name  string
	Arity int
	Slots int
	Chunk Chunk

	// Results is how many values the function returns, so the VM knows what to
	// leave on the stack. The error position, when there is one, is the last.
	Results int
}

// A Program is everything the VM needs to run.
type Program struct {
	File    string
	Funcs   []*Function
	Globals []string // module-level var names, in slot order

	// Main indexes Funcs, or is -1 when the module declares no main.
	Main int

	// Init indexes the synthetic function holding module-level `var`
	// initializers, or is -1 when there are none. The VM runs it before main.
	Init int

	// MainReturnsError records which of resolved question R9's two forms was
	// written. When true, a non-nil result is printed to stderr and the process
	// exits 1.
	MainReturnsError bool
}

func itoa(n int) string { return strconv.Itoa(n) }
