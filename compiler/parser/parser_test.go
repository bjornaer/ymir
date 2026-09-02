package parser

import (
	"strings"
	"testing"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
)

func parseOK(t *testing.T, src string) *ast.File {
	t.Helper()
	f, errs := ParseFile("test.ymr", src)
	if !errs.Empty() {
		t.Fatalf("unexpected errors parsing:\n%s\n%s", src, errs.Render())
	}
	return f
}

// parseErr asserts that parsing fails and that some diagnostic mentions want.
func parseErr(t *testing.T, src, want string) {
	t.Helper()
	_, errs := ParseFile("test.ymr", src)
	if errs.Empty() {
		t.Fatalf("expected an error mentioning %q, got none, parsing:\n%s", want, src)
	}
	if !strings.Contains(errs.Render(), want) {
		t.Fatalf("expected an error mentioning %q, got:\n%s", want, errs.Render())
	}
}

// wrap puts stmts inside a module and a main function.
func wrap(stmts string) string {
	return "module t\n\nfunc main() {\n" + stmts + "\n}\n"
}

// A call's callee is an expression, never a name. The legacy AST stored it as a
// string, which made function values structurally inexpressible.
func TestCalleeIsAnExpression(t *testing.T) {
	f := parseOK(t, wrap("    fs[0](1, 2)\n    obj.method()\n    get()()"))
	body := f.Decls[0].(*ast.FuncDecl).Body

	if _, ok := body.Stmts[0].(*ast.ExprStmt).X.(*ast.CallExpr).Fun.(*ast.IndexExpr); !ok {
		t.Error("callee of fs[0](...) is not an IndexExpr")
	}
	if _, ok := body.Stmts[1].(*ast.ExprStmt).X.(*ast.CallExpr).Fun.(*ast.SelectorExpr); !ok {
		t.Error("callee of obj.method() is not a SelectorExpr")
	}
	if _, ok := body.Stmts[2].(*ast.ExprStmt).X.(*ast.CallExpr).Fun.(*ast.CallExpr); !ok {
		t.Error("callee of get()() is not a CallExpr")
	}
}

// Identifiers are nodes with positions, never bare strings.
func TestIdentifiersAreNodes(t *testing.T) {
	f := parseOK(t, wrap("    x := 1"))
	body := f.Decls[0].(*ast.FuncDecl).Body
	lhs := body.Stmts[0].(*ast.AssignStmt).Lhs[0]
	id, ok := lhs.(*ast.Ident)
	if !ok {
		t.Fatalf("assignment target is %T, want *ast.Ident", lhs)
	}
	if id.Pos().Line != 4 || id.Pos().Column != 5 {
		t.Errorf("ident position is %s, want 4:5", id.Pos())
	}
}

// Precedence follows the table in spec 04.
func TestPrecedence(t *testing.T) {
	for _, tc := range []struct{ src, want string }{
		{"a + b * c", "(a + (b * c))"},
		{"a * b + c", "((a * b) + c)"},
		{"a + b < c", "((a + b) < c)"},
		{"a < b == c", "((a < b) == c)"},
		{"a == b && c", "((a == b) && c)"},
		{"a && b || c", "((a && b) || c)"},
		{"a @ b + c", "((a @ b) + c)"},
		// ** is the one right-associative operator: 2 ** 3 ** 2 is 512.
		{"a ** b ** c", "(a ** (b ** c))"},
		{"a ** b * c", "((a ** b) * c)"},
		{"-a ** b", "(-(a ** b))"},
	} {
		f := parseOK(t, wrap("    x := "+tc.src))
		body := f.Decls[0].(*ast.FuncDecl).Body
		got := render(body.Stmts[0].(*ast.AssignStmt).Rhs[0])
		if got != tc.want {
			t.Errorf("%s parsed as %s, want %s", tc.src, got, tc.want)
		}
	}
}

// render writes an expression in fully parenthesized form, for precedence tests.
func render(e ast.Expr) string {
	switch x := e.(type) {
	case *ast.Ident:
		return x.Name
	case *ast.BasicLit:
		return x.Value
	case *ast.BinaryExpr:
		return "(" + render(x.X) + " " + x.Op.String() + " " + render(x.Y) + ")"
	case *ast.UnaryExpr:
		return "(" + x.Op.String() + render(x.X) + ")"
	case *ast.ParenExpr:
		return render(x.X)
	}
	return "?"
}

