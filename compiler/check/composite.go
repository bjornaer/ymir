package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Composite literals and indexing. Chapter 04 §Composite literals and
// §Indexing and selection.
//
// Composite literals are the one place Ymir types bidirectionally: "Where the
// context supplies an expected type, that type wins." That is what makes
// `var xs: array[int] = []` and `var a: matrix[float] = [[1.0, 2.0]]` work,
// neither of which can be typed from the literal alone.

// wanted strips a nullable from an expected type, since a `T` literal is
// assignable to a `?T` location (rule N4) and the literal itself is never nil.
func wanted(want types.Type) types.Type {
	if want == nil || types.IsInvalid(want) {
		return nil
	}
	if n, ok := want.(*types.Nullable); ok {
		return n.Elem
	}
	return want
}

// arrayLit types `[a, b, c]`, which is an array or a matrix.
func (c *checker) arrayLit(scope *Scope, x *ast.ArrayLit, want types.Type) types.Type {
	switch w := wanted(want).(type) {
	case *types.Array:
		for _, el := range x.Elements {
			t := c.exprWant(scope, el, w.Elem)
			c.assignableTo(el.Pos(), t, w.Elem, "the array literal")
		}
		return w

	case *types.Matrix:
		// Every element must itself be a row literal of the element type.
		row := &types.Array{Elem: w.Elem}
		width := -1
		for _, el := range x.Elements {
			inner, isLit := el.(*ast.ArrayLit)
			if !isLit {
				t := c.exprWant(scope, el, row)
				c.assignableTo(el.Pos(), t, row, "the matrix literal")
				continue
			}
			if width >= 0 && len(inner.Elements) != width {
				c.hint(inner.Pos(),
					"matrix rows must all have the same length: this one has "+
						plural(len(inner.Elements), "element")+", the first had "+
						plural(width, "element"),
					"a matrix is rectangular; use array[array[T]] for a ragged one")
			}
			if width < 0 {
				width = len(inner.Elements)
			}
			c.exprWant(scope, inner, row)
		}
		return w
	}

	// No context: infer from the elements.
	if len(x.Elements) == 0 {
		c.hint(x.Pos(),
			"cannot infer the element type of an empty literal",
			"annotate it: var xs: array[int] = []")
		return types.Invalid
	}

	elems := make([]types.Type, len(x.Elements))
	for i, el := range x.Elements {
		elems[i] = c.exprWant(scope, el, nil)
	}

	elem := elems[0]
	for i := 1; i < len(elems); i++ {
		if types.IsInvalid(elems[i]) || types.IsInvalid(elem) {
			continue
		}
		if !types.Identical(elems[i], elem) {
			c.hint(x.Elements[i].Pos(),
				"array elements must all have the same type: this one is "+
					elems[i].String()+", the first was "+elem.String(),
				"an array is homogeneous; use an enum to hold a mix")
			return types.Invalid
		}
	}
	if types.IsInvalid(elem) {
		return types.Invalid
	}

	// "A nested array literal is matrix[T] when every row has equal length and
	// T is float or complex; otherwise it is array[array[T]]."
	if inner, ok := elem.(*types.Array); ok && types.IsValidMatrixElem(inner.Elem) && rectangular(x) {
		return &types.Matrix{Elem: inner.Elem}
	}
	return &types.Array{Elem: elem}
}

// rectangular reports whether every element of x is an array literal of the
// same length. Only literals can be measured statically.
func rectangular(x *ast.ArrayLit) bool {
	width := -1
	for _, el := range x.Elements {
		inner, ok := el.(*ast.ArrayLit)
		if !ok {
			return false
		}
		if width < 0 {
			width = len(inner.Elements)
		} else if len(inner.Elements) != width {
			return false
		}
	}
	return width >= 0
}

