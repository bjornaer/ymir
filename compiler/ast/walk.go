package ast

import "fmt"

// Traversal of the syntax tree.
//
// The checker needs this and the printer already had it, in the shape of one
// type switch (print.go). This is that switch, factored out so there is exactly
// one place that knows which node has which children — a second, drifting copy
// inside compiler/check is how a checker starts silently skipping a construct.
//
// Every node kind must appear below. Adding an AST node without adding it here
// is a bug that shows up as a rule not being enforced rather than as a compile
// error, so TestWalkVisitsEveryNodeKind pins the coverage.

// A Visitor is invoked for each node encountered by Walk.
//
// If the result is non-nil, Walk descends into the node's children with that
// visitor, then calls v.Visit(nil) to signal the end of the node. Returning nil
// prunes the subtree.
type Visitor interface {
	Visit(n Node) Visitor
}

// Walk traverses n in depth-first source order, calling v.Visit for every
// non-nil node.
//
// Nil children are common and legal — a `var` with no initializer, an `if` with
// no `else`, a `self` receiver with no type, a `_` in a match pattern — and are
// skipped rather than visited.
func Walk(v Visitor, n Node) {
	if n == nil {
		return
	}
	if v = v.Visit(n); v == nil {
		return
	}

	switch x := n.(type) {

	// --------------------------------------------------------------- File

	case *File:
		if x.Module != nil {
			Walk(v, x.Module)
		}
		for _, imp := range x.Imports {
			Walk(v, imp)
		}
		for _, d := range x.Decls {
			Walk(v, d)
		}

	// --------------------------------------------------------------- Names

	case *Ident:
		// leaf

	case *QualifiedIdent:
		for _, p := range x.Parts {
			Walk(v, p)
		}

	// -------------------------------------------------------- Declarations

	case *ModuleDecl:
		Walk(v, x.Name)

	case *ImportDecl:
		Walk(v, x.Path)
		if x.Alias != nil {
			Walk(v, x.Alias)
		}

	case *Param:
		Walk(v, x.Name)
		if x.Type != nil { // nil for a `self` receiver
			Walk(v, x.Type)
		}

	case *FuncDecl:
		if x.Recv != nil {
			Walk(v, x.Recv)
		}
		Walk(v, x.Name)
		for _, p := range x.Params {
			Walk(v, p)
		}
		for _, r := range x.Results {
			Walk(v, r)
		}
		if x.Body != nil {
			Walk(v, x.Body)
		}

	case *Field:
		Walk(v, x.Name)
		Walk(v, x.Type)

	case *StructDecl:
		Walk(v, x.Name)
		for _, f := range x.Fields {
			Walk(v, f)
		}

	case *Variant:
		Walk(v, x.Name)
		for _, p := range x.Payload {
			Walk(v, p)
		}

	case *EnumDecl:
		Walk(v, x.Name)
		for _, vr := range x.Variants {
			Walk(v, vr)
		}

	case *ConstDecl:
		Walk(v, x.Name)
		if x.Type != nil {
			Walk(v, x.Type)
		}
		if x.Value != nil {
			Walk(v, x.Value)
		}

	case *VarDecl:
		// Both a Decl (module level) and a Stmt (inside a block); one case
		// serves both.
		Walk(v, x.Name)
		if x.Type != nil { // nil when inferred
			Walk(v, x.Type)
		}
		if x.Value != nil { // nil when zero-initialized
			Walk(v, x.Value)
		}

	// --------------------------------------------------------------- Types

	case *NamedType:
		Walk(v, x.Name)

	case *GenericType:
		Walk(v, x.Name)
		if x.Width != nil { // qreg[N] only
			Walk(v, x.Width)
		}
		for _, a := range x.Args {
			Walk(v, a)
		}

	case *FuncType:
		for _, p := range x.Params {
			Walk(v, p)
		}
		for _, r := range x.Results {
			Walk(v, r)
		}

	case *NullableType:
		Walk(v, x.Elem)

	case *UnionType:
		for _, m := range x.Members {
			Walk(v, m)
		}

	// --------------------------------------------------------- Expressions

	case *BasicLit, *BoolLit, *NilLit, *BadExpr:
		// leaves

	case *UnaryExpr:
		Walk(v, x.X)

	case *BinaryExpr:
		Walk(v, x.X)
		Walk(v, x.Y)

	case *CallExpr:
		Walk(v, x.Fun)
		for _, a := range x.Args {
			Walk(v, a)
		}

	case *TryExpr:
		Walk(v, x.Call)

	case *IndexExpr:
		Walk(v, x.X)
		Walk(v, x.Index)

	case *SelectorExpr:
		Walk(v, x.X)
		Walk(v, x.Sel)

	case *TupleIndexExpr:
		Walk(v, x.X)

	case *ParenExpr:
		Walk(v, x.X)

	case *ArrayLit:
		for _, e := range x.Elements {
			Walk(v, e)
		}

	case *KeyValue:
		Walk(v, x.Key)
		Walk(v, x.Value)

	case *MapLit:
		for _, e := range x.Entries {
			Walk(v, e)
		}

	case *TupleLit:
		for _, e := range x.Elements {
			Walk(v, e)
		}

	case *FieldInit:
		Walk(v, x.Name)
		Walk(v, x.Value)

	case *StructLit:
		Walk(v, x.Type)
		for _, f := range x.Fields {
			Walk(v, f)
		}

	case *FuncLit:
		for _, p := range x.Params {
			Walk(v, p)
		}
		for _, r := range x.Results {
			Walk(v, r)
		}
		Walk(v, x.Body)

	// ---------------------------------------------------------- Statements

	case *BlockStmt:
		for _, s := range x.Stmts {
			Walk(v, s)
		}

	case *ExprStmt:
		Walk(v, x.X)

	case *AssignStmt:
		for _, e := range x.Lhs {
			Walk(v, e)
		}
		for _, e := range x.Rhs {
			Walk(v, e)
		}

	case *IncDecStmt:
		Walk(v, x.X)

	case *IfStmt:
		Walk(v, x.Cond)
		Walk(v, x.Then)
		if x.Else != nil { // *IfStmt for else-if, *BlockStmt for else
			Walk(v, x.Else)
		}

	case *WhileStmt:
		Walk(v, x.Cond)
		Walk(v, x.Body)

	case *RangeStmt:
		for _, name := range x.Names {
			Walk(v, name)
		}
		Walk(v, x.X)
		Walk(v, x.Body)

	case *ForStmt:
		if x.Init != nil {
			Walk(v, x.Init)
		}
		if x.Cond != nil {
			Walk(v, x.Cond)
		}
		if x.Post != nil {
			Walk(v, x.Post)
		}
		Walk(v, x.Body)

	case *Pattern:
		// Enum and Variant are nil for a wildcard or a nil arm, and Binds holds
		// a nil entry for each `_`.
		if x.Enum != nil {
			Walk(v, x.Enum)
		}
		if x.Variant != nil {
			Walk(v, x.Variant)
		}
		for _, b := range x.Binds {
			if b != nil {
				Walk(v, b)
			}
		}

	case *MatchArm:
		Walk(v, x.Pattern)
		Walk(v, x.Body)

	case *MatchStmt:
		Walk(v, x.X)
		for _, a := range x.Arms {
			Walk(v, a)
		}

	case *ReturnStmt:
		for _, r := range x.Results {
			Walk(v, r)
		}

	case *BranchStmt, *BadStmt:
		// leaves

	case *SpawnStmt:
		Walk(v, x.Call)

	case *SendStmt:
		Walk(v, x.Chan)
		Walk(v, x.Value)

	case *CommClause:
		if x.Comm != nil { // nil for `default`
			Walk(v, x.Comm)
		}
		for _, s := range x.Body {
			Walk(v, s)
		}

	case *SelectStmt:
		for _, c := range x.Cases {
			Walk(v, c)
		}

	default:
		panic(fmt.Sprintf("ast.Walk: unhandled node type %T", n))
	}

	v.Visit(nil)
}

// inspector adapts a function to the Visitor interface.
type inspector func(Node) bool

func (f inspector) Visit(n Node) Visitor {
	if n != nil && f(n) {
		return f
	}
	return nil
}

// Inspect walks n, calling f for each node. If f returns false the subtree is
// not descended into.
func Inspect(n Node, f func(Node) bool) {
	Walk(inspector(f), n)
}
