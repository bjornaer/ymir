package check

import (
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// ScopeKind names one of the five levels of chapter 03 §Scope.
type ScopeKind int

const (
	// UniverseScope holds the predeclared type names and builtins.
	UniverseScope ScopeKind = iota
	// ModuleScope holds a module's func, struct, enum, const and var. Its
	// contents are collected in a pre-pass, so declarations are visible
	// regardless of textual order.
	ModuleScope
	// FileScope holds imports, and nothing else.
	FileScope
	// FuncScope holds parameters and the receiver.
	FuncScope
	// BlockScope is any { ... }, plus the implicit scopes of a for header, a
	// match arm, and a select case.
	BlockScope
)

// A Scope is one level of the lexical chain.
//
// Resolution runs innermost first: block chain, then parameters, then this
// file's imports, then the whole module, then universe. That order is why
// FileScope sits between the function and the module rather than outside both.
type Scope struct {
	parent *Scope
	kind   ScopeKind
	names  map[string]*Object
}

// NewScope returns a scope nested inside parent.
func NewScope(parent *Scope, kind ScopeKind) *Scope {
	return &Scope{parent: parent, kind: kind, names: map[string]*Object{}}
}

// Kind reports which level this is.
func (s *Scope) Kind() ScopeKind { return s.kind }

// Parent returns the enclosing scope, or nil for universe.
func (s *Scope) Parent() *Scope { return s.parent }

// Insert binds o in s.
//
// It returns the object already bound under that name in *this* scope, if any,
// and does not overwrite it — redeclaring a name in the same scope is a compile
// error, while shadowing it in a nested scope is legal (chapter 03 §Variables).
// The blank identifier is never bound: it may be written but not read.
func (s *Scope) Insert(o *Object) *Object {
	if o.Name == "_" {
		return nil
	}
	if prev, ok := s.names[o.Name]; ok {
		return prev
	}
	s.names[o.Name] = o
	return nil
}

// Lookup finds a name in this scope only.
func (s *Scope) Lookup(name string) *Object { return s.names[name] }

// LookupParent finds a name in this scope or any enclosing one, innermost
// first, and reports the scope it was found in.
func (s *Scope) LookupParent(name string) (*Object, *Scope) {
	for sc := s; sc != nil; sc = sc.parent {
		if o, ok := sc.names[name]; ok {
			return o, sc
		}
	}
	return nil, nil
}

// Names returns the names bound directly in s, unordered. For tests and
// diagnostics.
func (s *Scope) Names() []string {
	out := make([]string, 0, len(s.names))
	for n := range s.names {
		out = append(out, n)
	}
	return out
}

// newUniverse builds the universe scope from compiler/types.
//
// A fresh one is built per run rather than shared, so that a later phase adding
// something to it cannot leak state between compilations.
func newUniverse() *Scope {
	s := NewScope(nil, UniverseScope)
	for name, t := range types.Predeclared {
		s.Insert(&Object{Kind: TypeName, Name: name, Type: t})
	}
	// types.Gates is deliberately NOT inserted here. Chapter 08 lists h, x, y,
	// z, s and t as gate names, and putting single letters in universe scope
	// would mean a typo'd `x` resolves to the Pauli-X gate instead of being
	// reported as undefined. Where the gates live is open question Q14.
	for name, b := range types.Builtins {
		// float, int and complex are both type names and conversion
		// functions. The type name is inserted above and wins the scope slot;
		// the checker recognizes the conversion from the call site instead.
		if s.Lookup(name) != nil {
			continue
		}
		s.Insert(&Object{Kind: Builtin, Name: name, Type: b})
	}
	return s
}

// declare inserts o into scope, reporting a redeclaration at pos.
func (c *checker) declare(scope *Scope, o *Object) {
	if prev := scope.Insert(o); prev != nil {
		if prev.Pos.IsValid() {
			c.hint(o.Pos,
				o.Name+" redeclared in this scope",
				"the first declaration is at "+prev.Pos.String())
		} else {
			c.errorf(o.Pos, "%s redeclares a predeclared name", o.Name)
		}
	}
}

// lookup resolves a name from scope, reporting it as undefined at pos when it
// is not found. It returns nil in that case.
func (c *checker) lookup(scope *Scope, name string, pos token.Position) *Object {
	o, _ := scope.LookupParent(name)
	if o == nil {
		c.errorf(pos, "undefined: %s", name)
	}
	return o
}