func TestDeclarations(t *testing.T) {
	f := parseOK(t, `module m

import stdlib.math
import stdlib.io as io

const PI: float = 3.14159

export struct Point {
    x: float,
    y: float,
}

enum Shape {
    Circle(float),
    Rect(float, float),
    Point,
}

export func area(s: Shape) -> float {
    return 0.0
}

func (p: mut Point) scale(k: float) {
    p.x = p.x * k
}

gate bell(a: mut qubit, b: mut qubit) {
    h(a)
}
`)
	if len(f.Imports) != 2 {
		t.Errorf("got %d imports, want 2", len(f.Imports))
	}
	if f.Imports[1].Alias == nil || f.Imports[1].Alias.Name != "io" {
		t.Error("import alias not parsed")
	}
	if len(f.Decls) != 6 {
		t.Fatalf("got %d declarations, want 6", len(f.Decls))
	}
	if s, ok := f.Decls[1].(*ast.StructDecl); !ok || !s.Export || len(s.Fields) != 2 {
		t.Error("struct not parsed as expected")
	}
	if e, ok := f.Decls[2].(*ast.EnumDecl); !ok || len(e.Variants) != 3 {
		t.Error("enum not parsed as expected")
	} else if len(e.Variants[1].Payload) != 2 {
		t.Error("enum variant payload not parsed")
	}
	if m, ok := f.Decls[4].(*ast.FuncDecl); !ok || m.Recv == nil || !m.Recv.Mut {
		t.Error("method receiver not parsed as mut")
	}
	if g, ok := f.Decls[5].(*ast.FuncDecl); !ok || !g.IsGate {
		t.Error("gate not parsed")
	}
}

// Error sets: `-> (T, A | B)` (spec 06).
func TestErrorSetTypes(t *testing.T) {
	f := parseOK(t, `module m

func load(p: string) -> (Config, IOError | ParseError) {
    return zero, nil
}
`)
	fn := f.Decls[0].(*ast.FuncDecl)
	if len(fn.Results) != 2 {
		t.Fatalf("got %d results, want 2", len(fn.Results))
	}
	u, ok := fn.Results[1].(*ast.UnionType)
	if !ok {
		t.Fatalf("second result is %T, want *ast.UnionType", fn.Results[1])
	}
	if len(u.Members) != 2 {
		t.Errorf("union has %d members, want 2", len(u.Members))
	}
	if !fn.HasErrorPosition() {
		t.Error("HasErrorPosition is false for a two-result function")
	}
}

func TestTryExpr(t *testing.T) {
	f := parseOK(t, wrap("    data := try readFile(path)"))
	body := f.Decls[0].(*ast.FuncDecl).Body
	if _, ok := body.Stmts[0].(*ast.AssignStmt).Rhs[0].(*ast.TryExpr); !ok {
		t.Error("try not parsed as a TryExpr")
	}
	// `try` binds tighter than any binary operator.
	f = parseOK(t, wrap("    n := try f() + 1"))
	body = f.Decls[0].(*ast.FuncDecl).Body
	bin, ok := body.Stmts[0].(*ast.AssignStmt).Rhs[0].(*ast.BinaryExpr)
	if !ok {
		t.Fatal("try f() + 1 did not parse as a binary expression")
	}
	if _, ok := bin.X.(*ast.TryExpr); !ok {
		t.Error("try did not bind tighter than +")
	}
}

func TestTryNeedsACall(t *testing.T) {
	parseErr(t, wrap("    x := try y"), "`try` applies to a call")
}

