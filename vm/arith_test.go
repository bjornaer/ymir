package vm

import (
	"strings"
	"testing"

	"github.com/bjornaer/ymir/compiler/bytecode"
)

// binOp runs one binary opcode over two constants and returns the result.
func binOp(t *testing.T, op bytecode.Op, a, b bytecode.Const) (Value, error) {
	t.Helper()
	p := mainWith(1, func(c *bytecode.Chunk) {
		c.Emit(bytecode.OpConst, c.AddConst(a), 1)
		c.Emit(bytecode.OpConst, c.AddConst(b), 1)
		c.Emit(op, 0, 1)
		c.Emit(bytecode.OpReturn, 1, 1)
	})
	_, result, err := runProgram(t, p)
	return result, err
}

func ci(n int64) bytecode.Const   { return bytecode.Const{Kind: bytecode.ConstInt, I: n} }
func cf(f float64) bytecode.Const { return bytecode.Const{Kind: bytecode.ConstFloat, F: f} }
func cs(s string) bytecode.Const  { return bytecode.Const{Kind: bytecode.ConstString, S: s} }

func TestIntArithmetic(t *testing.T) {
	tests := []struct {
		op   bytecode.Op
		a, b int64
		want int64
	}{
		{bytecode.OpAddInt, 2, 3, 5},
		{bytecode.OpSubInt, 2, 3, -1},
		{bytecode.OpMulInt, 4, 5, 20},
		// "/ on int is truncating integer division. 7 / 2 is 3, not 3.5."
		{bytecode.OpDivInt, 7, 2, 3},
		{bytecode.OpDivInt, -7, 2, -3},
		// "% takes the sign of the dividend (-7 % 3 is -1)."
		{bytecode.OpModInt, -7, 3, -1},
		{bytecode.OpModInt, 7, 3, 1},
		{bytecode.OpPowInt, 2, 10, 1024},
		{bytecode.OpPowInt, 2, 0, 1},
	}
	for _, tc := range tests {
		got, err := binOp(t, tc.op, ci(tc.a), ci(tc.b))
		if err != nil {
			t.Errorf("%s(%d, %d): %v", tc.op, tc.a, tc.b, err)
			continue
		}
		if got.Kind != KindInt || got.N != tc.want {
			t.Errorf("%s(%d, %d) = %s, want %d", tc.op, tc.a, tc.b, got.Display(), tc.want)
		}
	}
}

func TestIntOverflowTraps(t *testing.T) {
	// R5: "Arithmetic on int that overflows the signed 64-bit range MUST panic.
	// It MUST NOT wrap and MUST NOT saturate — both produce a silently wrong
	// answer." Wrapping here is the exact defect class the rewrite exists for.
	const maxInt = int64(9223372036854775807)
	const minInt = -maxInt - 1

	tests := []struct {
		name string
		op   bytecode.Op
		a, b int64
	}{
		{"add", bytecode.OpAddInt, maxInt, 1},
		{"add negative", bytecode.OpAddInt, minInt, -1},
		{"sub", bytecode.OpSubInt, minInt, 1},
		{"mul", bytecode.OpMulInt, maxInt, 2},
		{"mul min by -1", bytecode.OpMulInt, minInt, -1},
		{"div min by -1", bytecode.OpDivInt, minInt, -1},
		{"pow", bytecode.OpPowInt, 2, 64},
	}
	for _, tc := range tests {
		_, err := binOp(t, tc.op, ci(tc.a), ci(tc.b))
		if err == nil {
			t.Errorf("%s: overflow was not trapped", tc.name)
			continue
		}
		if !strings.Contains(err.Error(), "integer overflow") {
			t.Errorf("%s: panicked with %q, want an overflow message", tc.name, err)
		}
	}
}

func TestIntDivisionByZeroPanics(t *testing.T) {
	// Chapter 06 §panic lists integer division and modulo by zero.
	for _, op := range []bytecode.Op{bytecode.OpDivInt, bytecode.OpModInt} {
		_, err := binOp(t, op, ci(1), ci(0))
		if err == nil {
			t.Errorf("%s by zero did not panic", op)
			continue
		}
		if !strings.Contains(err.Error(), "by zero") {
			t.Errorf("%s by zero panicked with %q", op, err)
		}
	}
}

