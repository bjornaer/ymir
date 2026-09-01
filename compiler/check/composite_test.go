package check_test

import "testing"

// Composite literals and indexing. Chapter 04 §Composite literals and
// §Indexing and selection.

func TestArrayLiterals(t *testing.T) {
	mustCheckClean(t, wrap("    xs := [1, 2, 3]\n    print(len(xs))"))
	mustReport(t, wrap("    xs := [1, 2.0]\n    print(len(xs))"), "same type")

	// "An empty collection literal has no inferable element type and MUST be
	// annotated." (chapter 02 §Type inference)
	mustReport(t, wrap("    ys := []\n    print(len(ys))"), "cannot infer the element type")
	mustCheckClean(t, wrap("    var ys: array[int] = []\n    print(len(ys))"))

	// The expected type wins where context supplies one, which is what lets a
	// literal of ints fill an array of nullables.
	mustCheckClean(t, wrap("    var xs: array[?int] = [1, nil, 3]\n    print(len(xs))"))
	mustReport(t, wrap("    var xs: array[int] = [1, \"a\"]\n    print(len(xs))"),
		"cannot use string as int")
}

func TestMatrixLiterals(t *testing.T) {
	// "A nested array literal is matrix[T] when every row has equal length and
	// T is float or complex; otherwise it is array[array[T]]."
	mustCheckClean(t, wrap("    var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]\n    print(1)"))
	mustReport(t, wrap("    var a: matrix[float] = [[1.0, 2.0], [3.0]]\n    print(1)"), "same length")
	mustReport(t, wrap("    var a: matrix[int] = [[1, 2]]\n    print(1)"), "float or complex")

	// Without context, a rectangular nested literal of floats is a matrix and
	// one of ints is an array of arrays.
	mustCheckClean(t, wrap("    a := [[1.0, 2.0], [3.0, 4.0]]\n    b := a @ a\n    print(1)"))
	mustReport(t, wrap("    a := [[1, 2], [3, 4]]\n    b := a @ a\n    print(1)"),
		"@ is matrix multiplication")
}

func TestMapLiterals(t *testing.T) {
	mustCheckClean(t, wrap("    m := {\"a\": 1, \"b\": 2}\n    print(len(m))"))
	mustReport(t, wrap("    m := {}\n    print(len(m))"), "cannot infer the key and value types")
	mustCheckClean(t, wrap("    var m: map[string, int] = {}\n    print(len(m))"))
	mustReport(t, wrap("    m := {\"a\": 1, \"b\": 2.0}\n    print(len(m))"), "map values must all have the same type")
	mustReport(t, wrap("    m := {\"a\": 1, 2: 3}\n    print(len(m))"), "map keys must all have the same type")

	// The key type must be hashable, wherever the map came from.
	mustReport(t, `module t

enum Color {
    Red,
}

func main() {
    m := {Red: 1}
    print(len(m))
}
`, "not hashable")
}

func TestTupleLiterals(t *testing.T) {
	mustCheckClean(t, wrap("    p := (1, \"one\")\n    print(p.0)\n    print(p.1)"))
	mustReport(t, wrap("    p := (1, \"one\")\n    print(p.2)"), "no element 2")
	mustReport(t, wrap("    p := (1, \"one\")\n    print(p.0 + p.1)"), "mismatched types int and string")

	// Tuples are indexed positionally with a literal, never with brackets.
	mustReport(t, wrap("    p := (1, \"one\")\n    print(p[0])"), "not indexed with brackets")
}

func TestStructLiterals(t *testing.T) {
	src := func(lit string) string {
		return "module t\n\nstruct Point {\n    x: float,\n    y: float,\n}\n\nfunc main() {\n    p := " + lit + "\n    print(p.x)\n}\n"
	}
	mustCheckClean(t, src("Point{x: 1.0, y: 2.0}"))

	// "Field initialization MUST be exhaustive and by name."
	mustReport(t, src("Point{x: 1.0}"), "Point literal is missing y")
	mustReport(t, src("Point{x: 1.0, y: 2.0, z: 3.0}"), "Point has no field z")
	mustReport(t, src("Point{x: 1.0, x: 2.0, y: 3.0}"), "field x is initialized twice")
	mustReport(t, src("Point{x: 1, y: 2.0}"), "cannot use int as float")

	// A missing field is named, and several are listed.
	mustReport(t, `module t

struct Wide {
    a: int,
    b: int,
    c: int,
}

func main() {
    w := Wide{a: 1}
    print(w.a)
}
`, "missing b and c")

	// Only a struct has a field literal.
	mustReport(t, `module t

enum Shape {
    Circle(float),
}

func main() {
    s := Shape{x: 1.0}
    print(1)
}
`, "is not a struct")
}

func TestIndexing(t *testing.T) {
	mustCheckClean(t, wrap(`    xs := [1, 2, 3]
    print(xs[0])
    m := {"a": 1}
    print(m["a"])
    s := "abc"
    print(s[0])`))

	mustReport(t, wrap("    xs := [1]\n    print(xs[\"a\"])"), "an array is indexed by int, got string")
	mustReport(t, wrap("    m := {\"a\": 1}\n    print(m[1])"), "cannot use int as string")
	mustReport(t, wrap("    x := 1\n    print(x[0])"), "cannot index int")

	// The element type is real.
	mustReport(t, wrap("    xs := [1]\n    var f: float = xs[0]"), "cannot use int as float")
	mustReport(t, wrap("    s := \"abc\"\n    var c: string = s[0]"), "cannot use int as string")
}

func TestMapTwoValueForm(t *testing.T) {
	// "v, ok := m[\"key\"] # map, two-value form; ok is false if absent"
	mustCheckClean(t, wrap(`    m := {"a": 1}
    v, ok := m["a"]
    if ok {
        print(v)
    }`))

	// The second value is a bool, and the first the map's value type.
	mustReport(t, wrap("    m := {\"a\": 1}\n    v, ok := m[\"a\"]\n    var s: string = v\n    print(ok)"),
		"cannot use int as string")

	// Only a map yields two values; an array index does not.
	mustReport(t, wrap("    xs := [1]\n    v, ok := xs[0]\n    print(v)"), "assignment mismatch")
}

func TestMatrixIndexingIsNotDefined(t *testing.T) {
	// Chapter 02 specifies matrix arithmetic and never specifies indexing one.
	// Guessing a shape would be inventing language, so it is refused.
	mustReport(t, wrap("    a := [[1.0, 2.0], [3.0, 4.0]]\n    print(a[0])"),
		"indexing a matrix is not defined in v1")
}

func TestFieldAssignmentNeedsAMutableBase(t *testing.T) {
	// "Assignment to an index or field is legal where the base is mutable."
	// A struct has value semantics, so a non-mut parameter is a copy.
	mustReport(t, `module t

struct Point {
    x: int,
}

func f(p: Point) {
    p.x = 1
}

func main() {
    var p: Point = Point{x: 0}
    f(p)
}
`, "is not mutable")

	mustCheckClean(t, `module t

struct Point {
    x: int,
}

func f(p: mut Point) {
    p.x = 1
}

func main() {
    var p: Point = Point{x: 0}
    f(p)
}
`)
}

func TestNullableCollectionsMustBeNarrowed(t *testing.T) {
	mustReport(t, wrap("    var xs: ?array[int] = nil\n    print(xs[0])"), "which may be nil")
	mustReport(t, `module t

struct Point {
    x: int,
}

func main() {
    var p: ?Point = nil
    print(p.x)
}
`, "which may be nil")
}
