package bytecode

import (
	"strings"
	"testing"
)

func TestOpNamesAreComplete(t *testing.T) {
	// A missing name is a bug that would otherwise surface as an unreadable
	// disassembly at the worst possible moment. OpHalt is the last opcode, so
	// every value up to it must be named.
	for op := OpNop; op <= OpHalt; op++ {
		if got := op.String(); strings.HasPrefix(got, "Op(") {
			t.Errorf("opcode %d has no name", op)
		}
	}
	// And nothing past it should be named, so the loop bound above stays
	// honest as opcodes are added.
	if got := (OpHalt + 1).String(); !strings.HasPrefix(got, "Op(") {
		t.Errorf("Op(%d) is named %q, but OpHalt is meant to be the last opcode",
			OpHalt+1, got)
	}
}

func TestOperandClassification(t *testing.T) {
	withOperand := []Op{
		OpConst, OpGetLocal, OpSetLocal, OpGetGlobal, OpSetGlobal,
		OpJump, OpJumpIfFalse, OpCall, OpPrint,
	}
	want := map[Op]bool{}
	for _, op := range withOperand {
		want[op] = true
	}
	for op := OpNop; op <= OpHalt; op++ {
		if op.HasOperand() != want[op] {
			t.Errorf("%s.HasOperand() = %v, want %v", op, op.HasOperand(), want[op])
		}
	}

	if !OpJump.IsJump() || !OpJumpIfFalse.IsJump() {
		t.Error("the jump opcodes must report themselves as jumps")
	}
	if OpCall.IsJump() {
		t.Error("Call is not a jump: its operand is a function index, not a pc")
	}
}

func TestConstantsAreInterned(t *testing.T) {
	var c Chunk
	a := c.AddConst(Const{Kind: ConstInt, I: 7})
	b := c.AddConst(Const{Kind: ConstInt, I: 7})
	d := c.AddConst(Const{Kind: ConstInt, I: 8})

	if a != b {
		t.Errorf("equal constants got indices %d and %d; the pool must intern", a, b)
	}
	if a == d {
		t.Error("different constants must get different indices")
	}
	if len(c.Consts) != 2 {
		t.Errorf("pool holds %d constants, want 2", len(c.Consts))
	}

	// A float and an int of the same numeric value are different constants.
	e := c.AddConst(Const{Kind: ConstFloat, F: 7})
	if e == a {
		t.Error("an int and a float constant must not intern together")
	}
}

func TestEmitAndPatch(t *testing.T) {
	var c Chunk
	jump := c.Emit(OpJumpIfFalse, -1, 3)
	c.Emit(OpNil, 0, 4)
	target := c.Len()
	c.Emit(OpReturn, 0, 5)

	if jump != 0 {
		t.Errorf("first Emit returned pc %d, want 0", jump)
	}
	c.Patch(jump, int32(target))
	if got := c.Code[jump].A; got != int32(target) {
		t.Errorf("after Patch the operand is %d, want %d", got, target)
	}
	if got := c.LineAt(jump); got != 3 {
		t.Errorf("line of pc 0 is %d, want 3", got)
	}
	// A pc past the end must not panic: a corrupt frame should not take down
	// the panic handler that is trying to report it.
	if got := c.LineAt(999); got != 0 {
		t.Errorf("LineAt out of range = %d, want 0", got)
	}
}

func TestDisassembly(t *testing.T) {
	fn := &Function{Name: "main", Arity: 0, Slots: 0}
	msg := fn.Chunk.AddConst(Const{Kind: ConstString, S: "main ran"})
	fn.Chunk.Emit(OpConst, msg, 8)
	fn.Chunk.Emit(OpPrint, 1, 8)
	fn.Chunk.Emit(OpReturn, 0, 9)

	p := &Program{File: "t.ymr", Funcs: []*Function{fn}, Main: 0}

	var out strings.Builder
	if err := p.Disassemble(&out); err != nil {
		t.Fatalf("Disassemble: %v", err)
	}
	got := out.String()

	for _, want := range []string{
		"func main/0",
		"; entry point",
		`Const`,
		`; "main ran"`,
		"Print",
		"Return",
	} {
		if !strings.Contains(got, want) {
			t.Errorf("listing does not contain %q:\n%s", want, got)
		}
	}

	// The line column repeats only when the line changes, so consecutive
	// instructions from one source line read as a group.
	if strings.Count(got, "     8  ") != 1 {
		t.Errorf("line 8 should be printed once, then elided:\n%s", got)
	}
	if !strings.Contains(got, "|  Print") {
		t.Errorf("the second instruction on line 8 should show the elision bar:\n%s", got)
	}
}

func TestDisassemblyReportsDanglingIndices(t *testing.T) {
	// A bad index is a compiler bug. The listing must say so rather than print
	// a bare number that reads as fine.
	fn := &Function{Name: "broken"}
	fn.Chunk.Emit(OpConst, 99, 1)
	fn.Chunk.Emit(OpGetGlobal, 99, 1)
	fn.Chunk.Emit(OpCall, 99, 1)
	p := &Program{Funcs: []*Function{fn}, Main: -1}

	var out strings.Builder
	if err := p.Disassemble(&out); err != nil {
		t.Fatalf("Disassemble: %v", err)
	}
	for _, want := range []string{"<no such constant>", "<no such global>", "<no such function>"} {
		if !strings.Contains(out.String(), want) {
			t.Errorf("listing does not contain %q:\n%s", want, out.String())
		}
	}
}

func TestDisassemblyShowsGlobalsAndJumpTargets(t *testing.T) {
	fn := &Function{Name: "f"}
	fn.Chunk.Emit(OpGetGlobal, 0, 2)
	fn.Chunk.Emit(OpJumpIfFalse, 4, 2)
	fn.Chunk.Emit(OpReturn, 0, 3)

	p := &Program{Funcs: []*Function{fn}, Globals: []string{"total"}, Main: -1}

	var out strings.Builder
	if err := p.Disassemble(&out); err != nil {
		t.Fatalf("Disassemble: %v", err)
	}
	got := out.String()
	for _, want := range []string{"globals:", "total", "; total", "; -> 0004"} {
		if !strings.Contains(got, want) {
			t.Errorf("listing does not contain %q:\n%s", want, got)
		}
	}
}

func TestConstString(t *testing.T) {
	tests := []struct {
		c    Const
		want string
	}{
		{Const{Kind: ConstInt, I: -7}, "-7"},
		{Const{Kind: ConstFloat, F: 3.5}, "3.5"},
		{Const{Kind: ConstComplex, F: 1, G: 2}, "1+2i"},
		{Const{Kind: ConstString, S: "a\nb"}, `"a\nb"`},
		{Const{Kind: ConstBool, B: true}, "true"},
	}
	for _, tc := range tests {
		if got := tc.c.String(); got != tc.want {
			t.Errorf("Const.String() = %q, want %q", got, tc.want)
		}
	}
}
