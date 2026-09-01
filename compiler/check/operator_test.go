package check_test

import "testing"

// The operand table of chapter 04 §Operand typing, and the inference rules of
// chapter 02 §Type inference.

func TestOperandTypesMustBeIdentical(t *testing.T) {
	// "Both operands of a binary operator MUST have identical types."
	mustReport(t, wrap("    x := 1\n    y := 2.0\n    print(x + y)"),
		"mismatched types int and float")
	mustReport(t, wrap("    print(1 + \"a\")"), "mismatched types int and string")

	// The explicit conversion is named in the hint, because that is the fix.
	mustReport(t, wrap("    x := 1\n    y := 2.0\n    print(x + y)"),
		"float(x) on the int operand")
}

func TestArithmeticResultTypes(t *testing.T) {
	mustCheckClean(t, wrap(`    i := 1 + 2 - 3 * 4 / 5 % 6 ** 2
    f := 1.0 + 2.0 - 3.0 * 4.0 / 5.0 ** 2.0
    s := "a" + "b"
    b := true && false || !true
    print(i)
    print(f)
    print(s)
    print(b)`))
}

func TestModuloIsIntOnly(t *testing.T) {
	mustCheckClean(t, wrap("    print(7 % 3)"))
	mustReport(t, wrap("    x := 7.0\n    y := 2.0\n    print(x % y)"),
		"% is defined only on int")
}

func TestComplexIsNotOrdered(t *testing.T) {
	mustReport(t, wrap("    a := 1.0i\n    b := 2.0i\n    if a < b {\n        print(1)\n    }"),
		"complex is not ordered")

	// Equality is defined on it, as on any unrestricted type.
	mustCheckClean(t, wrap("    a := 1.0i\n    b := 2.0i\n    if a == b {\n        print(1)\n    }"))
}

func TestComparisonYieldsBool(t *testing.T) {
	mustCheckClean(t, wrap(`    if 1 < 2 && "a" == "b" {
        print(1)
    }`))
	mustReport(t, wrap("    if 1 && true {\n        print(1)\n    }"), "mismatched types int and bool")
}

func TestNoTruthiness(t *testing.T) {
	// "The condition MUST be bool. There is no truthiness."
	mustReport(t, wrap("    x := 1\n    if x {\n        print(1)\n    }"), "want bool")
	mustReport(t, wrap("    x := 1\n    while x {\n        print(1)\n    }"), "want bool")
	mustReport(t, wrap("    for i := 0; i; i = i + 1 {\n        print(i)\n    }"), "want bool")
	mustCheckClean(t, wrap("    x := 1\n    if x != 0 {\n        print(1)\n    }"))
}

func TestUnaryOperators(t *testing.T) {
	mustCheckClean(t, wrap("    print(-1)\n    print(-1.0)\n    print(!true)"))
	mustReport(t, wrap("    print(-\"a\")"), "invalid operation: - on string")
	mustReport(t, wrap("    print(!1)"), "invalid operation: ! on int")

	// `<-ch` yields the element type.
	mustCheckClean(t, wrap("    ch := make_chan[int](1)\n    print(1)"))
	mustReport(t, wrap("    x := 1\n    y := <-x\n    print(y)"), "receive from int")
}

func TestNilComparison(t *testing.T) {
	// Rule N3: only a nullable type has nil.
	mustReport(t, wrap("    var n: int = 0\n    if n == nil {\n        print(1)\n    }"),
		"int is never nil")
	mustReport(t, `module t

enum Shape {
    Circle(float),
}

func main() {
    # Annotated rather than inferred: call typing is M5, so := would leave
    # s unknown and the nil comparison unchecked.
    var s: Shape = Circle(1.0)
    if s == nil {
        print(1)
    }
}
`, "Shape is never nil")

	// A nullable may be compared, and only with == and !=.
	mustCheckClean(t, wrap("    var v: ?int = nil\n    if v != nil {\n        print(1)\n    }"))
	mustReport(t, wrap("    var v: ?int = nil\n    if v < nil {\n        print(1)\n    }"),
		"only == and != are defined")
}

func TestInference(t *testing.T) {
	// "Inferred: the type of a var or := binding, from its initializer."
	mustCheckClean(t, wrap("    x := 1\n    var y := 2.0\n    print(x)\n    print(y)"))

	// The inferred type is real, not a placeholder: mixing it errors.
	mustReport(t, wrap("    x := 1\n    var y := 2.0\n    print(x + y)"), "mismatched types")

	// nil alone is uninferable.
	mustReport(t, wrap("    v := nil\n    print(1)"), "cannot infer a type for v from nil")
	mustCheckClean(t, wrap("    var v: ?int = nil\n    print(1)"))
}