// mapLit types `{"a": 1}`.
func (c *checker) mapLit(scope *Scope, x *ast.MapLit, want types.Type) types.Type {
	if w, ok := wanted(want).(*types.Map); ok {
		for _, e := range x.Entries {
			k := c.exprWant(scope, e.Key, w.Key)
			c.assignableTo(e.Key.Pos(), k, w.Key, "the map literal")
			v := c.exprWant(scope, e.Value, w.Value)
			c.assignableTo(e.Value.Pos(), v, w.Value, "the map literal")
		}
		return w
	}

	if len(x.Entries) == 0 {
		c.hint(x.Pos(),
			"cannot infer the key and value types of an empty literal",
			"annotate it: var m: map[string, int] = {}")
		return types.Invalid
	}

	keys := make([]types.Type, len(x.Entries))
	vals := make([]types.Type, len(x.Entries))
	for i, e := range x.Entries {
		keys[i] = c.exprWant(scope, e.Key, nil)
		vals[i] = c.exprWant(scope, e.Value, nil)
	}

	key, ok := c.uniform(keys, x.Entries[0].Key.Pos(), entryPositions(x, true), "map key")
	if !ok {
		return types.Invalid
	}
	val, ok := c.uniform(vals, x.Entries[0].Value.Pos(), entryPositions(x, false), "map value")
	if !ok {
		return types.Invalid
	}
	if !types.IsValidMapKey(key) {
		c.hint(x.Entries[0].Key.Pos(),
			"map key type "+key.String()+" is not hashable",
			"a key must be a primitive type or a struct whose fields are all primitive")
		return types.Invalid
	}
	return &types.Map{Key: key, Value: val}
}

func entryPositions(x *ast.MapLit, keys bool) []token.Position {
	out := make([]token.Position, len(x.Entries))
	for i, e := range x.Entries {
		if keys {
			out[i] = e.Key.Pos()
		} else {
			out[i] = e.Value.Pos()
		}
	}
	return out
}

// uniform requires every type in ts to be identical, reporting the first that
// is not.
func (c *checker) uniform(ts []types.Type, first token.Position, at []token.Position, what string) (types.Type, bool) {
	t := ts[0]
	for i := 1; i < len(ts); i++ {
		if types.IsInvalid(ts[i]) || types.IsInvalid(t) {
			continue
		}
		if !types.Identical(ts[i], t) {
			c.errorf(at[i], "%ss must all have the same type: this one is %s, the first was %s",
				what, ts[i], t)
			return types.Invalid, false
		}
	}
	return t, !types.IsInvalid(t)
}

// tupleLit types `(1, "one")`.
func (c *checker) tupleLit(scope *Scope, x *ast.TupleLit, want types.Type) types.Type {
	w, _ := wanted(want).(*types.Tuple)

	elems := make([]types.Type, len(x.Elements))
	for i, el := range x.Elements {
		var elemWant types.Type
		if w != nil && i < len(w.Elems) {
			elemWant = w.Elems[i]
		}
		elems[i] = c.exprWant(scope, el, elemWant)
		if elemWant != nil {
			c.assignableTo(el.Pos(), elems[i], elemWant, "the tuple literal")
		}
	}
	if w != nil && len(w.Elems) == len(elems) {
		return w
	}
	return &types.Tuple{Elems: elems}
}

// structLit types `Point{x: 1.0, y: 2.0}`.
//
// "Field initialization MUST be exhaustive and by name. There is no positional
// struct literal and no partial initialization defaulting to zero — a struct
// literal names every field." (chapter 02 §Structs)
func (c *checker) structLit(scope *Scope, x *ast.StructLit) types.Type {
	t := c.resolveType(scope, x.Type)
	named, ok := t.(*types.Named)
	if !ok || named.Kind != types.Struct {
		if !types.IsInvalid(t) {
			c.hint(x.Type.Pos(),
				t.String()+" is not a struct, so it has no field literal",
				"only a struct is built with {field: value}")
		}
		for _, f := range x.Fields {
			c.exprWant(scope, f.Value, nil)
		}
		return types.Invalid
	}

	seen := map[string]bool{}
	for _, f := range x.Fields {
		field := named.LookupField(f.Name.Name)
		if field == nil {
			c.errorf(f.Name.Pos(), "%s has no field %s", named.Name, f.Name.Name)
			c.exprWant(scope, f.Value, nil)
			continue
		}
		if seen[f.Name.Name] {
			c.errorf(f.Name.Pos(), "field %s is initialized twice", f.Name.Name)
		}
		seen[f.Name.Name] = true
		v := c.exprWant(scope, f.Value, field.Type)
		c.assignableTo(f.Value.Pos(), v, field.Type, "the field "+f.Name.Name)
	}

	var missing []string
	for _, field := range named.Fields {
		if !seen[field.Name] {
			missing = append(missing, field.Name)
		}
	}
	if len(missing) > 0 {
		c.hint(x.Rbrace,
			named.Name+" literal is missing "+joinNames(missing),
			"a struct literal names every field; there is no partial initialization")
	}
	return named
}

