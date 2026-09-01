// Package ast defines Ymir's syntax tree.
//
// Two invariants here are non-negotiable, because violating them is what made
// the legacy implementation unfixable:
//
//   - An identifier is an *Ident node, never a bare string. In the legacy AST
//     identifiers were Python strings, and an unknown one silently evaluated to
//     a string equal to its own name, so a typo became a value instead of an
//     error.
//   - A call's callee is an Expr, never a string. The legacy FunctionCall stored
//     `func_name: str`, which made function values structurally inexpressible:
//     no closures, no higher-order functions, ever.
package ast

import "github.com/bjornaer/ymir/compiler/token"

// Node is any syntax tree node.
type Node interface {
	// Pos is the position of the node's first token.
	Pos() token.Position
	// End is the position just past the node's last token.
	End() token.Position
}

type Expr interface {
	Node
	exprNode()
}

type Stmt interface {
	Node
	stmtNode()
}

type Decl interface {
	Node
	declNode()
}

// Type is a syntactic type expression. It is resolved to a semantic type in
// Phase 2; the parser only records what was written.
type Type interface {
	Node
	typeNode()
}

// ---------------------------------------------------------------- File

// File is one parsed source file.
type File struct {
	Module  *ModuleDecl
	Imports []*ImportDecl
	Decls   []Decl
}

func (f *File) Pos() token.Position {
	if f.Module != nil {
		return f.Module.Pos()
	}
	return token.Position{}
}

func (f *File) End() token.Position {
	if n := len(f.Decls); n > 0 {
		return f.Decls[n-1].End()
	}
	if n := len(f.Imports); n > 0 {
		return f.Imports[n-1].End()
	}
	if f.Module != nil {
		return f.Module.End()
	}
	return token.Position{}
}

// ---------------------------------------------------------------- Names

// Ident is a single identifier. Never a string (see package doc).
type Ident struct {
	NamePos token.Position
	Name    string
}

func (i *Ident) Pos() token.Position { return i.NamePos }
func (i *Ident) End() token.Position { return shift(i.NamePos, len(i.Name)) }
func (i *Ident) exprNode()           {}
func (i *Ident) typeNode()           {}

// QualifiedIdent is a dotted name, as in a module declaration or import path.
type QualifiedIdent struct {
	Parts []*Ident
}

func (q *QualifiedIdent) Pos() token.Position { return q.Parts[0].Pos() }
func (q *QualifiedIdent) End() token.Position { return q.Parts[len(q.Parts)-1].End() }

func (q *QualifiedIdent) String() string {
	s := ""
	for i, p := range q.Parts {
		if i > 0 {
			s += "."
		}
		s += p.Name
	}
	return s
}

// ---------------------------------------------------------------- Declarations

type ModuleDecl struct {
	Keyword token.Position
	Name    *QualifiedIdent
}

func (d *ModuleDecl) Pos() token.Position { return d.Keyword }
func (d *ModuleDecl) End() token.Position { return d.Name.End() }
func (d *ModuleDecl) declNode()           {}

type ImportDecl struct {
	Keyword token.Position
	Path    *QualifiedIdent
	Alias   *Ident // nil unless `as` was given
}

func (d *ImportDecl) Pos() token.Position { return d.Keyword }
func (d *ImportDecl) End() token.Position {
	if d.Alias != nil {
		return d.Alias.End()
	}
	return d.Path.End()
}
func (d *ImportDecl) declNode() {}

// Param is one parameter or receiver. Mut marks a mutable reference.
type Param struct {
	Name *Ident
	Mut  bool
	Type Type // nil only for a `self` receiver
}

func (p *Param) Pos() token.Position { return p.Name.Pos() }
func (p *Param) End() token.Position {
	if p.Type != nil {
		return p.Type.End()
	}
	return p.Name.End()
}

// FuncDecl is a function, method, or gate.
//
// Recv non-nil makes it a method. IsGate marks a `gate` declaration, which the
// checker restricts to unitary operations (spec 08).
type FuncDecl struct {
	Keyword token.Position
	Export  bool
	IsGate  bool
	Recv    *Param
	Name    *Ident
	Params  []*Param
	Results []Type // empty for no result; >1 for a multi-value return
	Body    *BlockStmt
}

