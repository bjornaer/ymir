package check_test

import "testing"

// Error sets, `try`, and unhandled errors. Chapter 06.

const errSrc = `module t

enum IOError    { NotFound(string), }
enum ParseError { UnexpectedEOF, }

func readFile(path: string) -> (string, ?IOError) {
    return "", nil
}

func parse(data: string) -> (int, ?ParseError) {
    return 0, nil
}

func infallible(n: int) -> int {
    return n
}

`

func errProg(decls string) string {
	return errSrc + decls + "\nfunc main() {\n    print(1)\n}\n"
}

func TestTryPropagatesASubset(t *testing.T) {
	// "The callee's error set MUST be a subset of the enclosing function's."
	mustCheckClean(t, errProg(`func load(p: string) -> (int, ?(IOError | ParseError)) {
    data := try readFile(p)
    n := try parse(data)
    return n, nil
}
`))

	mustReport(t, errProg(`func load(p: string) -> (int, ?IOError) {
    n := try parse("x")
    return n, nil
}
`), "try propagates ParseError, which is not a subset of this function's IOError")

	// The hint names the widened set, which is the fix.
	mustReport(t, errProg(`func load(p: string) -> (int, ?IOError) {
    n := try parse("x")
    return n, nil
}
`), "widen the declared set to ?(IOError | ParseError)")

	// Identical sets are a subset of themselves.
	mustCheckClean(t, errProg(`func load(p: string) -> (string, ?IOError) {
    data := try readFile(p)
    return data, nil
}
`))
}

func TestTryNeedsAnErrorPositionOnBothSides(t *testing.T) {
	// "The enclosing function MUST have an error position."
	mustReport(t, errProg(`func load(p: string) -> string {
    data := try readFile(p)
    return data
}
`), "no error position to return it in")

	// "try on a call with no error position is a compile error."
	mustReport(t, errProg(`func load(p: string) -> (int, ?IOError) {
    n := try infallible(1)
    return n, nil
}
`), "try needs a call that can fail, and infallible has no error position")
}

func TestTryNeedsZeroValuesForOtherResults(t *testing.T) {
	// "Every non-error result of the enclosing function MUST have a zero value.
	// try in a function returning an enum or a linear type is a compile error,
	// since there is nothing to return on the error path."
	mustReport(t, errProg(`func load(p: string) -> (ParseError, ?IOError) {
    data := try readFile(p)
    return ParseError.UnexpectedEOF, nil
}
`), "try returns the zero value of every other result, and ParseError has none")

	// A nullable of the same enum does have one, so it is fine.
	mustCheckClean(t, errProg(`func load(p: string) -> (?ParseError, ?IOError) {
    data := try readFile(p)
    return nil, nil
}
`))
}

func TestTryShape(t *testing.T) {
	// "The type of try e is the callee's result type with the error position
	// removed."
	mustReport(t, errProg(`func load(p: string) -> (string, ?IOError) {
    var n: int = try readFile(p)
    return "", nil
}
`), "cannot use string as int")

	// Where no non-error result remains, try produces no value.
	mustCheckClean(t, errProg(`func touch(p: string) -> ?IOError {
    return nil
}

func load(p: string) -> ?IOError {
    try touch(p)
    return nil
}
`))
}

func TestUnhandledErrorResult(t *testing.T) {
	// "If a call's result type has an error position, the caller MUST bind it."
	mustReport(t, errProg(`func load(p: string) {
    readFile(p)
}
`), "unhandled error result from readFile")

	// The three legal forms.
	mustCheckClean(t, errProg(`func load(p: string) {
    _, _ = readFile(p)
}
`))
	mustCheckClean(t, errProg(`func load(p: string) {
    data, err := readFile(p)
    if err != nil {
        print("failed")
    }
    print(data)
}
`))
	mustCheckClean(t, errProg(`func load(p: string) -> (string, ?IOError) {
    data := try readFile(p)
    return data, nil
}
`))

	// A call with no error position may stand alone: that is how a
	// void-in-effect function is written.
	mustCheckClean(t, errProg(`func load(p: string) {
    print(infallible(1))
}
`))
}

func TestErrorBindingMustBeRead(t *testing.T) {
	// "Binding an error and never reading it is also a compile error."
	mustReport(t, errProg(`func load(p: string) {
    data, err := readFile(p)
    print(data)
}
`), "err holds an error that is never read")

	// Reading it in any way satisfies the rule.
	mustCheckClean(t, errProg(`func load(p: string) {
    data, err := readFile(p)
    if err != nil {
        print("failed")
    }
    print(data)
}
`))
	mustCheckClean(t, errProg(`func load(p: string) -> (string, ?IOError) {
    data, err := readFile(p)
    return data, err
}
`))

	// Discarding it deliberately is fine — that is what `_` is for.
	mustCheckClean(t, errProg(`func load(p: string) {
    data, _ := readFile(p)
    print(data)
}
`))

	// Writing to the binding is not reading it.
	mustReport(t, errProg(`func load(p: string) {
    data, err := readFile(p)
    err = nil
    print(data)
}
`), "never read")

	// Reading it on the right of an assignment to itself counts.
	mustCheckClean(t, errProg(`func load(p: string) -> (string, ?IOError) {
    data, err := readFile(p)
    if err != nil {
        return "", err
    }
    return data, nil
}
`))
}

func TestErrorSetsCompose(t *testing.T) {
	// The property the whole design exists for: a function's set is the union
	// of its callees', and returning a callee's error needs no wrapping.
	mustCheckClean(t, errProg(`func load(p: string) -> (int, ?(IOError | ParseError)) {
    data, err := readFile(p)
    if err != nil {
        return 0, err
    }
    n, err2 := parse(data)
    if err2 != nil {
        return 0, err2
    }
    return n, nil
}
`))
}
