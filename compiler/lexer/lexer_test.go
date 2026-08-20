package lexer

import (
	"testing"

	"github.com/bjornaer/ymir/compiler/diag"
	"github.com/bjornaer/ymir/compiler/token"
)

func lex(t *testing.T, src string) ([]token.Token, *diag.List) {
	t.Helper()
	errs := diag.NewList("test.ymr", src)
	return Tokens("test.ymr", src, errs), errs
}

func kinds(toks []token.Token) []token.Kind {
	out := make([]token.Kind, 0, len(toks))
	for _, tk := range toks {
		out = append(out, tk.Kind)
	}
	return out
}

func wantKinds(t *testing.T, src string, want ...token.Kind) []token.Token {
	t.Helper()
	toks, errs := lex(t, src)
	if !errs.Empty() {
		t.Fatalf("lexing %q: unexpected errors:\n%s", src, errs.Render())
	}
	got := kinds(toks)
	if len(got) != len(want) {
		t.Fatalf("lexing %q:\n got %v\nwant %v", src, got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("lexing %q: token %d is %v, want %v\n got %v\nwant %v",
				src, i, got[i], want[i], got, want)
		}
	}
	return toks
}

// The legacy lexer used the character class [+\-*/%=<>!@]+, so `x==-3` lexed as
// a single "==-" token and the program was rejected. Conformance case
// lexical/operator_munch.
func TestMaximalMunch(t *testing.T) {
	wantKinds(t, "x==-3",
		token.IDENT, token.EQL, token.SUB, token.INT, token.EOF)

	wantKinds(t, "a**=b",
		token.IDENT, token.POW_ASSIGN, token.IDENT, token.EOF)

	wantKinds(t, "a**b",
		token.IDENT, token.POW, token.IDENT, token.EOF)

	wantKinds(t, "a<=b>=c!=d==e",
		token.IDENT, token.LEQ, token.IDENT, token.GEQ, token.IDENT,
		token.NEQ, token.IDENT, token.EQL, token.IDENT, token.EOF)

	wantKinds(t, "a&&b||c",
		token.IDENT, token.LAND, token.IDENT, token.LOR, token.IDENT, token.EOF)

	// `|` is the union separator; `||` is logical or. Maximal munch keeps them
	// distinct without any context sensitivity (spec 01, spec 02 §Union types).
	wantKinds(t, "A|B",
		token.IDENT, token.OR, token.IDENT, token.EOF)
}

// `<-` is always one token, so `a<-b` is a send, never `a < -b` (spec 01).
func TestChannelOperatorIsOneToken(t *testing.T) {
	wantKinds(t, "a<-b",
		token.IDENT, token.CHAN_OP, token.IDENT, token.EOF)

	wantKinds(t, "a < -b",
		token.IDENT, token.LSS, token.SUB, token.IDENT, token.EOF)

	wantKinds(t, "v := <-ch",
		token.IDENT, token.DEFINE, token.CHAN_OP, token.IDENT, token.EOF)
}

func TestArrowsDistinctFromComparison(t *testing.T) {
	wantKinds(t, "-> => >= <= <-",
		token.ARROW, token.FATARROW, token.GEQ, token.LEQ, token.CHAN_OP, token.EOF)
}

// Legacy stored literals with their quotes attached, stripped them ad hoc in two
// places in the interpreter, and never decoded escapes: print("a\nb") printed a
// backslash. Conformance case lexical/string_escapes.
func TestStringEscapesAreDecoded(t *testing.T) {
	for _, tc := range []struct{ src, want string }{
		{`"hello"`, "hello"},
		{`"a\nb"`, "a\nb"},
		{`"say \"hi\""`, `say "hi"`},
		{`"tab\there"`, "tab\there"},
		{`"back\\slash"`, `back\slash`},
		{`"\u{48}\u{49}"`, "HI"},
		{`""`, ""},
	} {
		toks, errs := lex(t, tc.src)
		if !errs.Empty() {
			t.Errorf("lexing %s: %s", tc.src, errs.Render())
			continue
		}
		if toks[0].Kind != token.STRING {
			t.Errorf("lexing %s: kind is %v, want STRING", tc.src, toks[0].Kind)
			continue
		}
		if toks[0].Lit != tc.want {
			t.Errorf("lexing %s: got %q, want %q", tc.src, toks[0].Lit, tc.want)
		}
	}
}

func TestStringErrors(t *testing.T) {
	for _, src := range []string{
		`"unterminated`,
		"\"spans\nlines\"",
		`"bad escape \q"`,
		`"\u{}"`,
		`"\u{110000}"`,
	} {
		if _, errs := lex(t, src); errs.Empty() {
			t.Errorf("lexing %s: expected an error, got none", src)
		}
	}
}

func TestNumbers(t *testing.T) {
	for _, tc := range []struct {
		src  string
		kind token.Kind
	}{
		{"42", token.INT},
		{"1_000_000", token.INT},
		{"0xFF", token.INT},
		{"0o755", token.INT},
		{"0b1010", token.INT},
		{"3.14", token.FLOAT},
		{"1e-9", token.FLOAT},
		{"6.022e23", token.FLOAT},
		{"1_000.5", token.FLOAT},
		{"3i", token.IMAG},
		{"2.5i", token.IMAG},
		{"1e3i", token.IMAG},
	} {
		toks, errs := lex(t, tc.src)
		if !errs.Empty() {
			t.Errorf("lexing %s: %s", tc.src, errs.Render())
			continue
		}
		if toks[0].Kind != tc.kind {
			t.Errorf("lexing %s: kind is %v, want %v", tc.src, toks[0].Kind, tc.kind)
		}
	}
}