func (d *FuncDecl) Pos() token.Position { return d.Keyword }
func (d *FuncDecl) End() token.Position { return d.Body.End() }
func (d *FuncDecl) declNode()           {}

// HasErrorPosition reports whether the last result could be an error set. The
// error position is positional (spec 06 §The error position, and open question
// Q10); resolving whether that type is an enum or union is the checker's job.
func (d *FuncDecl) HasErrorPosition() bool { return len(d.Results) > 1 }

type Field struct {
	Name *Ident
	Type Type
}

func (f *Field) Pos() token.Position { return f.Name.Pos() }
func (f *Field) End() token.Position { return f.Type.End() }

type StructDecl struct {
	Keyword token.Position
	Export  bool
	Name    *Ident
	Fields  []*Field
	Rbrace  token.Position
}

func (d *StructDecl) Pos() token.Position { return d.Keyword }
func (d *StructDecl) End() token.Position { return shift(d.Rbrace, 1) }
func (d *StructDecl) declNode()           {}

// Variant is one enum variant. Payload is empty for a payload-free variant.
type Variant struct {
	Name    *Ident
	Payload []Type
	Rparen  token.Position
}

func (v *Variant) Pos() token.Position { return v.Name.Pos() }
func (v *Variant) End() token.Position {
	if len(v.Payload) > 0 {
		return shift(v.Rparen, 1)
	}
	return v.Name.End()
}

type EnumDecl struct {
	Keyword  token.Position
	Export   bool
	Name     *Ident
	Variants []*Variant
	Rbrace   token.Position
}

func (d *EnumDecl) Pos() token.Position { return d.Keyword }
func (d *EnumDecl) End() token.Position { return shift(d.Rbrace, 1) }
func (d *EnumDecl) declNode()           {}

// ConstDecl requires an explicit type and a constant initializer (spec 03).
type ConstDecl struct {
	Keyword token.Position
	Export  bool
	Name    *Ident
	Type    Type
	Value   Expr
}

func (d *ConstDecl) Pos() token.Position { return d.Keyword }
func (d *ConstDecl) End() token.Position { return d.Value.End() }
func (d *ConstDecl) declNode()           {}

// VarDecl is `var x: T = e`, `var x: T`, or `var x := e`. It is both a
// declaration (module level) and a statement (inside a block).
type VarDecl struct {
	Keyword token.Position
	Export  bool // rejected by the checker: there are no mutable globals (spec 03)
	Name    *Ident
	Type    Type // nil when inferred
	Value   Expr // nil when zero-initialized
}

func (d *VarDecl) Pos() token.Position { return d.Keyword }
func (d *VarDecl) End() token.Position {
	if d.Value != nil {
		return d.Value.End()
	}
	if d.Type != nil {
		return d.Type.End()
	}
	return d.Name.End()
}
func (d *VarDecl) declNode() {}
func (d *VarDecl) stmtNode() {}

// ---------------------------------------------------------------- Types

// NamedType is `int`, `Point`, or `math.Complex`. Type names are predeclared
// identifiers rather than keywords, so they arrive here as idents.
type NamedType struct {
	Name *QualifiedIdent
}

func (t *NamedType) Pos() token.Position { return t.Name.Pos() }
func (t *NamedType) End() token.Position { return t.Name.End() }
func (t *NamedType) typeNode()           {}

// GenericType is a built-in parameterized type: array[T], map[K, V],
// tuple[...], matrix[T], chan[T], qreg[N].
type GenericType struct {
	Name   *Ident
	Args   []Type
	Rbrack token.Position

	// Width is set only for qreg[N], whose argument is a compile-time integer
	// constant rather than a type (grammar 09 §Types). Args is empty then.
	Width *BasicLit
}

func (t *GenericType) Pos() token.Position { return t.Name.Pos() }
func (t *GenericType) End() token.Position { return shift(t.Rbrack, 1) }
func (t *GenericType) typeNode()           {}

// FuncType is `func(T, U) -> V`.
type FuncType struct {
	Keyword token.Position
	Params  []Type
	Results []Type
	end     token.Position
}

