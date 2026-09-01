package check_test

import "testing"

// Calls, method sets, and selection. Chapter 04 §Calls and §Indexing and
// selection, chapter 02 §Structs and §Enums.

func TestCallArityAndArgumentTypes(t *testing.T) {
	// "Argument count and types MUST match exactly. There are no default
	// parameters, no variadic user functions, and no keyword arguments."
	src := func(call string) string {
		return "module t\n\nfunc add(a: int, b: int) -> int {\n    return a + b\n}\n\nfunc main() {\n    " + call + "\n}\n"
	}
	mustCheckClean(t, src("print(add(1, 2))"))
	mustReport(t, src("print(add(1))"), "add takes 2 arguments, got 1")
	mustReport(t, src("print(add(1, 2, 3))"), "add takes 2 arguments, got 3")
	mustReport(t, src("print(add(1, 2.0))"), "cannot use float as int in the call to add")
}

func TestCallingSomethingThatIsNotAFunction(t *testing.T) {
	mustReport(t, wrap("    x := 1\n    print(x(2))"), "cannot call int")
	mustReport(t, `module t

struct Point {
    x: int,
}

func main() {
    p := Point(1)
    print(1)
}
`, "Point is a type, not a function")
}

func TestFunctionValues(t *testing.T) {
	// Functions are first class (chapter 02 §func), which the legacy AST made
	// structurally impossible.
	mustCheckClean(t, `module t

func double(n: int) -> int {
    return n * 2
}

func apply(f: func(int) -> int, n: int) -> int {
    return f(n)
}

func main() {
    print(apply(double, 3))
    g := double
    print(g(4))
    print(apply(func(x: int) -> int { return x + 1 }, 5))
}
`)

	mustReport(t, `module t

func double(n: int) -> int {
    return n * 2
}

func apply(f: func(int) -> int, n: int) -> int {
    return f(n)
}

func main() {
    print(apply(double, 3.0))
}
`, "cannot use float as int")
}

func TestMultiValuedCalls(t *testing.T) {
	src := func(body string) string {
		return "module t\n\nfunc divmod(a: int, b: int) -> (int, int) {\n    return a / b, a % b\n}\n\nfunc main() {\n" + body + "\n}\n"
	}
	// "A multi-valued call may appear only as the entire right-hand side of a
	// destructuring assignment or a return."
	mustCheckClean(t, src("    q, r := divmod(17, 5)\n    print(q)\n    print(r)"))
	mustReport(t, src("    print(divmod(17, 5))"), "multi-valued call in expression position")
	// Chapter 03: "A multi-valued call MUST be destructured; binding it to a
	// single name is a compile error."
	mustReport(t, src("    q := divmod(17, 5)\n    print(q)"), "multi-valued call")
	mustReport(t, src("    a, b, c := divmod(17, 5)\n    print(a)"), "assignment mismatch")

	// And as the whole of a return.
	mustCheckClean(t, `module t

func divmod(a: int, b: int) -> (int, int) {
    return a / b, a % b
}

func pass(a: int, b: int) -> (int, int) {
    return divmod(a, b)
}

func main() {
    q, r := pass(17, 5)
    print(q)
    print(r)
}
`)
}

func TestCallWithNoResultsIsNotAValue(t *testing.T) {
	// A void-in-effect call is legal as a statement and nowhere else.
	mustCheckClean(t, wrap("    print(1)"))
	mustReport(t, wrap("    x := print(1)\n    print(x)"), "returns no values")
}

func TestReturnValues(t *testing.T) {
	mustReport(t, "module t\n\nfunc f() -> int {\n    return 1.0\n}\n\nfunc main() {\n    print(f())\n}\n",
		"cannot use float as int in the return")
	mustReport(t, "module t\n\nfunc f() -> int {\n    return\n}\n\nfunc main() {\n    print(f())\n}\n",
		"bare return in a function declared to return 1 value")
	mustReport(t, "module t\n\nfunc f() {\n    return 1\n}\n\nfunc main() {\n    f()\n}\n",
		"declares no results")
	mustReport(t, "module t\n\nfunc f() -> (int, int) {\n    return 1\n}\n\nfunc main() {\n    a, b := f()\n    print(a + b)\n}\n",
		"return has 1 value, want 2 values")

	// T is assignable to ?T at a return, like anywhere else.
	mustCheckClean(t, "module t\n\nfunc f() -> ?int {\n    return 1\n}\n\nfunc main() {\n    print(1)\n}\n")
	mustCheckClean(t, "module t\n\nfunc f() -> ?int {\n    return nil\n}\n\nfunc main() {\n    print(1)\n}\n")
}

func TestErrorSetSubsetAtAReturn(t *testing.T) {
	// The rule the whole error design rests on: a callee's narrower set flows
	// out through a wider declared one, and not the other way.
	wide := `module t

enum IOError    { NotFound(string), }
enum ParseError { UnexpectedEOF, }

func narrow() -> (int, ?IOError) {
    return 0, nil
}

func widen() -> (int, ?(IOError | ParseError)) {
    n, err := narrow()
    return n, err
}

func main() {
    print(1)
}
`
	mustCheckClean(t, wide)

	narrowing := `module t

enum IOError    { NotFound(string), }
enum ParseError { UnexpectedEOF, }

func wide() -> (int, ?(IOError | ParseError)) {
    return 0, nil
}

func narrow() -> (int, ?IOError) {
    n, err := wide()
    return n, err
}

func main() {
    print(1)
}
`
	mustReport(t, narrowing, "cannot use ?(IOError | ParseError) as ?IOError")
	mustReport(t, narrowing, "assignable only to a superset")
}

