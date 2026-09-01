package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Narrowing, rule N6 of chapter 02.
//
//	v := lookup(key)         # v: ?string
//	if v != nil {
//	    print(v + "!")       # v: string here
//	}
//
// It is deliberately minimal. The condition MUST be exactly `x != nil` or
// `x == nil` for a *binding* x — not a field, not an index, not an element of a
// && chain, not the result of a call. It applies to the corresponding branch
// and does not survive reassignment of x. This is not flow typing, and
// generalizing it into flow typing is a much larger commitment that the spec
// does not make.
//
// The mechanism is a scope, not a side table: the narrowed branch is checked in
// a scope holding a shadow binding of the narrowed type. Lexical scoping then
// gives the "that branch only" half for free, and the shadow is what an
// assignment removes to give the "does not survive reassignment" half.

// narrowScopes returns the scopes in which to check an if's two branches.
//
// Either may be the original scope, when the condition narrows nothing.
func (c *checker) narrowScopes(scope *Scope, cond ast.Expr) (thenScope, elseScope *Scope) {
	o, elem, op, ok := c.narrowTarget(scope, cond)
	if !ok {
		return scope, scope
	}

	narrow := func() *Scope {
		s := NewScope(scope, BlockScope)
		shadow := &Object{
			Kind:     o.Kind,
			Name:     o.Name,
			Type:     elem,
			Pos:      o.Pos,
			Mutable:  o.Mutable,
			Exported: o.Exported,
		}
		s.names[o.Name] = shadow
		c.narrowedFrom[shadow] = o
		return s
	}

	if op == token.NEQ {
		// `x != nil`: x is a T in the then branch.
		return narrow(), scope
	}
	// `x == nil`: x is a T in the else branch.
	return scope, narrow()
}

// narrowTarget recognizes the exact shape N6 permits and resolves what it
// narrows.
func (c *checker) narrowTarget(scope *Scope, cond ast.Expr) (o *Object, elem types.Type, op token.Kind, ok bool) {
	bin, isBinary := cond.(*ast.BinaryExpr)
	if !isBinary || (bin.Op != token.EQL && bin.Op != token.NEQ) {
		return nil, nil, 0, false
	}

	// One side must be the literal nil and the other a plain name. Anything
	// else — a field, an index, a call — is outside the rule.
	var id *ast.Ident
	switch {
	case isNilLit(bin.Y):
		id, _ = bin.X.(*ast.Ident)
	case isNilLit(bin.X):
		id, _ = bin.Y.(*ast.Ident)
	}
	if id == nil {
		return nil, nil, 0, false
	}

	o, _ = scope.LookupParent(id.Name)
	if o == nil {
		return nil, nil, 0, false
	}
	n, isNullable := o.Type.(*types.Nullable)
	if !isNullable {
		// Comparing a non-nullable to nil is an error the operator check
		// already reported (N3).
		return nil, nil, 0, false
	}
	return o, n.Elem, bin.Op, true
}

func isNilLit(e ast.Expr) bool {
	_, ok := e.(*ast.NilLit)
	return ok
}

// dropNarrowing ends a narrowing when the binding it narrowed is reassigned:
// "it does not survive reassignment of x" (rule N6).
//
// It returns the original binding, so the assignment is checked against the
// declared `?T` rather than against the narrowed `T`.
func (c *checker) dropNarrowing(scope *Scope, name string) *Object {
	o, owner := scope.LookupParent(name)
	if o == nil {
		return nil
	}
	orig := c.narrowedFrom[o]
	if orig == nil {
		return o
	}
	delete(owner.names, name)
	delete(c.narrowedFrom, o)
	return orig
}