// Requiring a digit on both sides of the point is what makes `t.0` unambiguous
// (spec 01 §Float).
func TestFloatNeedsDigitAfterPoint(t *testing.T) {
	if _, errs := lex(t, "x := 1."); errs.Empty() {
		t.Error("`1.` should be a lexical error")
	}
	// `.5` is not a float: the '.' lexes as a selector.
	wantKinds(t, "t.0", token.IDENT, token.PERIOD, token.INT, token.EOF)
}

// Comments are discarded and never reach the parser (spec 01 §Comments).
func TestCommentsAreDiscarded(t *testing.T) {
	wantKinds(t, "x # trailing comment\ny",
		token.IDENT, token.SEMI, token.IDENT, token.EOF)

	wantKinds(t, "# leading only\n", token.EOF)
}

// Spec 01 §Semicolons: a newline ends a statement unless the line's last token
// cannot end one.
func TestStatementTerminators(t *testing.T) {
	// Trailing binary operator: the statement continues.
	wantKinds(t, "total := a +\n b",
		token.IDENT, token.DEFINE, token.IDENT, token.ADD, token.IDENT, token.EOF)

	// Unclosed paren: the statement continues across lines, and the closing
	// paren then terminates it.
	wantKinds(t, "f(\n x,\n y,\n)\ng",
		token.IDENT, token.LPAREN, token.IDENT, token.COMMA, token.IDENT,
		token.COMMA, token.RPAREN, token.SEMI, token.IDENT, token.EOF)

	// Two statements on one line, separated explicitly.
	wantKinds(t, "a; b",
		token.IDENT, token.SEMI, token.IDENT, token.EOF)

	// A blank line does not produce a second terminator.
	wantKinds(t, "a\n\n\nb",
		token.IDENT, token.SEMI, token.IDENT, token.EOF)

	// A comment must not suppress the terminator on its line.
	wantKinds(t, "a # note\nb",
		token.IDENT, token.SEMI, token.IDENT, token.EOF)
}

// Type names are predeclared identifiers, not keywords, so `func str(...)` stays
// parseable (spec 01 §Keywords).
func TestTypeNamesAreIdentifiers(t *testing.T) {
	toks := wantKinds(t, "int float string bool any array map matrix complex error",
		token.IDENT, token.IDENT, token.IDENT, token.IDENT, token.IDENT,
		token.IDENT, token.IDENT, token.IDENT, token.IDENT, token.IDENT, token.EOF)
	if toks[0].Lit != "int" {
		t.Errorf("literal is %q, want \"int\"", toks[0].Lit)
	}
}

func TestKeywords(t *testing.T) {
	wantKinds(t, "func if else while for in return try match enum struct",
		token.FUNC, token.IF, token.ELSE, token.WHILE, token.FOR, token.IN,
		token.RETURN, token.TRY, token.MATCH, token.ENUM, token.STRUCT, token.EOF)

	// Reserved for the quantum fragment: unusable as identifiers now, so adding
	// the feature later breaks nothing (spec 01).
	wantKinds(t, "qubit measure reset discard gate",
		token.QUBIT, token.MEASURE, token.RESET, token.DISCARD, token.GATE, token.EOF)
}

func TestPositions(t *testing.T) {
	src := "module m\n\nfunc main() {\n    print(x)\n}\n"
	toks, errs := lex(t, src)
	if !errs.Empty() {
		t.Fatalf("unexpected errors:\n%s", errs.Render())
	}
	var printTok token.Token
	for _, tk := range toks {
		if tk.Kind == token.IDENT && tk.Lit == "print" {
			printTok = tk
		}
	}
	if printTok.Pos.Line != 4 {
		t.Errorf("print is on line %d, want 4", printTok.Pos.Line)
	}
	if printTok.Pos.Column != 5 {
		t.Errorf("print is at column %d, want 5", printTok.Pos.Column)
	}
}

func TestUnexpectedCharacterRecovers(t *testing.T) {
	// Lexing must make progress past a bad character so the caller sees them all.
	toks, errs := lex(t, "a $ b ~ c")
	if errs.Len() != 2 {
		t.Errorf("got %d errors, want 2:\n%s", errs.Len(), errs.Render())
	}
	if toks[len(toks)-1].Kind != token.EOF {
		t.Error("lexing did not reach EOF")
	}
}

// ':' is a delimiter but also the prefix of ':='. Operators are matched before
// delimiters so ':=' stays reachable.
func TestColonVsDefine(t *testing.T) {
	wantKinds(t, "var x: int = 0",
		token.VAR, token.IDENT, token.COLON, token.IDENT, token.ASSIGN,
		token.INT, token.EOF)

	wantKinds(t, "x := 0",
		token.IDENT, token.DEFINE, token.INT, token.EOF)

	wantKinds(t, "m := {\"a\": 1}",
		token.IDENT, token.DEFINE, token.LBRACE, token.STRING, token.COLON,
		token.INT, token.RBRACE, token.EOF)
}