func (t *FuncType) Pos() token.Position { return t.Keyword }
func (t *FuncType) End() token.Position { return t.end }
func (t *FuncType) typeNode()           {}

// NullableType is `?T`: T, or nil.
//
// A general type former, not a rule about position. `?` requires an unrestricted
// type; `?qubit` is rejected by the checker, since a linear value that may be
// absent cannot be consumed exactly once (spec 02).
type NullableType struct {
	Question token.Position
	Elem     Type
}

func (t *NullableType) Pos() token.Position { return t.Question }
func (t *NullableType) End() token.Position { return t.Elem.End() }
func (t *NullableType) typeNode()           {}

// UnionType is `A | B`. Members must all be enum types; the parser records the
// syntax and the checker enforces that (spec 02 §Union types).
type UnionType struct {
	Members []Type
}

func (t *UnionType) Pos() token.Position { return t.Members[0].Pos() }
func (t *UnionType) End() token.Position { return t.Members[len(t.Members)-1].End() }
func (t *UnionType) typeNode()           {}

// ---------------------------------------------------------------- Expressions

type BasicLit struct {
	ValuePos token.Position
	Kind     token.Kind // INT, FLOAT, IMAG, STRING
	Value    string     // decoded for STRING, raw text otherwise
	raw      int        // source width, for End
}

func (e *BasicLit) Pos() token.Position { return e.ValuePos }
func (e *BasicLit) End() token.Position { return shift(e.ValuePos, e.raw) }
func (e *BasicLit) exprNode()           {}

// BoolLit is `true` or `false`; NilLit is `nil`. Both are keywords, so neither
// can be shadowed.
type BoolLit struct {
	ValuePos token.Position
	Value    bool
}

func (e *BoolLit) Pos() token.Position { return e.ValuePos }
func (e *BoolLit) End() token.Position {
	if e.Value {
		return shift(e.ValuePos, 4)
	}
	return shift(e.ValuePos, 5)
}
func (e *BoolLit) exprNode() {}

type NilLit struct{ ValuePos token.Position }

func (e *NilLit) Pos() token.Position { return e.ValuePos }
func (e *NilLit) End() token.Position { return shift(e.ValuePos, 3) }
func (e *NilLit) exprNode()           {}

type UnaryExpr struct {
	OpPos token.Position
	Op    token.Kind // SUB, NOT, CHAN_OP
	X     Expr
}

func (e *UnaryExpr) Pos() token.Position { return e.OpPos }
func (e *UnaryExpr) End() token.Position { return e.X.End() }
func (e *UnaryExpr) exprNode()           {}

type BinaryExpr struct {
	X     Expr
	OpPos token.Position
	Op    token.Kind
	Y     Expr
}

func (e *BinaryExpr) Pos() token.Position { return e.X.Pos() }
func (e *BinaryExpr) End() token.Position { return e.Y.End() }
func (e *BinaryExpr) exprNode()           {}

// CallExpr is a call. Fun is an Expr, never a name (see package doc).
type CallExpr struct {
	Fun    Expr
	Args   []Expr
	Rparen token.Position
}

func (e *CallExpr) Pos() token.Position { return e.Fun.Pos() }
func (e *CallExpr) End() token.Position { return shift(e.Rparen, 1) }
func (e *CallExpr) exprNode()           {}

// TryExpr is `try f()`, the error-propagation operator (spec 06 §Propagation).
// Unrelated to a try/catch block; Ymir has no exceptions.
type TryExpr struct {
	Keyword token.Position
	Call    Expr
}

func (e *TryExpr) Pos() token.Position { return e.Keyword }
func (e *TryExpr) End() token.Position { return e.Call.End() }
func (e *TryExpr) exprNode()           {}

// IndexExpr is `a[i]`.
type IndexExpr struct {
	X      Expr
	Index  Expr
	Rbrack token.Position
}

func (e *IndexExpr) Pos() token.Position { return e.X.Pos() }
func (e *IndexExpr) End() token.Position { return shift(e.Rbrack, 1) }
func (e *IndexExpr) exprNode()           {}

