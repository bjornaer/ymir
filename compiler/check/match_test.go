package check_test

import "testing"

// `match` and exhaustiveness. Chapter 05 §match, §Patterns and §Exhaustiveness;
// chapter 06 §Qualified patterns.

const shapeEnum = `module t

enum Shape {
    Circle(float),
    Rect(float, float),
    Point,
}

func main() {
    var s: Shape = Point
`

func shape(body string) string { return shapeEnum + body + "\n}\n" }

func TestMatchMustBeExhaustive(t *testing.T) {
	mustCheckClean(t, shape(`    match s {
        Circle(r)  => print(r),
        Rect(w, h) => print(w),
        Point      => print(0.0),
    }`))

	// "A match that omits a variant and has no _ arm is a compile error naming
	// the missing variants."
	mustReport(t, shape(`    match s {
        Circle(r) => print(r),
    }`), "missing Point and Rect")

	// A `_` arm satisfies it.
	mustCheckClean(t, shape(`    match s {
        Circle(r) => print(r),
        _         => print(0.0),
    }`))
}

func TestMatchArmsAreASet(t *testing.T) {
	mustReport(t, shape(`    match s {
        Circle(r)  => print(r),
        Circle(q)  => print(q),
        Rect(w, h) => print(w),
        Point      => print(0.0),
    }`), "duplicate arm for Shape.Circle")

	mustReport(t, shape(`    match s {
        Circle(r) => print(r),
        _         => print(0.0),
        _         => print(1.0),
    }`), "duplicate _ arm")
}

func TestPatternArityAndBindings(t *testing.T) {
	mustReport(t, shape(`    match s {
        Circle(r, extra) => print(r),
        Rect(w, h)       => print(w),
        Point            => print(0.0),
    }`), "Circle carries 1 value, but this pattern binds 2")

	mustReport(t, shape(`    match s {
        Circle()   => print(0.0),
        Rect(w, h) => print(w),
        Point      => print(0.0),
    }`), "binds 0")

	// A binding has the payload's type, not an unknown one.
	mustReport(t, shape(`    match s {
        Circle(r)  => print(r + 1),
        Rect(w, h) => print(w),
        Point      => print(0.0),
    }`), "mismatched types float and int")

	// `_` discards a position, and several may appear in one pattern.
	mustCheckClean(t, shape(`    match s {
        Circle(_)  => print(0.0),
        Rect(_, _) => print(1.0),
        Point      => print(2.0),
    }`))

	mustReport(t, shape(`    match s {
        Nope(r)    => print(r),
        Circle(r)  => print(r),
        Rect(w, h) => print(w),
        Point      => print(0.0),
    }`), "enum Shape has no variant Nope")
}

func TestMatchOverAUnion(t *testing.T) {
	src := func(body string) string {
		return `module t

enum IOError    { NotFound(string), }
enum ParseError { UnexpectedEOF, }

func report(e: IOError | ParseError) {
` + body + `
}

func main() {
    report(IOError.NotFound("x"))
}
`
	}

	// "Exhaustiveness is computed over the whole union: every variant of every
	// member."
	mustCheckClean(t, src(`    match e {
        IOError.NotFound(p)      => print(p),
        ParseError.UnexpectedEOF => print("eof"),
    }`))

	mustReport(t, src(`    match e {
        IOError.NotFound(p) => print(p),
    }`), "missing ParseError.UnexpectedEOF")

	// Patterns over a union MUST be qualified, since two members may share a
	// variant name.
	mustReport(t, src(`    match e {
        NotFound(p)   => print(p),
        UnexpectedEOF => print("eof"),
    }`), "must name its enum")

	// The qualifier must be a member of the scrutinee, not just any enum.
	mustReport(t, `module t

enum IOError    { NotFound(string), }
enum ParseError { UnexpectedEOF, }
enum Other      { Nope, }

func report(e: IOError | ParseError) {
    match e {
        IOError.NotFound(p)      => print(p),
        ParseError.UnexpectedEOF => print("eof"),
        Other.Nope               => print("no"),
    }
}

func main() {
    report(IOError.NotFound("x"))
}
`, "Other is not part of this match's type")
}

func TestUnqualifiedIsFineOnASingleEnum(t *testing.T) {
	// "Within a match on a single enum, the qualifier MAY be omitted."
	mustCheckClean(t, shape(`    match s {
        Shape.Circle(r)  => print(r),
        Rect(w, h)       => print(w),
        Point            => print(0.0),
    }`))
}

func TestNilArms(t *testing.T) {
	src := func(param, body string) string {
		return `module t

enum IOError { NotFound(string), }

func report(e: ` + param + `) {
` + body + `
}

func main() {
    report(nil)
}
`
	}

	// "Matching an un-narrowed nullable requires exactly one nil arm."
	mustReport(t, src("?IOError", `    match e {
        NotFound(p) => print(p),
    }`), "must include exactly one nil arm")

	mustCheckClean(t, src("?IOError", `    match e {
        nil         => print("ok"),
        NotFound(p) => print(p),
    }`))

	mustReport(t, src("?IOError", `    match e {
        nil         => print("ok"),
        nil         => print("ok"),
        NotFound(p) => print(p),
    }`), "at most one nil arm")

	// "Inside a block guarded by x != nil the checker narrows it, and the nil
	// arm is then neither required nor permitted."
	mustCheckClean(t, src("?IOError", `    if e != nil {
        match e {
            NotFound(p) => print(p),
        }
    }`))

	mustReport(t, src("?IOError", `    if e != nil {
        match e {
            nil         => print("ok"),
            NotFound(p) => print(p),
        }
    }`), "is never nil, so this match must not have a nil arm")
}

func TestMatchNeedsAnEnum(t *testing.T) {
	// "Enum values are inspected only by match" — and match inspects nothing
	// else.
	mustReport(t, wrap("    x := 1\n    match x {\n        _ => print(1),\n    }"),
		"match is defined on enums and unions of enums")
}

func TestArmBindingsAreScopedToTheArm(t *testing.T) {
	mustReport(t, shape(`    match s {
        Circle(r)  => print(r),
        Rect(w, h) => print(w),
        Point      => print(0.0),
    }
    print(r)`), "undefined: r")

	// The same name in two arms does not collide.
	mustCheckClean(t, shape(`    match s {
        Circle(v)  => print(v),
        Rect(v, h) => print(v),
        Point      => print(0.0),
    }`))
}
