package check_test

import "testing"

// Definite return, chapter 05 §Returning on every path, and main's signature,
// chapter 03 §main.

func fn(body string) string {
	return "module t\n\nfunc f(n: int) -> string {\n" + body + "\n}\n\nfunc main() {\n    print(f(1))\n}\n"
}

func TestFunctionMustReturnOnEveryPath(t *testing.T) {
	mustCheckClean(t, fn(`    return "x"`))

	// Legacy returned "the last evaluated value" here, so a function's result
	// depended on the shape of its final statement.
	mustReport(t, fn(`    print(n)`), "missing return at the end of f")
}

func TestIfTerminatesOnlyWithAnElse(t *testing.T) {
	// "An if with no else never terminates, however its branch ends."
	mustReport(t, fn(`    if n > 0 {
        return "positive"
    }`), "missing return")

	mustCheckClean(t, fn(`    if n > 0 {
        return "positive"
    } else {
        return "non-positive"
    }`))

	// Both branches must terminate, not just one.
	mustReport(t, fn(`    if n > 0 {
        return "positive"
    } else {
        print(n)
    }`), "missing return")

	// else-if chains work, as long as the chain ends in an else.
	mustCheckClean(t, fn(`    if n > 0 {
        return "positive"
    } else if n < 0 {
        return "negative"
    } else {
        return "zero"
    }`))

	mustReport(t, fn(`    if n > 0 {
        return "positive"
    } else if n < 0 {
        return "negative"
    }`), "missing return")
}

func TestPanicTerminates(t *testing.T) {
	mustCheckClean(t, fn(`    panic("unreachable")`))
	mustCheckClean(t, fn(`    if n > 0 {
        return "positive"
    } else {
        panic("bad")
    }`))
}

func TestMatchTerminatesWhenEveryArmDoes(t *testing.T) {
	src := func(body string) string {
		return `module t

enum Shape {
    Circle(float),
    Point,
}

func describe(s: Shape) -> string {
` + body + `
}

func main() {
    print(describe(Point))
}
`
	}
	mustCheckClean(t, src(`    match s {
        Circle(r) => return "circle",
        Point     => return "point",
    }`))

	// One arm that falls through is enough to break it.
	mustReport(t, src(`    match s {
        Circle(r) => return "circle",
        Point     => print("point"),
    }`), "missing return")
}

func TestWhileTrueTerminates(t *testing.T) {
	// "A while true { ... } whose body contains no break that leaves it."
	mustCheckClean(t, fn(`    while true {
        return "x"
    }`))

	// A break makes the loop exitable, so control can reach the end.
	mustReport(t, fn(`    while true {
        if n > 0 {
            break
        }
    }`), "missing return")

	// A break belonging to a *nested* loop does not escape the outer one.
	mustCheckClean(t, fn(`    while true {
        while n > 0 {
            break
        }
        return "x"
    }`))

	// Any other condition does not terminate: the checker does not prove the
	// loop runs at all.
	mustReport(t, fn(`    while n > 0 {
        return "x"
    }`), "missing return")
	mustReport(t, fn(`    for i := 0; i < 3; i = i + 1 {
        return "x"
    }`), "missing return")
}

func TestFunctionLiteralsMustReturnToo(t *testing.T) {
	mustReport(t, wrap(`    f := func(x: int) -> int {
        print(x)
    }
    print(f(1))`), "missing return at the end of this function literal")

	mustCheckClean(t, wrap(`    f := func(x: int) -> int {
        return x + 1
    }
    print(f(1))`))
}

func TestFunctionsWithNoResultsNeedNoReturn(t *testing.T) {
	mustCheckClean(t, "module t\n\nfunc f(n: int) {\n    print(n)\n}\n\nfunc main() {\n    f(1)\n}\n")
}

func TestMainSignature(t *testing.T) {
	mustCheckClean(t, "module t\n\nfunc main() {\n    print(1)\n}\n")

	mustReport(t, "module t\n\nfunc main(n: int) {\n    print(n)\n}\n", "main takes no parameters")
	mustReport(t, "module t\n\nfunc main() -> int {\n    return 0\n}\n", "main declares no results")

	// "main is invoked automatically; it MUST NOT be called explicitly."
	mustReport(t, "module t\n\nfunc again() {\n    main()\n}\n\nfunc main() {\n    print(1)\n}\n",
		"must not be called explicitly")

	// A method named main is a different thing entirely.
	mustCheckClean(t, `module t

struct Runner {
    n: int,
}

func (r: Runner) main() {
    print(r.n)
}

func main() {
    var r: Runner = Runner{n: 1}
    r.main()
}
`)
}
