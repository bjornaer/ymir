package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Local inference and assignability.
//
// "Inference is local. There is no global or Hindley-Milner inference; a
// function's signature is always fully annotated." (chapter 02 §Type inference)
// Exactly two things are inferred: the type of a `var` or `:=` binding, from
// its initializer. Everything else is written down.
//
// Assignability is chapter 02 §Assignability, implemented in compiler/types.
// This file is the list of places it applies.

// assignableTo checks that a value may be stored in a location, reporting at
// pos when it may not. what names the location for the message.
func (c *checker) assignableTo(pos token.Position, src, dst types.Type, what string) bool {
	if types.Assignable(src, dst) {
		return true
	}
	msg := "cannot use " + src.String() + " as " + dst.String() + " in " + what
	switch {
	case isNilType(src):
		c.hint(pos, msg,
			"nil belongs only to a nullable type; write ?"+dst.String())
	case types.IsErrorSet(types.Underlying(src)) && types.IsErrorSet(types.Underlying(dst)):
		c.hint(pos, msg,
			"an error set is assignable only to a superset of itself; widen the declared set")
	case types.Identical(types.Underlying(dst), src):
		c.hint(pos, msg, "a "+dst.String()+" may be absent; "+src.String()+" is not the same type")
	case types.Identical(dst, types.Underlying(src)):
		c.hint(pos, msg,
			"narrow it first: inside `if x != nil` the checker knows it is "+dst.String())
	default:
		c.errorf(pos, "%s", msg)
	}
	return false
}

// varType computes the type of a `var` declaration, in its three forms:
//
//	var x: T = e    annotated and initialized, so e must be assignable to T
//	var x := e      inferred from e
//	var x: T        zero-initialized, so T must have a zero value
func (c *checker) varType(scope *Scope, x *ast.VarDecl) types.Type {
	var declared types.Type
	if x.Type != nil {
		declared = c.resolveType(scope, x.Type)
	}

	if x.Value == nil {
		if declared == nil {
			// The parser does not produce this, but a `var` with neither a
			// type nor a value would be uninferable.
			c.errorf(x.Name.Pos(), "%s needs a type or an initializer", x.Name.Name)
			return types.Invalid
		}
		c.requireZeroValue(x.Name.Pos(), declared, x.Name.Name)
		return declared
	}

	value := c.exprWant(scope, x.Value, declared)

	if declared == nil {
		return c.inferred(x.Name.Pos(), value, x.Name.Name)
	}
	c.assignableTo(x.Value.Pos(), value, declared, "the declaration of "+x.Name.Name)
	return declared
}

// requireZeroValue reports a `var` of a type that has none.
//
// "Types with no zero value: enum and bare unions (no privileged variant), chan
// and func, and every linear type." (chapter 02 §Zero values)
func (c *checker) requireZeroValue(pos token.Position, t types.Type, name string) {
	if types.IsInvalid(t) || types.HasZeroValue(t) {
		return
	}
	hint := "give it an initializer"
	switch {
	case types.IsLinear(t):
		hint = "a linear value must be consumed exactly once, so it cannot start absent"
	case isErrorSetType(t):
		hint = "an enum has no privileged variant; initialize it, or write ?" + t.String()
	default:
		hint = "write ?" + t.String() + " for one that may be absent, or give it an initializer"
	}
	c.hint(pos, t.String()+" has no zero value, so "+name+" needs an initializer", hint)
}

// inferred validates a type arrived at by inference rather than annotation.
func (c *checker) inferred(pos token.Position, t types.Type, name string) types.Type {
	if isNilType(t) {
		c.hint(pos,
			"cannot infer a type for "+name+" from nil",
			"annotate it: var "+name+": ?T = nil")
		return types.Invalid
	}
	return t
}

// define handles the `:=` form, which infers exactly as `var x := e` does.
func (c *checker) define(scope *Scope, id *ast.Ident, value types.Type) {
	var t types.Type = types.Invalid
	if id.Name != "_" {
		t = c.inferred(id.Pos(), value, id.Name)
	}
	c.declareLocal(scope, id, t)
}

// constDeclBody folds a `const` initializer and records its value, so a later
// constant expression naming it can fold too.
//
// "A const initializer MUST be a compile-time constant expression: literals and
// operators over literals and other constants." (chapter 03 §Constants)
func (c *checker) constDeclBody(scope *Scope, x *ast.ConstDecl) {
	o := c.info.Defs[x.Name]
	if x.Value == nil {
		return
	}
	declared := types.Type(types.Invalid)
	if o != nil {
		declared = o.Type
	}
	value := c.exprWant(scope, x.Value, declared)
	c.assignableTo(x.Value.Pos(), value, declared, "the declaration of "+x.Name.Name)

	v, ok := c.constOf(x.Value)
	if !ok {
		// constOf already reported overflow or division by zero. Anything else
		// simply is not constant.
		if !c.reportedAt(x.Value) {
			c.hint(x.Value.Pos(),
				"a const initializer must be a constant expression",
				"literals, other constants, and operators over them")
		}
		return
	}
	if o != nil {
		c.constVals[o] = v
	}
}

// varDeclBody checks a module-level `var`, whose object was already created by
// the declaration pass so that every function can see it.
func (c *checker) varDeclBody(scope *Scope, x *ast.VarDecl, o *Object) {
	if x.Value == nil {
		if o != nil {
			c.requireZeroValue(x.Name.Pos(), o.Type, x.Name.Name)
		}
		return
	}
	var declared types.Type
	if o != nil && x.Type != nil {
		declared = o.Type
	}
	value := c.exprWant(scope, x.Value, declared)
	if o == nil {
		return
	}
	if x.Type == nil {
		// Inferred. The declaration pass could not know the type, so fill it
		// in now; nothing has read it yet, because bodies are checked after.
		o.Type = c.inferred(x.Name.Pos(), value, x.Name.Name)
		return
	}
	c.assignableTo(x.Value.Pos(), value, o.Type, "the declaration of "+x.Name.Name)
}

// reportedAt reports whether a diagnostic already exists inside e's extent, so
// a second, vaguer message about the same expression is not added on top.
func (c *checker) reportedAt(e ast.Expr) bool {
	from, to := e.Pos().Offset, e.End().Offset
	for _, d := range c.errs.All() {
		if d.Pos.Offset >= from && d.Pos.Offset <= to {
			return true
		}
	}
	return false
}

func isErrorSetType(t types.Type) bool {
	if named, ok := t.(*types.Named); ok {
		return named.Kind == types.Enum
	}
	_, isUnion := t.(*types.Union)
	return isUnion
}
