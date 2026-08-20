// Package token defines the lexical tokens of Ymir and their source positions.
//
// See docs/spec/01-lexical.md. The operator set is closed and matched by longest
// prefix; it is never a character class. The legacy implementation used the class
// [+\-*/%=<>!@]+, which lexes x==-3 as a single "==-" token.
package token

import "fmt"

type Kind int

const (
	INVALID Kind = iota
	EOF
	SEMI // statement terminator: an explicit ';' or a significant newline

	IDENT
	INT
	FLOAT
	IMAG
	STRING

	// Keywords. Type names are NOT keywords; they are predeclared identifiers,
	// so `func str(...)` stays parseable (spec 01, §Keywords).
	keywordStart
	BREAK
	CASE
	CONST
	CONTINUE
	ELSE
	ENUM
	EXPORT
	FALSE
	FOR
	FUNC
	IF
	IMPORT
	IN
	MATCH
	MODULE
	MUT
	NIL
	RETURN
	SELECT
	SPAWN
	STRUCT
	TRUE
	TRY
	VAR
	WHILE
	// Reserved for the quantum fragment (spec 08). Unusable as identifiers even
	// before implementation, so adding them later breaks no existing program.
	DISCARD
	GATE
	MEASURE
	QUBIT
	RESET
	keywordEnd

	operatorStart
	ADD // +
	SUB // -
	MUL // *
	QUO // /
	REM // %
	POW // **
	AT  // @

	ASSIGN     // =
	DEFINE     // :=
	ADD_ASSIGN // +=
	SUB_ASSIGN // -=
	MUL_ASSIGN // *=
	QUO_ASSIGN // /=
	REM_ASSIGN // %=
	POW_ASSIGN // **=

	INC // ++
	DEC // --

	EQL // ==
	NEQ // !=
	LSS // <
	LEQ // <=
	GTR // >
	GEQ // >=

	LAND // &&
	LOR  // ||
	NOT  // !

	AND      // &
	OR       // |  union type separator (spec 02, §Union types)
	ARROW    // -> function result
	FATARROW // => match arm
	CHAN_OP  // <- send and receive; always one token (spec 01)
	operatorEnd

	LPAREN
	RPAREN
	LBRACK
	RBRACK
	LBRACE
	RBRACE
	COMMA
	PERIOD
	COLON
	QUESTION // ?T, the nullable type former (spec 02)
)

var kindNames = map[Kind]string{
	INVALID: "invalid", EOF: "end of file", SEMI: "statement end",
	IDENT: "identifier", INT: "int literal", FLOAT: "float literal",
	IMAG: "complex literal", STRING: "string literal",

	BREAK: "break", CASE: "case", CONST: "const", CONTINUE: "continue",
	ELSE: "else", ENUM: "enum", EXPORT: "export", FALSE: "false", FOR: "for",
	FUNC: "func", IF: "if", IMPORT: "import", IN: "in", MATCH: "match",
	MODULE: "module", MUT: "mut", NIL: "nil", RETURN: "return", SELECT: "select",
	SPAWN: "spawn", STRUCT: "struct", TRUE: "true", TRY: "try", VAR: "var",
	WHILE: "while", DISCARD: "discard", GATE: "gate", MEASURE: "measure",
	QUBIT: "qubit", RESET: "reset",

	ADD: "+", SUB: "-", MUL: "*", QUO: "/", REM: "%", POW: "**", AT: "@",
	ASSIGN: "=", DEFINE: ":=", ADD_ASSIGN: "+=", SUB_ASSIGN: "-=",
	MUL_ASSIGN: "*=", QUO_ASSIGN: "/=", REM_ASSIGN: "%=", POW_ASSIGN: "**=",
	INC: "++", DEC: "--", EQL: "==", NEQ: "!=", LSS: "<", LEQ: "<=",
	GTR: ">", GEQ: ">=", LAND: "&&", LOR: "||", NOT: "!", AND: "&", OR: "|",
	ARROW: "->", FATARROW: "=>", CHAN_OP: "<-",

	LPAREN: "(", RPAREN: ")", LBRACK: "[", RBRACK: "]", LBRACE: "{",
	RBRACE: "}", COMMA: ",", PERIOD: ".", COLON: ":", QUESTION: "?",
}

