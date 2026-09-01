package check_test

import (
	"strings"
	"testing"
)

// errorsFor checks a source string and returns the rendered diagnostics.
func errorsFor(t *testing.T, src string) string {
	t.Helper()
	_, rendered := checkSrc(t, src)
	return rendered
}

// mustCheckClean fails when a program that should be legal is rejected. Half of
// a checker's bugs are false positives, and they are the half that makes a
// language unusable.
func mustCheckClean(t *testing.T, src string) {
	t.Helper()
	if got := errorsFor(t, src); strings.TrimSpace(got) != "" {
		t.Errorf("expected no diagnostics, got:\n%s", got)
	}
}

// mustReport fails unless exactly the given substrings appear in the output.
func mustReport(t *testing.T, src string, subs ...string) {
	t.Helper()
	got := errorsFor(t, src)
	if strings.TrimSpace(got) == "" {
		t.Fatalf("expected a diagnostic mentioning %q, got none", subs)
	}
	for _, sub := range subs {
		if !strings.Contains(got, sub) {
			t.Errorf("diagnostics do not mention %q:\n%s", sub, got)
		}
	}
}

func TestScopeChainOrder(t *testing.T) {
	// A parameter shadows a module-level var, and a block binding shadows the
	// parameter. Resolution is innermost first (chapter 03 §Scope).
	mustCheckClean(t, `module t

var total: int = 0

func bump(total: int) {
    if true {
        total := 3
        print(total)
    }
    print(total)
}

func main() {
    bump(1)
    print(total)
}
`)
}

func TestModuleVarIsVisibleInsideFunctions(t *testing.T) {
	// Normative in chapter 03 §Scope, and the legacy implementation failed it
	// with "Undefined variable: total".
	mustCheckClean(t, `module t

var total: int = 0

func bump() {
    total = total + 10
}

func main() {
    bump()
    print(total)
}
`)
}

func TestModuleDeclarationsAreOrderIndependent(t *testing.T) {
	// Stated in chapter 03 §Scope as of M0. A function may call one declared
	// below it, and a struct field may name a type declared later.
	mustCheckClean(t, `module t

func main() {
    print(later())
}

func later() -> int {
    return 1
}

struct Outer {
    inner: Inner,
}

struct Inner {
    n: int,
}
`)
}

func TestMutuallyRecursiveTypes(t *testing.T) {
	// Type names are collected before any field is resolved, so two structs may
	// name each other. Reference semantics on array make the cycle finite.
	mustCheckClean(t, `module t

struct Node {
    kids: array[Node],
}

func main() {
    print(1)
}
`)
}

func TestBlockBindingDoesNotEscape(t *testing.T) {
	mustReport(t, wrap(`    if true {
        inner := 1
        print(inner)
    }
    print(inner)`), "undefined: inner")
}

func TestLoopHeaderBindingsAreScopedToTheLoop(t *testing.T) {
	// "The init clause's bindings are scoped to the loop" (chapter 05 §for).
	mustReport(t, wrap(`    for i := 0; i < 3; i = i + 1 {
        print(i)
    }
    print(i)`), "undefined: i")

	// The same for `for x in xs`.
	mustReport(t, wrap(`    xs := [1, 2]
    for x in xs {
        print(x)
    }
    print(x)`), "undefined: x")
}

func TestPatternBindingsAreScopedToTheirArm(t *testing.T) {
	// "Bindings introduced by a pattern are scoped to that arm."
	mustReport(t, `module t

enum Shape {
    Circle(float),
    Point,
}

func main() {
    s := Circle(1.0)
    match s {
        Circle(r) => print(r),
        Point     => print(0.0),
    }
    print(r)
}
`, "undefined: r")
}

func TestSelectCaseBindingIsScopedToTheCase(t *testing.T) {
	mustReport(t, wrap(`    ch := make_chan[int](1)
    select {
        case v := <-ch: print(v)
        case default:   print(0)
    }
    print(v)`), "undefined: v")
}

func TestRedeclarationInTheSameScope(t *testing.T) {
	// Ymir is stricter than Go here: chapter 03 §Variables makes redeclaring a
	// name bound in the same scope an error, with no "at least one is new"
	// exception.
	mustReport(t, wrap("    x := 1\n    x := 2\n    print(x)"), "redeclared")
	mustReport(t, wrap("    a := 1\n    a, b := 2, 3\n    print(a + b)"), "redeclared")

	// Shadowing in a nested scope stays legal.
	mustCheckClean(t, wrap("    x := 1\n    if true {\n        x := 2\n        print(x)\n    }\n    print(x)"))
}

func TestUniverseNamesCanBeShadowed(t *testing.T) {
	// "Type names are not keywords ... They can be shadowed by a local
	// binding, which is legal but a lint warning" (chapter 01 §Keywords). A
	// lint warning is not an error, and diag has no warning severity, so this
	// must check clean.
	mustCheckClean(t, wrap("    string := 1\n    print(string)"))
}

func TestUndefinedNameIsAnError(t *testing.T) {
	mustReport(t, wrap("    var count: int = 5\n    print(cuont + 1)"), "undefined: cuont")
}