// SelectorExpr is `x.field`, `x.method`, or `m.Variant`. Legacy conflated field
// access and method call in one node; they are distinguished here by whether a
// CallExpr wraps the selector.
type SelectorExpr struct {
	X   Expr
	Sel *Ident
}

func (e *SelectorExpr) Pos() token.Position { return e.X.Pos() }
func (e *SelectorExpr) End() token.Position { return e.Sel.End() }
func (e *SelectorExpr) exprNode()           {}

// TupleIndexExpr is `t.0`. The index must be an integer literal (spec 04).
type TupleIndexExpr struct {
	X      Expr
	Index  int
	IdxPos token.Position
	raw    int
}

func (e *TupleIndexExpr) Pos() token.Position { return e.X.Pos() }
func (e *TupleIndexExpr) End() token.Position { return shift(e.IdxPos, e.raw) }
func (e *TupleIndexExpr) exprNode()           {}

// ParenExpr preserves explicit grouping, which matters for formatting and for
// the composite-literal ambiguity rule (spec 09).
type ParenExpr struct {
	Lparen token.Position
	X      Expr
	Rparen token.Position
}

func (e *ParenExpr) Pos() token.Position { return e.Lparen }
func (e *ParenExpr) End() token.Position { return shift(e.Rparen, 1) }
func (e *ParenExpr) exprNode()           {}

// ArrayLit is `[a, b, c]`. Whether it denotes an array or a matrix is the
// checker's decision, from element shape and context (spec 04).
type ArrayLit struct {
	Lbrack   token.Position
	Elements []Expr
	Rbrack   token.Position
}

func (e *ArrayLit) Pos() token.Position { return e.Lbrack }
func (e *ArrayLit) End() token.Position { return shift(e.Rbrack, 1) }
func (e *ArrayLit) exprNode()           {}

type KeyValue struct {
	Key   Expr
	Value Expr
}

func (e *KeyValue) Pos() token.Position { return e.Key.Pos() }
func (e *KeyValue) End() token.Position { return e.Value.End() }

type MapLit struct {
	Lbrace  token.Position
	Entries []*KeyValue
	Rbrace  token.Position
}

func (e *MapLit) Pos() token.Position { return e.Lbrace }
func (e *MapLit) End() token.Position { return shift(e.Rbrace, 1) }
func (e *MapLit) exprNode()           {}

// TupleLit is `(a, b)`. A one-element tuple needs the trailing comma, `(a,)`,
// which is what distinguishes it from parenthesization (spec 09).
type TupleLit struct {
	Lparen   token.Position
	Elements []Expr
	Rparen   token.Position
}

func (e *TupleLit) Pos() token.Position { return e.Lparen }
func (e *TupleLit) End() token.Position { return shift(e.Rparen, 1) }
func (e *TupleLit) exprNode()           {}

type FieldInit struct {
	Name  *Ident
	Value Expr
}

func (e *FieldInit) Pos() token.Position { return e.Name.Pos() }
func (e *FieldInit) End() token.Position { return e.Value.End() }

// StructLit is `Point{x: 1.0, y: 2.0}`. Every field is named; there is no
// positional form and no partial initialization (spec 02 §Structs).
type StructLit struct {
	Type   Type
	Fields []*FieldInit
	Rbrace token.Position
}

func (e *StructLit) Pos() token.Position { return e.Type.Pos() }
func (e *StructLit) End() token.Position { return shift(e.Rbrace, 1) }
func (e *StructLit) exprNode()           {}

// FuncLit is an inline function. It captures its enclosing scope by reference
// (spec 03 §Functions as values).
type FuncLit struct {
	Keyword token.Position
	Params  []*Param
	Results []Type
	Body    *BlockStmt
}

func (e *FuncLit) Pos() token.Position { return e.Keyword }
func (e *FuncLit) End() token.Position { return e.Body.End() }
func (e *FuncLit) exprNode()           {}

// ---------------------------------------------------------------- Statements

type BlockStmt struct {
	Lbrace token.Position
	Stmts  []Stmt
	Rbrace token.Position
}