func TestMatch(t *testing.T) {
	f := parseOK(t, wrap(`    match err {
        IOError.NotFound(p)      => print(p),
        ParseError.UnexpectedEOF => print("eof"),
        nil                      => print("ok"),
        _                        => print("other"),
    }`))
	body := f.Decls[0].(*ast.FuncDecl).Body
	m, ok := body.Stmts[0].(*ast.MatchStmt)
	if !ok {
		t.Fatalf("statement is %T, want *ast.MatchStmt", body.Stmts[0])
	}
	if len(m.Arms) != 4 {
		t.Fatalf("got %d arms, want 4", len(m.Arms))
	}
	if m.Arms[0].Pattern.Enum == nil || m.Arms[0].Pattern.Enum.Name != "IOError" {
		t.Error("qualified pattern's enum not parsed")
	}
	if len(m.Arms[0].Pattern.Binds) != 1 {
		t.Error("pattern binding not parsed")
	}
	if !m.Arms[2].Pattern.IsNil {
		t.Error("nil pattern not recognized")
	}
	if !m.Arms[3].Pattern.IsWildcard {
		t.Error("wildcard pattern not recognized")
	}
}

func TestMatchBlockArm(t *testing.T) {
	parseOK(t, wrap(`    match x {
        A => {
            y = 1
            print(y)
        }
        B => print("b"),
    }`))
}

// A comma in a single-statement arm terminates the arm, so it cannot also
// separate return values. The parser distinguishes the two rather than guessing.
func TestMatchArmMultiValueReturn(t *testing.T) {
	parseErr(t, wrap(`    match e {
        A => return 1, 2,
        B => return 3, 4,
    }`), "cannot return multiple values")

	// The same shape with a single value per arm, and a trailing comma, is fine.
	parseOK(t, wrap(`    match e {
        Circle(r)  => return 1.0,
        Rect(w, h) => return w * h,
    }`))
}

// Spec 09 §1: a composite literal must not appear unparenthesized at the top
// level of a control-flow header, since `{` opens the body there.
func TestCompositeLiteralInControlHeader(t *testing.T) {
	// `{` after the condition opens the body, not a map literal.
	f := parseOK(t, wrap("    if ok {\n        print(1)\n    }"))
	body := f.Decls[0].(*ast.FuncDecl).Body
	if _, ok := body.Stmts[0].(*ast.IfStmt); !ok {
		t.Error("if statement not parsed")
	}
	// Inside a call's parentheses a composite literal is unambiguous again.
	parseOK(t, wrap("    if eq(Point{x: 1.0}) {\n        print(1)\n    }"))
	// And a struct literal is fine outside a header.
	parseOK(t, wrap("    p := Point{x: 1.0, y: 2.0}"))
}

func TestForms(t *testing.T) {
	parseOK(t, wrap("    for x in xs {\n        print(x)\n    }"))
	parseOK(t, wrap("    for i, x in enumerate(xs) {\n        print(x)\n    }"))
	parseOK(t, wrap("    for i := 0; i < 10; i = i + 1 {\n        print(i)\n    }"))
	parseOK(t, wrap("    while ok {\n        break\n    }"))
}

func TestChannels(t *testing.T) {
	f := parseOK(t, wrap("    ch <- 42\n    v := <-ch\n    spawn worker(1, ch)"))
	body := f.Decls[0].(*ast.FuncDecl).Body
	if _, ok := body.Stmts[0].(*ast.SendStmt); !ok {
		t.Errorf("ch <- 42 parsed as %T, want *ast.SendStmt", body.Stmts[0])
	}
	if _, ok := body.Stmts[2].(*ast.SpawnStmt); !ok {
		t.Errorf("spawn parsed as %T, want *ast.SpawnStmt", body.Stmts[2])
	}
}

func TestSelect(t *testing.T) {
	parseOK(t, wrap(`    select {
        case v := <-inCh:
            print(v)
        case out <- x:
            print(1)
        case default:
            print(2)
    }`))
}

func TestTupleVsParen(t *testing.T) {
	f := parseOK(t, wrap("    a := (1)\n    b := (1,)\n    c := (1, 2)"))
	body := f.Decls[0].(*ast.FuncDecl).Body
	if _, ok := body.Stmts[0].(*ast.AssignStmt).Rhs[0].(*ast.ParenExpr); !ok {
		t.Error("(1) is not a ParenExpr")
	}
	if _, ok := body.Stmts[1].(*ast.AssignStmt).Rhs[0].(*ast.TupleLit); !ok {
		t.Error("(1,) is not a TupleLit")
	}
	if _, ok := body.Stmts[2].(*ast.AssignStmt).Rhs[0].(*ast.TupleLit); !ok {
		t.Error("(1, 2) is not a TupleLit")
	}
}