func TestMethods(t *testing.T) {
	src := `module t

struct Point {
    x: int,
    y: int,
}

func (p: Point) sum() -> int {
    return p.x + p.y
}

func (p: mut Point) scale(k: int) {
    p.x = p.x * k
}

func main() {
    var p: Point = Point{x: 2, y: 3}
    print(p.sum())
    p.scale(2)
}
`
	mustCheckClean(t, src)

	// Arity and argument types apply to a method exactly as to a function.
	mustReport(t, `module t

struct Point {
    x: int,
}

func (p: Point) offset(k: int) -> int {
    return p.x + k
}

func main() {
    var p: Point = Point{x: 1}
    print(p.offset())
}
`, "takes 1 argument, got 0")

	mustReport(t, `module t

struct Point {
    x: int,
}

func (p: Point) sum() -> int {
    return p.x
}

func main() {
    var p: Point = Point{x: 1}
    print(p.nope())
}
`, "has no field or method nope")
}

func TestMutReceiverNeedsAMutableBase(t *testing.T) {
	mustReport(t, `module t

struct Point {
    x: int,
}

func (p: mut Point) bump() {
    p.x = p.x + 1
}

func take(p: Point) {
    p.bump()
}

func main() {
    var p: Point = Point{x: 1}
    take(p)
}
`, "is not mutable")
}

func TestStructFieldAccess(t *testing.T) {
	src := `module t

struct Point {
    x: int,
    y: float,
}

func main() {
    var p: Point = Point{x: 1, y: 2.0}
    print(p.x)
    print(p.y)
}
`
	mustCheckClean(t, src)

	mustReport(t, `module t

struct Point {
    x: int,
}

func main() {
    var p: Point = Point{x: 1}
    print(p.z)
}
`, "Point has no field or method z")

	// The field's type is real, so misusing it errors.
	mustReport(t, `module t

struct Point {
    x: int,
    y: float,
}

func main() {
    var p: Point = Point{x: 1, y: 2.0}
    print(p.x + p.y)
}
`, "mismatched types int and float")
}

func TestEnumsAreInspectedOnlyByMatch(t *testing.T) {
	// "There is no field access, no cast, and no 'is this variant' predicate."
	mustReport(t, `module t

enum Shape {
    Circle(float),
    Point,
}

func main() {
    var s: Shape = Point
    print(s.Circle)
}
`, "inspected only by match")
}

func TestQualifiedVariantAsAValue(t *testing.T) {
	// A payload-free variant is a value; one with a payload must be built.
	mustCheckClean(t, `module t

enum Shape {
    Circle(float),
    Point,
}

func main() {
    var s: Shape = Shape.Point
    var t2: Shape = Shape.Circle(1.0)
    print(1)
}
`)
	mustReport(t, `module t

enum Shape {
    Circle(float),
}

func main() {
    var s: Shape = Shape.Circle
    print(1)
}
`, "must be constructed")

	// Payload arity is checked like any other call.
	mustReport(t, `module t

enum Shape {
    Rect(float, float),
}

func main() {
    var s: Shape = Rect(1.0)
    print(1)
}
`, "Shape.Rect takes 2 arguments, got 1")
}

func TestConversions(t *testing.T) {
	mustCheckClean(t, wrap(`    i := 1
    f := float(i)
    j := int(f)
    z := complex(f)
    print(real(z))
    print(imag(z))
    print(j)`))
	mustReport(t, wrap("    print(float(\"a\"))"), "cannot convert string to float")
	mustReport(t, wrap("    print(real(1))"), "real needs a complex, got int")
}

func TestBuiltinSignatures(t *testing.T) {
	// Annotated rather than inferred: composite literal typing is M6.
	mustCheckClean(t, wrap(`    var xs: array[int] = [1, 2, 3]
    append(xs, 4)
    print(len(xs))
    ys := copy(xs)
    print(len(ys))
    var m: map[string, int] = {"a": 1}
    delete(m, "a")
    print(len(m))
    print(len("abc"))
    print(len(chars("abc")))
    print(str(1))
    ch := make_chan[int](2)
    close(ch)`))

	mustReport(t, wrap("    print(len(1))"), "len is defined on array, map, string and qreg")
	mustReport(t, wrap("    var xs: array[int] = [1]\n    append(xs, \"a\")"), "cannot use string as int")
	mustReport(t, wrap("    var m: map[string, int] = {\"a\": 1}\n    delete(m, 1)"), "cannot use int as string")
	mustReport(t, wrap("    print(chars(1))"), "chars needs a string")
	mustReport(t, wrap("    panic(1)"), "panic takes a string message")
	mustReport(t, wrap("    print(Error(1))"), "Error takes a string message")
	mustReport(t, wrap("    close(1)"), "close needs a channel")
	mustReport(t, wrap("    ch := make_chan[int](\"a\")\n    close(ch)"), "capacity must be int")
	mustReport(t, wrap("    print(range(1.0, 2.0))"), "range takes int arguments")
}

func TestQuantumBuiltinsAreNotImplemented(t *testing.T) {
	// Decision D3 makes chapter 08 normative now and unimplemented until
	// Phase 7. Allowing an allocation would let a program build a linear value
	// the rest of the checker cannot yet track.
	mustReport(t, wrap("    q := qubit()\n    print(1)"), "quantum fragment is not implemented yet")
	mustReport(t, wrap("    discard(1)"), "quantum fragment is not implemented yet")
}