func (s *BlockStmt) Pos() token.Position { return s.Lbrace }
func (s *BlockStmt) End() token.Position { return shift(s.Rbrace, 1) }
func (s *BlockStmt) stmtNode()           {}

// ExprStmt holds a standalone expression. Only calls are legal here; a bare
// `x + 1` is rejected by the parser (spec 05 §Statement-level expressions).
type ExprStmt struct{ X Expr }

func (s *ExprStmt) Pos() token.Position { return s.X.Pos() }
func (s *ExprStmt) End() token.Position { return s.X.End() }
func (s *ExprStmt) stmtNode()           {}

// AssignStmt covers `=`, the compound forms, and `:=`.
//
// Lhs may hold several targets for destructuring: `q, r := divmod(17, 5)`.
type AssignStmt struct {
	Lhs    []Expr
	TokPos token.Position
	Tok    token.Kind // ASSIGN, DEFINE, ADD_ASSIGN, ...
	Rhs    []Expr
}

func (s *AssignStmt) Pos() token.Position { return s.Lhs[0].Pos() }
func (s *AssignStmt) End() token.Position { return s.Rhs[len(s.Rhs)-1].End() }
func (s *AssignStmt) stmtNode()           {}

// IncDecStmt is `x++` or `x--`. A statement, never an expression, so `y = x++`
// is a syntax error (spec 05).
type IncDecStmt struct {
	X      Expr
	TokPos token.Position
	Tok    token.Kind
}

func (s *IncDecStmt) Pos() token.Position { return s.X.Pos() }
func (s *IncDecStmt) End() token.Position { return shift(s.TokPos, 2) }
func (s *IncDecStmt) stmtNode()           {}

type IfStmt struct {
	Keyword token.Position
	Cond    Expr
	Then    *BlockStmt
	Else    Stmt // *IfStmt for `else if`, *BlockStmt for `else`, nil for neither
}

func (s *IfStmt) Pos() token.Position { return s.Keyword }
func (s *IfStmt) End() token.Position {
	if s.Else != nil {
		return s.Else.End()
	}
	return s.Then.End()
}
func (s *IfStmt) stmtNode() {}

type WhileStmt struct {
	Keyword token.Position
	Cond    Expr
	Body    *BlockStmt
}

func (s *WhileStmt) Pos() token.Position { return s.Keyword }
func (s *WhileStmt) End() token.Position { return s.Body.End() }
func (s *WhileStmt) stmtNode()           {}

// RangeStmt is `for x in xs` or `for i, x in xs`.
type RangeStmt struct {
	Keyword token.Position
	Names   []*Ident
	X       Expr
	Body    *BlockStmt
}

func (s *RangeStmt) Pos() token.Position { return s.Keyword }
func (s *RangeStmt) End() token.Position { return s.Body.End() }
func (s *RangeStmt) stmtNode()           {}

// ForStmt is the C-style form. Any clause may be nil.
type ForStmt struct {
	Keyword token.Position
	Init    Stmt
	Cond    Expr
	Post    Stmt
	Body    *BlockStmt
}

func (s *ForStmt) Pos() token.Position { return s.Keyword }
func (s *ForStmt) End() token.Position { return s.Body.End() }
func (s *ForStmt) stmtNode()           {}

// Pattern is one match arm's pattern.
//
// Enum is set for a qualified pattern like `IOError.NotFound`, which is required
// when matching a union (spec 06 §Qualified patterns). IsWildcard marks `_`,
// IsNil marks the `nil` arm of an un-narrowed error set.
type Pattern struct {
	StartPos   token.Position
	IsWildcard bool
	IsNil      bool
	Enum       *Ident // nil when unqualified
	Variant    *Ident
	Binds      []*Ident // nil entries are `_`
	end        token.Position
}

func (p *Pattern) Pos() token.Position { return p.StartPos }
func (p *Pattern) End() token.Position { return p.end }

type MatchArm struct {
	Pattern *Pattern
	Body    Stmt // a BlockStmt, or a single statement
}

func (a *MatchArm) Pos() token.Position { return a.Pattern.Pos() }
func (a *MatchArm) End() token.Position { return a.Body.End() }

type MatchStmt struct {
	Keyword token.Position
	X       Expr
	Arms    []*MatchArm
	Rbrace  token.Position
}