func TestFloatArithmeticIsIEEE(t *testing.T) {
	got, err := binOp(t, bytecode.OpDivFloat, cf(7), cf(2))
	if err != nil {
		t.Fatalf("float division: %v", err)
	}
	if got.F != 3.5 {
		t.Errorf("7.0 / 2.0 = %s, want 3.5", got.Display())
	}

	// "float division by zero yields IEEE infinity and does not panic."
	got, err = binOp(t, bytecode.OpDivFloat, cf(1), cf(0))
	if err != nil {
		t.Fatalf("float division by zero panicked: %v", err)
	}
	if !strings.Contains(got.Display(), "Inf") {
		t.Errorf("1.0 / 0.0 = %s, want an infinity", got.Display())
	}

	// And a float overflow does not trap either: R5 is about int.
	got, err = binOp(t, bytecode.OpMulFloat, cf(1e308), cf(10))
	if err != nil {
		t.Fatalf("float overflow panicked: %v", err)
	}
	if !strings.Contains(got.Display(), "Inf") {
		t.Errorf("1e308 * 10 = %s, want an infinity", got.Display())
	}
}

func TestStringConcatAndComparison(t *testing.T) {
	got, err := binOp(t, bytecode.OpConcat, cs("a"), cs("b"))
	if err != nil {
		t.Fatalf("concat: %v", err)
	}
	if got.String() != "ab" {
		t.Errorf(`"a" + "b" = %q, want "ab"`, got.String())
	}

	got, _ = binOp(t, bytecode.OpLtString, cs("a"), cs("b"))
	if !got.IsTrue() {
		t.Error(`"a" < "b" should be true`)
	}
}

func TestComparisonYieldsBool(t *testing.T) {
	got, err := binOp(t, bytecode.OpLtInt, ci(1), ci(2))
	if err != nil {
		t.Fatalf("comparison: %v", err)
	}
	if got.Kind != KindBool || !got.IsTrue() {
		t.Errorf("1 < 2 = %s, want true", got.Display())
	}

	// Equality dispatches on kind, because chapter 04 defines == on any
	// unrestricted type rather than per-type.
	got, _ = binOp(t, bytecode.OpEq, cs("a"), cs("a"))
	if !got.IsTrue() {
		t.Error(`"a" == "a" should be true`)
	}
	got, _ = binOp(t, bytecode.OpEq, ci(1), cf(1))
	if got.IsTrue() {
		t.Error("an int and a float are different kinds and must not compare equal")
	}
}

func TestNegationTrapsAtMinInt(t *testing.T) {
	// -MinInt64 has no representation, so it is an overflow like any other.
	p := mainWith(1, func(c *bytecode.Chunk) {
		c.Emit(bytecode.OpConst, c.AddConst(ci(-9223372036854775808)), 1)
		c.Emit(bytecode.OpNegInt, 0, 1)
		c.Emit(bytecode.OpReturn, 1, 1)
	})
	if _, _, err := runProgram(t, p); err == nil {
		t.Error("negating MinInt64 did not trap")
	}
}

func TestLocalsRoundTrip(t *testing.T) {
	// GetLocal and SetLocal address slots relative to the frame base.
	p := mainWith(1, func(c *bytecode.Chunk) {
		c.Emit(bytecode.OpConst, c.AddConst(ci(1)), 1) // slot 0
		c.Emit(bytecode.OpConst, c.AddConst(ci(9)), 2)
		c.Emit(bytecode.OpSetLocal, 0, 2)
		c.Emit(bytecode.OpGetLocal, 0, 3)
		c.Emit(bytecode.OpReturn, 1, 3)
	})
	_, result, err := runProgram(t, p)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	if result.N != 9 {
		t.Errorf("local = %s, want 9", result.Display())
	}
}