// ---------------------------------------------------------------------------
// Indexing

// indexExpr types `x[i]` in its single-value form. The two-value map form is
// handled by multiExpr, which is the only place it is legal.
func (c *checker) indexExpr(scope *Scope, x *ast.IndexExpr) types.Type {
	ts := c.indexResults(scope, x)
	return ts[0]
}

// indexResults returns the one or two values an index produces.
func (c *checker) indexResults(scope *Scope, x *ast.IndexExpr) []types.Type {
	base := c.expr(scope, x.X)

	switch b := base.(type) {
	case *types.Array:
		c.requireIntIndex(scope, x, "an array")
		return []types.Type{b.Elem}

	case *types.Map:
		idx := c.exprWant(scope, x.Index, b.Key)
		c.assignableTo(x.Index.Pos(), idx, b.Key, "the map index")
		// "v, ok := m[k]" is the safe accessor; "m[k]" alone panics on an
		// absent key (chapter 02 §map).
		return []types.Type{b.Value, types.Bool}

	case *types.QReg:
		// "Indexing a qreg yields a mutable borrow of one qubit, not a move"
		// (chapter 08 §Registers).
		c.requireIntIndex(scope, x, "a register")
		return []types.Type{types.QubitType}

	case *types.Nullable:
		c.hint(x.Pos(),
			"cannot index "+base.String()+", which may be nil",
			"narrow it first: inside `if x != nil` the checker knows it is "+b.Elem.String())
		c.expr(scope, x.Index)
		return []types.Type{types.Invalid}
	}

	if types.Identical(base, types.String) {
		// "s[3] # string, yields the byte at index 3 as int"
		c.requireIntIndex(scope, x, "a string")
		return []types.Type{types.Int}
	}
	if types.IsInvalid(base) {
		c.expr(scope, x.Index)
		return []types.Type{types.Invalid}
	}
	if _, isTuple := base.(*types.Tuple); isTuple {
		c.hint(x.Pos(),
			"a tuple is not indexed with brackets",
			"write t.0, t.1 and so on; the index must be a literal")
		c.expr(scope, x.Index)
		return []types.Type{types.Invalid}
	}
	if _, isMatrix := base.(*types.Matrix); isMatrix {
		// Chapter 02 defines matrix arithmetic but never defines indexing one.
		// Guessing a shape here would be inventing language, so it is refused
		// and recorded as a spec gap.
		c.hint(x.Pos(),
			"indexing a matrix is not defined in v1",
			"chapter 02 specifies matrix arithmetic only; use array[array[T]] to index")
		c.expr(scope, x.Index)
		return []types.Type{types.Invalid}
	}

	c.errorf(x.Pos(), "cannot index %s", base)
	c.expr(scope, x.Index)
	return []types.Type{types.Invalid}
}

func (c *checker) requireIntIndex(scope *Scope, x *ast.IndexExpr, what string) {
	idx := c.expr(scope, x.Index)
	if types.IsInvalid(idx) || types.Identical(idx, types.Int) {
		return
	}
	c.errorf(x.Index.Pos(), "%s is indexed by int, got %s", what, idx)
}

// tupleIndex types `t.0`.
func (c *checker) tupleIndex(scope *Scope, x *ast.TupleIndexExpr) types.Type {
	base := c.expr(scope, x.X)
	if types.IsInvalid(base) {
		return types.Invalid
	}
	tup, ok := base.(*types.Tuple)
	if !ok {
		c.errorf(x.IdxPos, "%s is not a tuple, so it has no element %d", base, x.Index)
		return types.Invalid
	}
	if x.Index < 0 || x.Index >= len(tup.Elems) {
		c.errorf(x.IdxPos, "%s has %s, so there is no element %d",
			tup, plural(len(tup.Elems), "element"), x.Index)
		return types.Invalid
	}
	return tup.Elems[x.Index]
}

func joinNames(names []string) string {
	switch len(names) {
	case 1:
		return names[0]
	case 2:
		return names[0] + " and " + names[1]
	}
	out := ""
	for i, n := range names[:len(names)-1] {
		if i > 0 {
			out += ", "
		}
		out += n
	}
	return out + ", and " + names[len(names)-1]
}