func TestAssignmentTargets(t *testing.T) {
	mustReport(t, "module t\n\nconst LIMIT: int = 1\n\nfunc main() {\n    LIMIT = 2\n}\n",
		"cannot assign to constant")

	// A non-`mut` parameter is a copy; writing through it is meaningless (R6).
	mustReport(t, "module t\n\nfunc f(n: int) {\n    n = 2\n}\n\nfunc main() {\n    f(1)\n}\n",
		"not mutable")

	// A `mut` parameter is a mutable reference.
	mustCheckClean(t, "module t\n\nfunc f(n: mut int) {\n    n = 2\n}\n\nfunc main() {\n    f(1)\n}\n")

	mustReport(t, wrap("    undeclared = 1"), "undefined: undeclared")
}

func TestBlankIdentifier(t *testing.T) {
	// It may be written to and never read (chapter 01 §Identifiers).
	mustCheckClean(t, wrap("    _ = 1"))
	mustReport(t, wrap("    _ = 1\n    print(_)"), "blank identifier")

	// It may be a match binding, and several `_` in one pattern do not collide.
	mustCheckClean(t, `module t

enum Pair {
    Both(int, int),
}

func main() {
    p := Both(1, 2)
    match p {
        Both(_, _) => print("two"),
    }
}
`)
}

func TestBranchOutsideALoop(t *testing.T) {
	mustReport(t, wrap("    break"), "break outside a loop")
	mustReport(t, wrap("    continue"), "continue outside a loop")

	// Inside any loop form, and inside a nested block within one, it is fine.
	mustCheckClean(t, wrap("    while true {\n        break\n    }"))
	mustCheckClean(t, wrap("    for i := 0; i < 3; i = i + 1 {\n        if true {\n            continue\n        }\n    }"))

	// A match arm inside a loop still counts as inside the loop; a match does
	// not reset the depth, because there is no `break` out of a match.
	mustCheckClean(t, `module t

enum Flag {
    On,
    Off,
}

func main() {
    f := On
    while true {
        match f {
            On  => break,
            Off => continue,
        }
    }
}
`)
}

func TestModuleIsNotAValue(t *testing.T) {
	mustReport(t, "module t\n\nimport stdlib.math\n\nfunc main() {\n    print(math)\n}\n",
		"is not a value")

	// A member of an imported module is accepted unchecked: resolving it needs
	// the module's declarations, which do not exist before Phase 6.
	mustCheckClean(t, "module t\n\nimport stdlib.math\n\nfunc main() {\n    print(math.sqrt(4.0))\n}\n")
}

func TestImportAliasBindsTheAlias(t *testing.T) {
	mustCheckClean(t, "module t\n\nimport stdlib.io as out\n\nfunc main() {\n    out.write(\"x\")\n}\n")

	// The alias replaces the last path element rather than adding to it.
	mustReport(t, "module t\n\nimport stdlib.io as out\n\nfunc main() {\n    io.write(\"x\")\n}\n",
		"undefined: io")
}

func TestQualifiedVariantMustExist(t *testing.T) {
	mustReport(t, `module t

enum IOError {
    NotFound(string),
}

func main() {
    e := IOError.Nope("x")
    print(1)
}
`, "has no variant Nope")
}

func TestContainerOfLinearIsIllFormed(t *testing.T) {
	// R8. qreg[N] is the collection-of-qubits type; an array's length is a
	// runtime value, so L1 cannot be proved for one.
	for _, container := range []string{
		"array[qubit]",
		"map[string, qubit]",
		"chan[qubit]",
		"tuple[qubit, int]",
	} {
		mustReport(t, "module t\n\nfunc f(x: "+container+") {\n    print(1)\n}\n\nfunc main() {\n    print(1)\n}\n",
			"which is linear")
	}

	// A struct may hold a linear field: its shape is static.
	mustCheckClean(t, `module t

struct Holder {
    q: qubit,
}

func main() {
    print(1)
}
`)
}

func TestUnqualifiedVariantConstruction(t *testing.T) {
	// "Construction names the variant; where ambiguous, qualify it."
	mustCheckClean(t, `module t

enum Shape {
    Circle(float),
    Point,
}

func main() {
    a := Circle(1.0)
    b := Shape.Point
    print(1)
}
`)

	// Ambiguous means the bare name belongs to two enums in the module.
	mustReport(t, `module t

enum Shape {
    Point,
}

enum Marker {
    Point,
}

func main() {
    s := Point
    print(1)
}
`, "ambiguous variant Point", "Marker.Point or Shape.Point")

	// An ordinary binding shadows a variant rather than colliding with it.
	mustCheckClean(t, `module t

enum Shape {
    Circle(float),
}

func main() {
    Circle := 1
    print(Circle)
}
`)
}

func TestGenericArity(t *testing.T) {
	mustReport(t, wrap("    var m: map[string]"), "map takes 2 type arguments")
	mustReport(t, wrap("    var xs: array[int, int]"), "array takes 1 type argument")
	mustReport(t, wrap("    var xs: array"), "array needs type arguments")
	mustReport(t, wrap("    var r: qreg[0]"), "positive integer")
}

func TestUserTypesTakeNoTypeArguments(t *testing.T) {
	// Until Q3 is answered, nothing a user declares is parameterized.
	mustReport(t, `module t

struct Box {
    n: int,
}

func main() {
    var b: Box[int]
    print(1)
}
`, "does not take type arguments")
}