func TestTupleIndexVsSelector(t *testing.T) {
	f := parseOK(t, wrap("    a := t.0\n    b := p.x"))
	body := f.Decls[0].(*ast.FuncDecl).Body
	if _, ok := body.Stmts[0].(*ast.AssignStmt).Rhs[0].(*ast.TupleIndexExpr); !ok {
		t.Error("t.0 is not a TupleIndexExpr")
	}
	if _, ok := body.Stmts[1].(*ast.AssignStmt).Rhs[0].(*ast.SelectorExpr); !ok {
		t.Error("p.x is not a SelectorExpr")
	}
}

func TestFuncLitAndFuncType(t *testing.T) {
	parseOK(t, wrap("    f := func(a: int) -> int { return a + 1 }"))
	parseOK(t, `module m
func apply(xs: array[int], f: func(int) -> int) -> array[int] {
    return xs
}
`)
}

// Spec 05: only a call may stand alone as a statement.
func TestBareExpressionIsNotAStatement(t *testing.T) {
	parseErr(t, wrap("    x + 1"), "expression is not a statement")
}

// Spec 05: ++ and -- are statements, so `y = x++` is a syntax error.
func TestIncDecIsAStatement(t *testing.T) {
	parseOK(t, wrap("    x++"))
	parseErr(t, wrap("    y = x++"), "expected")
}

// Spec 03: a module body holds only declarations.
func TestTopLevelStatementRejected(t *testing.T) {
	parseErr(t, "module m\n\nprint(1)\n", "expected a declaration")
}

func TestModuleDeclarationRequired(t *testing.T) {
	parseErr(t, "func main() {}\n", "must begin with a module declaration")
}

// Spec 03: `var` cannot be exported; there are no mutable globals.
func TestExportedVarRejected(t *testing.T) {
	parseErr(t, "module m\n\nexport var x: int = 0\n", "cannot be exported")
}

// Spec 02: parameters are always annotated.
func TestParameterNeedsType(t *testing.T) {
	parseErr(t, "module m\n\nfunc f(a) {}\n", "needs a type annotation")
}

// One syntax error must not cascade: the parser recovers at statement
// boundaries and keeps reporting real problems after it.
func TestRecoveryDoesNotCascade(t *testing.T) {
	_, errs := ParseFile("test.ymr", wrap("    x + 1\n    y + 2\n    z + 3"))
	if errs.Len() != 3 {
		t.Errorf("got %d errors, want 3 (one per bad statement):\n%s",
			errs.Len(), errs.Render())
	}
}

// Every diagnostic carries a file, line, and column, and renders with a source
// excerpt. This is a Phase 1 requirement, not later polish.
func TestDiagnosticsHavePositionAndExcerpt(t *testing.T) {
	_, errs := ParseFile("example.ymr", wrap("    x + 1"))
	if errs.Empty() {
		t.Fatal("expected an error")
	}
	out := errs.Render()
	for _, want := range []string{"example.ymr:4:5", "x + 1", "^"} {
		if !strings.Contains(out, want) {
			t.Errorf("rendered diagnostic missing %q:\n%s", want, out)
		}
	}
}

// `?T` is a general type former, not a rule about position (spec 02 §Nullable
// types). It may appear on results, parameters, and collection elements alike.
// qreg[N] is the one parameterized type whose argument is a compile-time integer
// rather than a type (grammar 09 §Types). It did not parse until Phase 2 M3
// found it: no conformance case used qreg, so nothing caught the gap.
func TestQregWidth(t *testing.T) {
	f := parseOK(t, wrap("    var r: qreg[4]"))
	v := f.Decls[0].(*ast.FuncDecl).Body.Stmts[0].(*ast.VarDecl)
	g, ok := v.Type.(*ast.GenericType)
	if !ok {
		t.Fatalf("qreg[4] is a %T, want *ast.GenericType", v.Type)
	}
	if g.Width == nil {
		t.Fatal("qreg[4] parsed with no Width; the integer argument was dropped")
	}
	if g.Width.Value != "4" {
		t.Errorf("Width = %q, want %q", g.Width.Value, "4")
	}
	if len(g.Args) != 0 {
		t.Errorf("Args = %d, want 0: a width is not a type argument", len(g.Args))
	}
	// The width must survive rendering, or `ymir parse` shows a type that is
	// not the one in the source.
	if got := ast.Sprint(v); !strings.Contains(got, "qreg[4]") {
		t.Errorf("printed as %q, want it to contain %q", got, "qreg[4]")
	}
}

