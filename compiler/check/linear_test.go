package check_test

import "testing"

// Linearity, rules L1 through L6 of chapter 02.
//
// A linear value is reachable from source without the simulator: `qubit()`
// allocates one and `discard` consumes it, both of which are type rules rather
// than runtime behaviour. Decision D3 is why these exist now.

func TestLinearMustBeConsumedExactlyOnce(t *testing.T) {
	// L1: zero uses is an error.
	mustReport(t, wrap("    q := qubit()\n    print(1)"), "q is not consumed")

	// Exactly one use is fine, by each of the consuming operations.
	mustCheckClean(t, wrap("    q := qubit()\n    discard(q)"))
	mustCheckClean(t, wrap("    q := qubit()\n    reset(q)"))
	mustCheckClean(t, wrap("    q := qubit()\n    b := measure(q)\n    print(1)"))

	// L1: two uses is an error.
	mustReport(t, wrap("    q := qubit()\n    discard(q)\n    discard(q)"), "use of moved value q")

	// A parameter is a linear binding too, and the callee owns it.
	mustReport(t, "module t\n\nfunc f(q: qubit) {\n    print(1)\n}\n\nfunc main() {\n    print(1)\n}\n",
		"q is not consumed")
	mustCheckClean(t, "module t\n\nfunc f(q: qubit) {\n    discard(q)\n}\n\nfunc main() {\n    print(1)\n}\n")
}

func TestAssignmentMoves(t *testing.T) {
	// L2: "Binding a linear value to a new name invalidates the old name.
	// Reading a moved-from binding is a compile error. This is the no-cloning
	// theorem, enforced by the type checker."
	mustReport(t, wrap("    q1 := qubit()\n    q2 := q1\n    discard(q1)\n    discard(q2)"),
		"use of moved value q1")
	mustCheckClean(t, wrap("    q1 := qubit()\n    q2 := q1\n    discard(q2)"))
}

func TestPassingMovesUnlessMut(t *testing.T) {
	// L3: "Passing a linear value as an argument consumes it, unless the
	// parameter is declared `mut`, which borrows it for the call's duration."
	consuming := "module t\n\nfunc take(q: qubit) {\n    discard(q)\n}\n\n"
	borrowing := "module t\n\nfunc peek(q: mut qubit) {\n    print(1)\n}\n\n"

	mustReport(t, consuming+"func main() {\n    q := qubit()\n    take(q)\n    take(q)\n}\n",
		"use of moved value q")
	mustCheckClean(t, borrowing+"func main() {\n    q := qubit()\n    peek(q)\n    peek(q)\n    discard(q)\n}\n")

	// A borrowed parameter is not owned, so the callee need not consume it --
	// and the caller still must.
	mustReport(t, borrowing+"func main() {\n    q := qubit()\n    peek(q)\n}\n", "q is not consumed")
}

func TestBranchesMustAgree(t *testing.T) {
	// L4: "Every branch of an `if` or `match` MUST leave the same set of linear
	// bindings live."
	mustReport(t, wrap("    q := qubit()\n    if true {\n        discard(q)\n    }"),
		"branches disagree about q")

	mustCheckClean(t, wrap(`    q := qubit()
    if true {
        discard(q)
    } else {
        reset(q)
    }`))

	// And across match arms.
	mustReport(t, `module t

enum Flag { On, Off, }

func main() {
    q := qubit()
    f := On
    match f {
        On  => discard(q),
        Off => print("no"),
    }
}
`, "branches disagree about q")

	mustCheckClean(t, `module t

enum Flag { On, Off, }

func main() {
    q := qubit()
    f := On
    match f {
        On  => discard(q),
        Off => reset(q),
    }
}
`)
}

