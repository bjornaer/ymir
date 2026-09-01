package check_test

import "testing"

// Nullable types and narrowing, rules N1-N6 of chapter 02.

const nullableSrc = `module t

func find() -> ?int {
    return 7
}

func main() {
`

func nullable(body string) string { return nullableSrc + body + "\n}\n" }

func TestNullableMustBeNarrowedBeforeUse(t *testing.T) {
	// N4: "A ?T MUST be narrowed before it is used as a T; x + 1 where x: ?int
	// is a type error."
	mustReport(t, nullable("    v := find()\n    print(v + 1)"),
		"?int must be narrowed before it is used as int")
	mustCheckClean(t, nullable("    v := find()\n    if v != nil {\n        print(v + 1)\n    }"))
}

func TestNarrowingBothBranches(t *testing.T) {
	// `x != nil` narrows the then branch...
	mustCheckClean(t, nullable(`    v := find()
    if v != nil {
        print(v + 1)
    } else {
        print(0)
    }`))

	// ...and `x == nil` narrows the else branch.
	mustCheckClean(t, nullable(`    v := find()
    if v == nil {
        print(0)
    } else {
        print(v + 1)
    }`))

	// The other branch is not narrowed in either case.
	mustReport(t, nullable(`    v := find()
    if v != nil {
        print(0)
    } else {
        print(v + 1)
    }`), "must be narrowed")
	mustReport(t, nullable(`    v := find()
    if v == nil {
        print(v + 1)
    }`), "must be narrowed")
}

func TestNarrowingDoesNotEscapeTheBranch(t *testing.T) {
	// "only within the matching branch" — it is not flow typing.
	mustReport(t, nullable(`    v := find()
    if v != nil {
        print(v + 1)
    }
    print(v + 1)`), "must be narrowed")
}

func TestNarrowingDoesNotSurviveReassignment(t *testing.T) {
	mustReport(t, nullable(`    v := find()
    if v != nil {
        v = nil
        print(v + 1)
    }`), "must be narrowed")

	// And the assignment itself is checked against the declared ?int, not
	// against the narrowed int, so writing nil there is legal.
	got := errorsFor(t, nullable(`    v := find()
    if v != nil {
        v = nil
    }`))
	if got != "" {
		t.Errorf("assigning nil to a narrowed ?int must be legal, got:\n%s", got)
	}
}

func TestNarrowingIsSyntacticallyExact(t *testing.T) {
	// The condition must be exactly `x != nil` or `x == nil` on a binding.
	// Anything else is outside the rule, so the value stays nullable.
	mustReport(t, nullable(`    v := find()
    if v != nil && true {
        print(v + 1)
    }`), "must be narrowed")

	mustReport(t, `module t

struct Box {
    v: ?int,
}

func main() {
    var b: Box = Box{v: 1}
    if b.v != nil {
        print(b.v + 1)
    }
}
`, "must be narrowed")
}

func TestNarrowingNests(t *testing.T) {
	mustCheckClean(t, `module t

func find() -> ?int {
    return 7
}

func other() -> ?string {
    return "a"
}

func main() {
    v := find()
    s := other()
    if v != nil {
        if s != nil {
            print(s + "!")
            print(v + 1)
        }
    }
}
`)
}

func TestNullableSelectionAndIndexing(t *testing.T) {
	mustReport(t, `module t

struct Point {
    x: int,
}

func main() {
    var p: ?Point = nil
    print(p.x)
}
`, "which may be nil")

	mustCheckClean(t, `module t

struct Point {
    x: int,
}

func main() {
    var p: ?Point = Point{x: 1}
    if p != nil {
        print(p.x)
    }
}
`)

	mustReport(t, wrap("    var xs: ?array[int] = nil\n    print(xs[0])"), "which may be nil")
	mustCheckClean(t, wrap("    var xs: ?array[int] = [1]\n    if xs != nil {\n        print(xs[0])\n    }"))
}

func TestNullableIsIdempotentAndRejectsLinear(t *testing.T) {
	// N2 and N5. `??T` is not writable — the parser folds it — so this checks
	// the observable half: a nullable qubit is refused.
	mustReport(t, "module t\n\nfunc f(q: ?qubit) {\n    print(1)\n}\n\nfunc main() {\n    print(1)\n}\n",
		"? requires an unrestricted type")
}

func TestNilBelongsOnlyToNullables(t *testing.T) {
	// N3.
	mustCheckClean(t, wrap("    var v: ?int = nil\n    print(1)"))
	mustReport(t, wrap("    var n: int = nil"), "cannot use nil as int")
	mustReport(t, wrap("    var n: int = 0\n    if n == nil {\n        print(1)\n    }"), "never nil")
}