func (k Kind) String() string {
	if s, ok := kindNames[k]; ok {
		return s
	}
	return fmt.Sprintf("Kind(%d)", int(k))
}

// IsKeyword reports whether k is a reserved word.
func (k Kind) IsKeyword() bool { return k > keywordStart && k < keywordEnd }

// IsOperator reports whether k is an operator.
func (k Kind) IsOperator() bool { return k > operatorStart && k < operatorEnd }

var keywords = map[string]Kind{
	"break": BREAK, "case": CASE, "const": CONST, "continue": CONTINUE,
	"else": ELSE, "enum": ENUM, "export": EXPORT, "false": FALSE, "for": FOR,
	"func": FUNC, "if": IF, "import": IMPORT, "in": IN, "match": MATCH,
	"module": MODULE, "mut": MUT, "nil": NIL, "return": RETURN,
	"select": SELECT, "spawn": SPAWN, "struct": STRUCT, "true": TRUE,
	"try": TRY, "var": VAR, "while": WHILE,
	"discard": DISCARD, "gate": GATE, "measure": MEASURE, "qubit": QUBIT,
	"reset": RESET,
}

// Lookup maps an identifier to its keyword kind, or IDENT if it is not reserved.
func Lookup(ident string) Kind {
	if k, ok := keywords[ident]; ok {
		return k
	}
	return IDENT
}

// operators is the closed operator set, grouped by length. The lexer tries
// longest first (maximal munch), which is what keeps `x==-3` lexing as
// `x` `==` `-` `3` rather than as a single merged token.
var operators = []map[string]Kind{
	3: {"**=": POW_ASSIGN},
	2: {
		":=": DEFINE, "==": EQL, "!=": NEQ, "<=": LEQ, ">=": GEQ,
		"&&": LAND, "||": LOR, "->": ARROW, "=>": FATARROW, "<-": CHAN_OP,
		"**": POW, "+=": ADD_ASSIGN, "-=": SUB_ASSIGN, "*=": MUL_ASSIGN,
		"/=": QUO_ASSIGN, "%=": REM_ASSIGN, "++": INC, "--": DEC,
	},
	1: {
		"+": ADD, "-": SUB, "*": MUL, "/": QUO, "%": REM, "=": ASSIGN,
		"<": LSS, ">": GTR, "!": NOT, "@": AT, "&": AND, "|": OR,
	},
}

// MaxOperatorLen is the longest operator, and so the lookahead the lexer needs.
const MaxOperatorLen = 3

// LookupOperator returns the operator of the given length, if s is one.
func LookupOperator(s string) (Kind, bool) {
	if len(s) >= len(operators) {
		return INVALID, false
	}
	k, ok := operators[len(s)][s]
	return k, ok
}

// Position is a resolved source location. Columns count bytes, 1-based, which
// is what editors expect for ASCII source; Ymir identifiers are ASCII (spec 01).
type Position struct {
	File   string
	Line   int
	Column int
	Offset int
}

func (p Position) String() string {
	if p.File == "" {
		return fmt.Sprintf("%d:%d", p.Line, p.Column)
	}
	return fmt.Sprintf("%s:%d:%d", p.File, p.Line, p.Column)
}

func (p Position) IsValid() bool { return p.Line > 0 }

// Token is a lexed token. Lit holds the decoded value for STRING and the raw
// text for numbers and identifiers; it is empty for tokens whose kind says all.
type Token struct {
	Kind Kind
	Lit  string
	Pos  Position
}

func (t Token) String() string {
	if t.Lit != "" {
		return fmt.Sprintf("%s(%q)", t.Kind, t.Lit)
	}
	return t.Kind.String()
}

// EndsStatement reports whether a newline following this token terminates a
// statement. Spec 01 §Semicolons: a newline ends a statement unless the
// statement is syntactically incomplete, which is exactly the case where the
// line's last token cannot end one.
func (t Token) EndsStatement() bool {
	switch t.Kind {
	case IDENT, INT, FLOAT, IMAG, STRING,
		BREAK, CONTINUE, RETURN, NIL, TRUE, FALSE,
		RPAREN, RBRACK, RBRACE, INC, DEC:
		return true
	}
	// Type names are predeclared identifiers, so they arrive as IDENT and are
	// already covered above.
	return false
}
