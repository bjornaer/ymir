package vm

import (
	"strings"
	"testing"

	"github.com/bjornaer/ymir/compiler/bytecode"
)

// runProgram executes a hand-built program and returns its stdout.
func runProgram(t *testing.T, p *bytecode.Program) (string, Value, error) {
	t.Helper()
	var out strings.Builder
	result, err := New(p, &out).Run()
	return out.String(), result, err
}

// mainWith builds a one-function program from a chunk builder.
func mainWith(results int, build func(c *bytecode.Chunk)) *bytecode.Program {
	fn := &bytecode.Function{Name: "main", Results: results}
	build(&fn.Chunk)
	return &bytecode.Program{
		File:             "t.ymr",
		Funcs:            []*bytecode.Function{fn},
		Main:             0,
		Init:             -1,
		MainReturnsError: results > 0,
	}
}

func TestPrintsConstants(t *testing.T) {
	p := mainWith(0, func(c *bytecode.Chunk) {
		c.Emit(bytecode.OpConst, c.AddConst(bytecode.Const{Kind: bytecode.ConstString, S: "main ran"}), 1)
		c.Emit(bytecode.OpPrint, 1, 1)
		c.Emit(bytecode.OpReturn, 0, 2)
	})
	out, _, err := runProgram(t, p)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	if out != "main ran\n" {
		t.Errorf("stdout = %q, want %q", out, "main ran\n")
	}
}

func TestPrintIsVariadicAndSpaceSeparated(t *testing.T) {
	p := mainWith(0, func(c *bytecode.Chunk) {
		c.Emit(bytecode.OpConst, c.AddConst(bytecode.Const{Kind: bytecode.ConstInt, I: 1}), 1)
		c.Emit(bytecode.OpConst, c.AddConst(bytecode.Const{Kind: bytecode.ConstString, S: "x"}), 1)
		c.Emit(bytecode.OpPrint, 2, 1)
		c.Emit(bytecode.OpReturn, 0, 2)
	})
	out, _, err := runProgram(t, p)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	if out != "1 x\n" {
		t.Errorf("stdout = %q, want %q", out, "1 x\n")
	}
}

func TestMainReturningAnErrorSurfacesIt(t *testing.T) {
	// R9's second form: the result reaches the caller, which prints it to
	// stderr and exits 1.
	p := mainWith(1, func(c *bytecode.Chunk) {
		c.Emit(bytecode.OpConst, c.AddConst(bytecode.Const{Kind: bytecode.ConstString, S: "boom"}), 1)
		c.Emit(bytecode.OpReturn, 1, 1)
	})
	_, result, err := runProgram(t, p)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	if result.IsNil() {
		t.Fatal("main's error result was lost")
	}
	if got := result.Display(); got != "boom" {
		t.Errorf("result = %q, want %q", got, "boom")
	}

	// And returning nil is the success path.
	p = mainWith(1, func(c *bytecode.Chunk) {
		c.Emit(bytecode.OpNil, 0, 1)
		c.Emit(bytecode.OpReturn, 1, 1)
	})
	_, result, err = runProgram(t, p)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	if !result.IsNil() {
		t.Errorf("returning nil produced %s, want nil", result.Display())
	}
}

func TestPanicCarriesAStackTrace(t *testing.T) {
	// Chapter 06 §panic: the message and a stack trace to stderr, non-zero
	// exit. Legacy exited 0 and printed nothing.
	p := mainWith(0, func(c *bytecode.Chunk) {
		c.Emit(bytecode.OpConst, c.AddConst(bytecode.Const{Kind: bytecode.ConstString, S: "deliberate"}), 7)
		c.Emit(bytecode.OpPanic, 0, 7)
	})
	_, _, err := runProgram(t, p)
	if err == nil {
		t.Fatal("expected a panic")
	}
	var pan *Panic
	if !asPanic(err, &pan) {
		t.Fatalf("error is %T, want *vm.Panic", err)
	}
	if pan.Msg != "deliberate" {
		t.Errorf("message = %q, want %q", pan.Msg, "deliberate")
	}
	if len(pan.Trace) != 1 || pan.Trace[0].Func != "main" {
		t.Fatalf("trace = %+v, want one frame in main", pan.Trace)
	}
	if pan.Trace[0].Line != 7 {
		t.Errorf("trace line = %d, want 7", pan.Trace[0].Line)
	}

	var rendered strings.Builder
	pan.Report(&rendered, "t.ymr")
	for _, want := range []string{"panic: deliberate", "main (t.ymr:7)"} {
		if !strings.Contains(rendered.String(), want) {
			t.Errorf("report does not contain %q:\n%s", want, rendered.String())
		}
	}
}

func TestMissingMainIsAnError(t *testing.T) {
	p := &bytecode.Program{File: "t.ymr", Main: -1, Init: -1}
	if _, _, err := runProgram(t, p); err == nil {
		t.Error("a program with no main must fail rather than silently succeed")
	}
}

func asPanic(err error, target **Panic) bool {
	p, ok := err.(*Panic)
	if ok {
		*target = p
	}
	return ok
}

func TestValueDisplay(t *testing.T) {
	// print and str() output is observable behaviour the conformance suite
	// asserts, so it is part of the language.
	tests := []struct {
		v    Value
		want string
	}{
		{Nil(), "nil"},
		{Bool(true), "true"},
		{Bool(false), "false"},
		{Int(-7), "-7"},
		{Float(3.5), "3.5"},
		// A whole float keeps its point, or a float and an int would be
		// indistinguishable in output.
		{Float(4), "4.0"},
		{Complex(1, 2), "1.0+2.0i"},
		{Complex(1, -2), "1.0-2.0i"},
		{Str("hi"), "hi"},
	}
	for _, tc := range tests {
		if got := tc.v.Display(); got != tc.want {
			t.Errorf("Display() = %q, want %q", got, tc.want)
		}
	}
}

func TestEquality(t *testing.T) {
	// Chapter 04: == is defined on any unrestricted type; float equality is
	// IEEE, so nan != nan.
	nan := Float(0)
	nan.F = nan.F / zero()

	tests := []struct {
		a, b Value
		want bool
	}{
		{Int(1), Int(1), true},
		{Int(1), Int(2), false},
		{Float(1.5), Float(1.5), true},
		{Str("a"), Str("a"), true},
		{Str("a"), Str("b"), false},
		{Bool(true), Bool(true), true},
		{Nil(), Nil(), true},
		{Nil(), Int(0), false},
		{Int(1), Float(1), false}, // different kinds never compare equal
		{nan, nan, false},
	}
	for _, tc := range tests {
		if got := Equal(tc.a, tc.b); got != tc.want {
			t.Errorf("Equal(%s, %s) = %v, want %v", tc.a.Display(), tc.b.Display(), got, tc.want)
		}
	}
}

func zero() float64 { return 0 }