func (s *MatchStmt) Pos() token.Position { return s.Keyword }
func (s *MatchStmt) End() token.Position { return shift(s.Rbrace, 1) }
func (s *MatchStmt) stmtNode()           {}

type ReturnStmt struct {
	Keyword token.Position
	Results []Expr
	end     token.Position
}

func (s *ReturnStmt) Pos() token.Position { return s.Keyword }
func (s *ReturnStmt) End() token.Position {
	if len(s.Results) > 0 {
		return s.Results[len(s.Results)-1].End()
	}
	return s.end
}
func (s *ReturnStmt) stmtNode() {}

type BranchStmt struct {
	Keyword token.Position
	Tok     token.Kind // BREAK or CONTINUE
}

func (s *BranchStmt) Pos() token.Position { return s.Keyword }
func (s *BranchStmt) End() token.Position {
	if s.Tok == token.BREAK {
		return shift(s.Keyword, 5)
	}
	return shift(s.Keyword, 8)
}
func (s *BranchStmt) stmtNode() {}

// SpawnStmt runs a call in a new task. A statement, with no task handle
// (spec 07 §Tasks).
type SpawnStmt struct {
	Keyword token.Position
	Call    Expr
}

func (s *SpawnStmt) Pos() token.Position { return s.Keyword }
func (s *SpawnStmt) End() token.Position { return s.Call.End() }
func (s *SpawnStmt) stmtNode()           {}

// SendStmt is `ch <- v`.
type SendStmt struct {
	Chan     Expr
	ArrowPos token.Position
	Value    Expr
}

func (s *SendStmt) Pos() token.Position { return s.Chan.Pos() }
func (s *SendStmt) End() token.Position { return s.Value.End() }
func (s *SendStmt) stmtNode()           {}

// CommClause is one `case` of a select. Comm is nil for `default`.
type CommClause struct {
	Keyword token.Position
	Comm    Stmt
	Body    []Stmt
	end     token.Position
}

func (c *CommClause) Pos() token.Position { return c.Keyword }
func (c *CommClause) End() token.Position {
	if n := len(c.Body); n > 0 {
		return c.Body[n-1].End()
	}
	return c.end
}

type SelectStmt struct {
	Keyword token.Position
	Cases   []*CommClause
	Rbrace  token.Position
}

func (s *SelectStmt) Pos() token.Position { return s.Keyword }
func (s *SelectStmt) End() token.Position { return shift(s.Rbrace, 1) }
func (s *SelectStmt) stmtNode()           {}

// BadStmt and BadExpr mark where the parser recovered, so one syntax error does
// not cascade into a page of noise.
type BadStmt struct {
	From, To token.Position
}

func (s *BadStmt) Pos() token.Position { return s.From }
func (s *BadStmt) End() token.Position { return s.To }
func (s *BadStmt) stmtNode()           {}

type BadExpr struct {
	From, To token.Position
}

func (e *BadExpr) Pos() token.Position { return e.From }
func (e *BadExpr) End() token.Position { return e.To }
func (e *BadExpr) exprNode()           {}

func shift(p token.Position, n int) token.Position {
	p.Column += n
	p.Offset += n
	return p
}

// SetEnd records the end position of nodes whose extent the parser learns after
// construction.
func (p *Pattern) SetEnd(pos token.Position)    { p.end = pos }
func (c *CommClause) SetEnd(pos token.Position) { c.end = pos }
func (s *ReturnStmt) SetEnd(pos token.Position) { s.end = pos }
func (t *FuncType) SetEnd(pos token.Position)   { t.end = pos }

// NewBasicLit builds a literal, recording its source width so End is accurate.
func NewBasicLit(pos token.Position, kind token.Kind, value string, width int) *BasicLit {
	return &BasicLit{ValuePos: pos, Kind: kind, Value: value, raw: width}
}

// NewTupleIndex builds `t.N`, recording the index's source width.
func NewTupleIndex(x Expr, idx int, pos token.Position, width int) *TupleIndexExpr {
	return &TupleIndexExpr{X: x, Index: idx, IdxPos: pos, raw: width}
}
