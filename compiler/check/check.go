// Package check is Ymir's type checker.
//
// It takes a parsed *ast.File and answers whether the program obeys chapters
// 02 through 06 of docs/spec, reporting through compiler/diag. Semantic types
// come from compiler/types; this package resolves the syntax to them.
//
// Nothing is written back onto the AST. Resolved types and resolved names live
// in Info, a side table keyed by node pointer, so the tree stays a faithful
// record of the source — which is what lets `ymir fmt` and the language server
// reuse it later without a second parser.
//
// Phase 2 is being built one rule at a time; PLAN.md §5 tracks which milestone
// added what.
package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/diag"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// ObjKind classifies what a name denotes.
type ObjKind int

const (
	// Var is a `var` binding, a `:=` binding, a parameter, a loop variable, or
	// a pattern binding.
	Var ObjKind = iota
	// Const is a `const` declaration. Immutable, and its value is known at
	// compile time.
	Const
	// Func is a function or method declaration.
	Func
	// TypeName is a struct, enum, or predeclared type name.
	TypeName
	// Module is an import: the name bound by `import a.b` or `... as m`.
	Module
	// Builtin is a predeclared function.
	Builtin
)

func (k ObjKind) String() string {
	switch k {
	case Var:
		return "variable"
	case Const:
		return "constant"
	case Func:
		return "function"
	case TypeName:
		return "type"
	case Module:
		return "module"
	case Builtin:
		return "builtin"
	}
	return "object"
}

// An Object is a declared name.
//
// Two Objects are the same declaration only when they are the same pointer,
// which is also how nominal type identity works (types.Named). The checker
// allocates exactly one per declaration.
type Object struct {
	Kind ObjKind
	Name string
	Type types.Type
	Pos  token.Position // where it was declared; the zero value for predeclared names

	// Mutable is false for a const, for a non-`mut` parameter, and for a
	// non-`mut` receiver. Plain locals and module-level `var`s are always
	// mutable in v1 (resolved question R6).
	Mutable bool

	// Exported records `export`. `var` cannot be exported: there are no
	// mutable globals across module boundaries (chapter 03 §Exports).
	Exported bool
}

// Info is the checker's output: everything it learned, keyed by the node it
// learned it about.
type Info struct {
	// Types is the type of every expression the checker visited. An expression
	// it could not type maps to types.Invalid rather than being absent, so a
	// missing key means "never visited", not "failed".
	Types map[ast.Expr]types.Type

	// Defs maps an identifier at its declaration to the object it declares.
	Defs map[*ast.Ident]*Object

	// Uses maps an identifier at a use site to the object it resolves to. An
	// identifier is in exactly one of Defs and Uses, never both.
	Uses map[*ast.Ident]*Object
}

func newInfo() *Info {
	return &Info{
		Types: map[ast.Expr]types.Type{},
		Defs:  map[*ast.Ident]*Object{},
		Uses:  map[*ast.Ident]*Object{},
	}
}

// TypeOf returns the type recorded for e, or types.Invalid when the checker
// never reached it.
func (i *Info) TypeOf(e ast.Expr) types.Type {
	if t, ok := i.Types[e]; ok {
		return t
	}
	return types.Invalid
}

// ObjectOf returns the object an identifier declares or refers to, or nil.
func (i *Info) ObjectOf(id *ast.Ident) *Object {
	if o, ok := i.Defs[id]; ok {
		return o
	}
	return i.Uses[id]
}

// checker holds the state of one run.
type checker struct {
	info *Info
	errs *diag.List
}

// Check type-checks a parsed file.
//
// name and src must be the ones passed to parser.ParseFile, because diagnostics
// quote the source to build their excerpt.
//
// The file MUST be free of syntax errors. The parser recovers by inserting
// synthetic nodes — a `_`-named VarDecl, a `_`-named NamedType, ast.BadExpr and
// ast.BadStmt — and checking those produces confident nonsense. Callers run the
// parser first and stop if it reported anything.
func Check(file *ast.File, name, src string) (*Info, *diag.List) {
	c := &checker{
		info: newInfo(),
		errs: diag.NewList(name, src),
	}
	c.checkFile(file)
	c.errs.Sort()
	return c.info, c.errs
}

func (c *checker) checkFile(file *ast.File) {
	if file == nil {
		return
	}
	// Milestones M3 onward hang off here: the module-scope pre-pass, then a
	// pass over each declaration's body.
}

// errorf reports a diagnostic at pos.
func (c *checker) errorf(pos token.Position, format string, args ...any) {
	c.errs.Addf(pos, format, args...)
}

// hint reports a diagnostic with a suggested fix. The hint is the fix, never a
// restatement of the message.
func (c *checker) hint(pos token.Position, msg, hint string) {
	c.errs.AddHint(pos, msg, hint)
}