func TestAnnotatedDeclarationChecksAssignability(t *testing.T) {
	mustReport(t, wrap("    var x: int = 1.0"), "cannot use float as int")
	mustCheckClean(t, wrap("    var x: float = 1.0\n    print(x)"))

	// T is assignable to ?T, but not the reverse (N4).
	mustCheckClean(t, wrap("    var x: ?int = 1\n    print(1)"))
	mustReport(t, wrap("    var a: ?int = 1\n    var b: int = a"), "cannot use ?int as int")
}

func TestAssignmentChecksAssignability(t *testing.T) {
	mustReport(t, wrap("    x := 1\n    x = 2.0"), "cannot use float as int")
	mustCheckClean(t, wrap("    x := 1\n    x = 2\n    print(x)"))
}

func TestZeroValues(t *testing.T) {
	// Types that have one.
	mustCheckClean(t, wrap(`    var i: int
    var s: string
    var xs: array[int]
    var m: map[string, int]
    var v: ?int
    print(i)`))

	// And those that do not (chapter 02 §Zero values).
	mustReport(t, `module t

enum Shape {
    Circle(float),
}

func main() {
    var s: Shape
    print(1)
}
`, "Shape has no zero value")
	mustReport(t, wrap("    var c: chan[int]"), "chan[int] has no zero value")
	mustReport(t, wrap("    var f: func(int) -> int"), "has no zero value")

	// A struct is field-wise zero, so it inherits the problem from a field.
	mustReport(t, `module t

enum Shape {
    Circle(float),
}

struct Holder {
    s: Shape,
}

func main() {
    var h: Holder
    print(1)
}
`, "Holder has no zero value")

	// The nullable form is the fix, and the hint says so.
	mustCheckClean(t, wrap("    var c: ?chan[int]\n    print(1)"))
}

func TestConstantExpressions(t *testing.T) {
	// "Division by zero in a constant expression is a compile error, not a
	// runtime panic." (chapter 04)
	mustReport(t, "module t\n\nconst R: int = 10 / 0\n\nfunc main() {\n    print(R)\n}\n",
		"division by zero in a constant expression")
	mustReport(t, "module t\n\nconst R: int = 10 % 0\n\nfunc main() {\n    print(R)\n}\n",
		"division by zero in a constant expression")

	// R5: overflow of an int constant expression is an error too.
	mustReport(t, "module t\n\nconst B: int = 9223372036854775807 + 1\n\nfunc main() {\n    print(B)\n}\n",
		"constant expression overflows int")
	mustReport(t, "module t\n\nconst B: int = 4611686018427387904 * 4\n\nfunc main() {\n    print(B)\n}\n",
		"constant expression overflows int")
	mustReport(t, "module t\n\nconst B: int = 2 ** 64\n\nfunc main() {\n    print(B)\n}\n",
		"constant expression overflows int")

	// A literal too large to represent is caught before any operator runs.
	mustReport(t, "module t\n\nconst B: int = 99999999999999999999\n\nfunc main() {\n    print(B)\n}\n",
		"overflows int")

	// float division by zero is IEEE infinity, not an error (chapter 04).
	mustCheckClean(t, "module t\n\nconst R: float = 1.0 / 0.0\n\nfunc main() {\n    print(R)\n}\n")

	// Constants compose, and one names another.
	mustCheckClean(t, `module t

const A: int = 2
const B: int = A * 3

func main() {
    print(B)
}
`)
	mustReport(t, `module t

const A: int = 4611686018427387904
const B: int = A * 4

func main() {
    print(B)
}
`, "constant expression overflows int")

	// The declared type still has to match.
	mustReport(t, "module t\n\nconst A: int = 1.5\n\nfunc main() {\n    print(A)\n}\n",
		"cannot use float as int")
}

func TestOverflowIsReportedOnce(t *testing.T) {
	// Folding is memoized, because both the operator check and the const
	// declaration check ask for the same initializer's value.
	got := errorsFor(t, "module t\n\nconst B: int = 9223372036854775807 + 1\n\nfunc main() {\n    print(B)\n}\n")
	if n := countOccurrences(got, "overflows int"); n != 1 {
		t.Errorf("overflow reported %d times, want 1:\n%s", n, got)
	}
}

func countOccurrences(s, sub string) int {
	n := 0
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			n++
		}
	}
	return n
}