func TestNoLinearCaptureOrSpawn(t *testing.T) {
	// L5: "A closure MUST NOT capture a linear value. A spawn'd call MUST NOT be
	// passed one. Both would make single-use unverifiable."
	mustReport(t, wrap(`    q := qubit()
    f := func() -> int {
        discard(q)
        return 1
    }
    print(f())`), "a closure cannot capture q, which is linear")

	mustReport(t, "module t\n\nfunc take(q: qubit) {\n    discard(q)\n}\n\nfunc main() {\n    q := qubit()\n    spawn take(q)\n}\n",
		"a spawned call cannot be passed q, which is linear")

	// A closure that allocates and consumes its own is fine.
	mustCheckClean(t, wrap(`    f := func() -> int {
        q := qubit()
        discard(q)
        return 1
    }
    print(f())`))
}

func TestLoopsMayNotConsumeOuterBindings(t *testing.T) {
	// L6: "A `while` or `for` body MUST NOT consume a linear binding declared
	// outside it, since the body runs an unknown number of times."
	mustReport(t, wrap(`    q := qubit()
    for i in range(0, 3) {
        discard(q)
    }`), "consumed inside a loop, but declared outside it")

	mustReport(t, wrap(`    q := qubit()
    while true {
        discard(q)
    }`), "consumed inside a loop")

	// A binding declared inside the body is the body's to consume.
	mustCheckClean(t, wrap(`    for i in range(0, 3) {
        q := qubit()
        discard(q)
    }`))
}

func TestQregIndexingIsABorrow(t *testing.T) {
	// "Indexing a qreg yields a mutable borrow of one qubit, not a move — the
	// register retains the obligation." (chapter 08 §Registers)
	mustCheckClean(t, "module t\n\nfunc peek(q: mut qubit) {\n    print(1)\n}\n\nfunc main() {\n    r := qreg[3]()\n    peek(r[0])\n    peek(r[1])\n    bits := measure_all(r)\n    print(len(bits))\n}\n")

	// The register itself still has to be consumed.
	mustReport(t, "module t\n\nfunc peek(q: mut qubit) {\n    print(1)\n}\n\nfunc main() {\n    r := qreg[3]()\n    peek(r[0])\n}\n",
		"r is not consumed")
}

func TestTwoMutBorrowsMustBeDistinct(t *testing.T) {
	// "Two `mut` borrows in one call MUST refer to distinct qubits. cnot(q, q)
	// is a compile error where aliasing is statically visible."
	src := "module t\n\nfunc pair(a: mut qubit, b: mut qubit) {\n    print(1)\n}\n\nfunc main() {\n"
	mustReport(t, src+"    q := qubit()\n    pair(q, q)\n    discard(q)\n}\n",
		"borrows q twice, and two mut borrows must be distinct")
	mustCheckClean(t, src+"    a := qubit()\n    b := qubit()\n    pair(a, b)\n    discard(a)\n    discard(b)\n}\n")
}

func TestLinearValuesMayNotBeComparedOrCopied(t *testing.T) {
	// Chapter 04: "Linear types MUST NOT be compared — comparison would read
	// them without consuming them."
	mustReport(t, wrap("    a := qubit()\n    b := qubit()\n    if a == b {\n        print(1)\n    }\n    discard(a)\n    discard(b)"),
		"linear values must not be compared")

	// Chapter 08: "There is no copy(q) and no way to write one."
	mustReport(t, wrap("    q := qubit()\n    r := copy(q)\n    discard(q)"),
		"copy is defined only on unrestricted types")

	// And printing one would read it without consuming it.
	mustReport(t, wrap("    q := qubit()\n    print(q)\n    discard(q)"), "cannot print qubit")
}

func TestDroppedLinearResult(t *testing.T) {
	// A returned linear value nobody binds is L1 too: it was produced and never
	// consumed. There is no implicit discard.
	mustReport(t, "module t\n\nfunc make() -> qubit {\n    return qubit()\n}\n\nfunc main() {\n    make()\n}\n",
		"the qubit returned by make is not consumed")
	mustCheckClean(t, "module t\n\nfunc make() -> qubit {\n    return qubit()\n}\n\nfunc main() {\n    q := make()\n    discard(q)\n}\n")
}
