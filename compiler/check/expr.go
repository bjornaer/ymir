package check

import (
	"sort"
	"strings"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Expressions.
//
// At M3 this resolves names and nothing else. Every case that does not yet
// know how to compute a type returns types.Invalid, which is assignable in
// both directions, so a not-yet-implemented rule produces silence rather than
// a wrong diagnostic. Milestones M4 through M8 replace the Invalids one at a
// time; the conformance gate's "cases without a compile-error must check
// clean" half is what stops a half-written rule from shipping.

func (c *checker) expr(scope *Scope, e ast.Expr) types.Type {
	t := c.exprInternal(scope, e)
	if e != nil {
		c.info.Types[e] = t
	}
	return t
}

// multiExpr returns every value an expression produces.
//
// Only a call can produce more or fewer than one, and chapter 04 permits a
// multi-valued one only as the entire right side of a destructuring assignment
// or a return — which is exactly where this is used.
//
// known is false when the count is not yet computable, which today means a call
// or a try: their result lists arrive with call typing in M5 and with `try` in
// M8. Callers must not report an arity mismatch while it is false, or every
// `a, b := f()` in the suite becomes a false positive.
func (c *checker) multiExpr(scope *Scope, e ast.Expr) (values []types.Type, known bool) {
	switch e.(type) {
	case *ast.CallExpr, *ast.TryExpr:
		return []types.Type{c.expr(scope, e)}, false
	case *ast.IndexExpr:
		// `v, ok := m[k]` is the two-value map form (chapter 04 §Indexing).
		// Whether this index is one of those depends on the base's type, which
		// arrives with indexing in M5.
		return []types.Type{c.expr(scope, e)}, false
	}
	return []types.Type{c.expr(scope, e)}, true
}

func (c *checker) exprInternal(scope *Scope, e ast.Expr) types.Type {
	switch x := e.(type) {
	case nil, *ast.BadExpr:
		return types.Invalid

	case *ast.Ident:
		return c.ident(scope, x)

	case *ast.BasicLit:
		return c.basicLit(x)

	case *ast.BoolLit:
		return types.Bool

	case *ast.NilLit:
		// nil has its own type, which belongs to every ?T and to nothing else
		// (rule N3). Assignability, not identity, is what accepts it.
		return types.Nil

	case *ast.ParenExpr:
		return c.expr(scope, x.X)

	case *ast.UnaryExpr:
		return c.unaryExpr(scope, x)

	case *ast.BinaryExpr:
		return c.binaryExpr(scope, x)

	case *ast.CallExpr:
		c.callee(scope, x.Fun)
		for _, a := range x.Args {
			c.expr(scope, a)
		}
		return types.Invalid // M5

	case *ast.TryExpr:
		c.expr(scope, x.Call)
		return types.Invalid // M8

	case *ast.IndexExpr:
		c.expr(scope, x.X)
		c.expr(scope, x.Index)
		return types.Invalid // M5

	case *ast.SelectorExpr:
		return c.selector(scope, x)

	case *ast.TupleIndexExpr:
		c.expr(scope, x.X)
		return types.Invalid // M5

	case *ast.ArrayLit:
		for _, el := range x.Elements {
			c.expr(scope, el)
		}
		return types.Invalid // M5

	case *ast.MapLit:
		for _, kv := range x.Entries {
			c.expr(scope, kv.Key)
			c.expr(scope, kv.Value)
		}
		return types.Invalid // M5

	case *ast.TupleLit:
		for _, el := range x.Elements {
			c.expr(scope, el)
		}
		return types.Invalid // M5

	case *ast.StructLit:
		// The literal's head is a type, not an expression, and a field name is
		// a field name — neither is a scope lookup.
		c.resolveType(scope, x.Type)
		for _, f := range x.Fields {
			c.expr(scope, f.Value)
		}
		return types.Invalid // M5

	case *ast.FuncLit:
		sig := c.litSignature(scope, x)
		c.funcBody(scope, nil, nil, x.Params, sig.Params, x.Body)
		return sig
	}

	c.errorf(e.Pos(), "internal: unchecked expression %T", e)
	return types.Invalid
}

// basicLit types a literal. The lexer has already decoded string escapes and
// classified the kind, so this is a mapping and nothing more.
func (c *checker) basicLit(x *ast.BasicLit) types.Type {
	switch x.Kind {
	case token.INT:
		// Fold it, so a literal too large for int64 is reported here rather
		// than silently wrapping (R5).
		c.constOf(x)
		return types.Int
	case token.FLOAT:
		return types.Float
	case token.IMAG:
		return types.Complex
	case token.STRING:
		return types.String
	}
	return types.Invalid
}

// ident resolves a name used as a value.
func (c *checker) ident(scope *Scope, id *ast.Ident) types.Type {
	if id.Name == "_" {
		// "It may appear as an assignment target or a match binding, discards
		// the value, and MUST NOT be read" (chapter 01 §Identifiers).
		c.hint(id.Pos(),
			"cannot read from the blank identifier",
			"_ discards a value; give the binding a name to use it")
		return types.Invalid
	}

	o, _ := scope.LookupParent(id.Name)
	if o == nil {
		// Not a binding. It may be an enum variant named without its enum,
		// which chapter 02 §Enums allows where it is unambiguous. This is
		// checked after scope resolution, so a local named Circle shadows the
		// variant rather than colliding with it.
		if o = c.variant(id); o == nil {
			c.errorf(id.Pos(), "undefined: %s", id.Name)
			return types.Invalid
		}
	}
	c.info.Uses[id] = o

	switch o.Kind {
	case EnumVariant:
		return types.Invalid // M5 types the construction
	case TypeName:
		// A bare type name in value position is only meaningful as a
		// conversion callee or a generic head, both of which are handled at
		// the call site. Typing it as a value waits for M5.
		return types.Invalid
	case Module:
		c.hint(id.Pos(),
			"module "+id.Name+" is not a value",
			"reach a member with "+id.Name+".name")
		return types.Invalid
	}
	return o.Type
}

// variant resolves a bare variant name through the module's variant index,
// reporting an ambiguity rather than picking one.
func (c *checker) variant(id *ast.Ident) *Object {
	cands := c.variants[id.Name]
	switch len(cands) {
	case 0:
		return nil
	case 1:
		return cands[0]
	}
	owners := make([]string, 0, len(cands))
	for _, o := range cands {
		if named, ok := o.Type.(*types.Named); ok {
			owners = append(owners, named.Name+"."+id.Name)
		}
	}
	sort.Strings(owners)
	c.hint(id.Pos(),
		"ambiguous variant "+id.Name+": it belongs to more than one enum",
		"qualify it as "+strings.Join(owners, " or "))
	return cands[0]
}

// callee resolves the function part of a call.
//
// A callee is an arbitrary expression — `fs[0](1)`, `get()()`, `obj.method()`,
// `IOError.NotFound(p)` — so it goes through the ordinary expression path,
// except that a bare type name here is a conversion or a constructor rather
// than a misuse.
func (c *checker) callee(scope *Scope, fun ast.Expr) {
	if id, ok := fun.(*ast.Ident); ok {
		if o, _ := scope.LookupParent(id.Name); o != nil && o.Kind == TypeName {
			// `float(x)`, `int(x)`, `qubit()`. The conversion's arity and
			// argument type are M5.
			c.info.Uses[id] = o
			c.info.Types[id] = types.Invalid
			return
		}
	}
	c.expr(scope, fun)
}

// selector resolves `x.y`, which is three different things depending on x:
// a module member, an enum variant, or a field or method.
func (c *checker) selector(scope *Scope, s *ast.SelectorExpr) types.Type {
	if id, ok := s.X.(*ast.Ident); ok {
		if o, _ := scope.LookupParent(id.Name); o != nil {
			switch o.Kind {
			case Module:
				// Resolving the member needs the imported module's
				// declarations, which do not exist before Phase 6. Record the
				// module reference and accept the member unchecked, rather
				// than reporting a name that is very likely correct.
				c.info.Uses[id] = o
				return types.Invalid

			case TypeName:
				// `IOError.NotFound` — a qualified enum variant. The variant
				// name is not a scope lookup.
				c.info.Uses[id] = o
				if named, isNamed := o.Type.(*types.Named); isNamed && named.Kind == types.Enum {
					if named.LookupVariant(s.Sel.Name) == nil {
						c.errorf(s.Sel.Pos(), "enum %s has no variant %s", named.Name, s.Sel.Name)
					}
				}
				return types.Invalid // M5 gives it the enum's type
			}
		}
	}

	// A field or a method. Both need the receiver's type, so M5.
	c.expr(scope, s.X)
	return types.Invalid
}