// Only qreg takes an integer. Everything else still requires a type.
func TestIntegerArgumentIsOnlyForQreg(t *testing.T) {
	parseErr(t, wrap("    var xs: array[4]"), "expected a type")
}

// A complex literal is `a ± bi`, folded here rather than lexed (R7). Lexing it
// as one token would make the language depend on whitespace.
func TestComplexLiteralFold(t *testing.T) {
	tests := []struct{ src, want string }{
		{"1.0 + 2.0i", "1.0+2.0i"},
		{"1.0+2.0i", "1.0+2.0i"}, // spacing does not matter
		{"1.0 - 2.0i", "1.0-2.0i"},
		{"-1.0 + 2.0i", "-1.0+2.0i"},
		{"1 + 2i", "1+2i"},
		{"2.0i", "2.0i"}, // a bare imaginary is already complex
	}
	for _, tc := range tests {
		f := parseOK(t, wrap("    z := "+tc.src))
		rhs := f.Decls[0].(*ast.FuncDecl).Body.Stmts[0].(*ast.AssignStmt).Rhs[0]
		lit, ok := rhs.(*ast.BasicLit)
		if !ok {
			t.Errorf("%s parsed as %T, want a folded *ast.BasicLit", tc.src, rhs)
			continue
		}
		if lit.Kind != token.IMAG {
			t.Errorf("%s has kind %s, want IMAG", tc.src, lit.Kind)
		}
		if lit.Value != tc.want {
			t.Errorf("%s folded to %q, want %q", tc.src, lit.Value, tc.want)
		}
	}
}

// Only literals fold. A binding on either side stays a binary expression, so
// the checker can reject it — there is no implicit conversion.
func TestComplexFoldRequiresLiterals(t *testing.T) {
	for _, src := range []string{"x + 2.0i", "1.0 + y", "1.0 * 2.0i"} {
		f := parseOK(t, wrap("    x := 1.0\n    y := 2.0i\n    z := "+src))
		rhs := f.Decls[0].(*ast.FuncDecl).Body.Stmts[2].(*ast.AssignStmt).Rhs[0]
		if _, folded := rhs.(*ast.BasicLit); folded {
			t.Errorf("%s folded into a literal; only literal operands may fold", src)
		}
	}
}

func TestNullableTypes(t *testing.T) {
	f := parseOK(t, `module m

func find(xs: array[int]) -> ?int {
    return nil
}

func describe(e: ?IOError, tags: array[?string]) -> ?string {
    return nil
}

func load(p: string) -> (int, ?(IOError | ParseError)) {
    return 0, nil
}
`)
	find := f.Decls[0].(*ast.FuncDecl)
	if _, ok := find.Results[0].(*ast.NullableType); !ok {
		t.Errorf("result of find is %T, want *ast.NullableType", find.Results[0])
	}

	desc := f.Decls[1].(*ast.FuncDecl)
	if _, ok := desc.Params[0].Type.(*ast.NullableType); !ok {
		t.Error("nullable parameter not parsed")
	}
	elem := desc.Params[1].Type.(*ast.GenericType).Args[0]
	if _, ok := elem.(*ast.NullableType); !ok {
		t.Error("nullable array element not parsed")
	}

	// `?(A | B)` parenthesizes the union; `?A | B` is not the same shape, which
	// is why the grammar requires the parens.
	load := f.Decls[2].(*ast.FuncDecl)
	n, ok := load.Results[1].(*ast.NullableType)
	if !ok {
		t.Fatalf("error position is %T, want *ast.NullableType", load.Results[1])
	}
	if u, ok := n.Elem.(*ast.UnionType); !ok || len(u.Members) != 2 {
		t.Error("?(A | B) did not parse as a nullable union")
	}
}
