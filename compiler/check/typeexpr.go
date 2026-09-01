package check

import (
	"strconv"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Resolving written types to semantic ones.
//
// This is where ast.Type — a record of what was typed — becomes types.Type, and
// where the formation constraints of chapter 02 are enforced: a map key must be
// hashable, a matrix element must be float or complex, a union member must be
// an enum, and ? requires an unrestricted type (rule N5).
//
// Every failure yields types.Invalid, which is assignable in both directions,
// so one bad annotation does not produce a cascade of follow-on errors.

// resolveType turns a written type into a semantic one, reporting any problem
// at the offending node.
func (c *checker) resolveType(scope *Scope, t ast.Type) types.Type {
	switch x := t.(type) {
	case nil:
		return types.Invalid

	case *ast.Ident:
		return c.resolveTypeName(scope, x.Name, x.NamePos)

	case *ast.NamedType:
		parts := x.Name.Parts
		if len(parts) == 1 {
			return c.resolveTypeName(scope, parts[0].Name, parts[0].NamePos)
		}
		// A qualified type name, `math.Complex`. Resolving it needs the
		// imported module's declarations, which do not exist before Phase 6.
		// Accept it as unknown rather than reporting a name that is not wrong.
		if o := c.lookup(scope, parts[0].Name, parts[0].NamePos); o != nil && o.Kind != Module {
			c.errorf(parts[0].NamePos, "%s is a %s, not a module", parts[0].Name, o.Kind)
		}
		return types.Invalid

	case *ast.GenericType:
		return c.resolveGeneric(scope, x)

	case *ast.FuncType:
		f := &types.Func{}
		for _, p := range x.Params {
			f.Params = append(f.Params, c.resolveType(scope, p))
		}
		for _, r := range x.Results {
			f.Results = append(f.Results, c.resolveType(scope, r))
		}
		return f

	case *ast.NullableType:
		elem := c.resolveType(scope, x.Elem)
		if types.IsInvalid(elem) {
			return types.Invalid
		}
		// Rule N5. A linear value that may be absent cannot be consumed
		// exactly once, and every branch would have to prove which case it was
		// in (rule L4).
		if types.IsLinear(elem) {
			c.hint(x.Question,
				"? requires an unrestricted type, and "+elem.String()+" is linear",
				"a linear value must be consumed exactly once, which an absent one cannot be")
			return types.Invalid
		}
		return types.NewNullable(elem)

	case *ast.UnionType:
		return c.resolveUnion(scope, x)
	}

	c.errorf(t.Pos(), "not a type")
	return types.Invalid
}

// resolveTypeName resolves a bare type name through the scope chain.
func (c *checker) resolveTypeName(scope *Scope, name string, pos token.Position) types.Type {
	// The parameterized built-ins are not types until applied. Naming one
	// bare is a mistake worth its own message.
	if _, isGeneric := types.GenericNames[name]; isGeneric {
		c.hint(pos,
			name+" needs type arguments",
			"write "+name+"[T]")
		return types.Invalid
	}

	o, _ := scope.LookupParent(name)
	if o == nil {
		c.errorf(pos, "undefined type: %s", name)
		return types.Invalid
	}
	if o.Kind != TypeName {
		c.errorf(pos, "%s is a %s, not a type", name, o.Kind)
		return types.Invalid
	}
	return o.Type
}

// resolveGeneric handles array[T], map[K, V], tuple[...], matrix[T], chan[T]
// and qreg[N]. The parser accepts any name with any arity, so both are checked
// here.
func (c *checker) resolveGeneric(scope *Scope, x *ast.GenericType) types.Type {
	name := x.Name.Name
	arity, known := types.GenericNames[name]
	if !known {
		// Not a built-in. Until Q3 answers whether users can declare generic
		// types, nothing else can be applied to type arguments.
		if o, _ := scope.LookupParent(name); o != nil && o.Kind == TypeName {
			c.hint(x.Name.NamePos,
				name+" does not take type arguments",
				"user-defined generic types are not in v1; see open question Q3")
		} else {
			c.errorf(x.Name.NamePos, "undefined type: %s", name)
		}
		return types.Invalid
	}

	if name == "qreg" {
		// The odd one out: its argument is a compile-time integer constant
		// rather than a type, so the parser puts it in Width and leaves Args
		// empty. The arity check below does not apply.
		return c.resolveQReg(x)
	}
	if arity >= 0 && len(x.Args) != arity {
		c.errorf(x.Name.NamePos, "%s takes %s, got %d",
			name, plural(arity, "type argument"), len(x.Args))
		return types.Invalid
	}

	switch name {
	case "array":
		elem := c.resolveType(scope, x.Args[0])
		if !c.requireUnrestricted(x.Args[0].Pos(), elem, "array") {
			return types.Invalid
		}
		return &types.Array{Elem: elem}

	case "map":
		key := c.resolveType(scope, x.Args[0])
		val := c.resolveType(scope, x.Args[1])
		if !types.IsInvalid(key) && !types.IsValidMapKey(key) {
			c.hint(x.Args[0].Pos(),
				"map key type "+key.String()+" is not hashable",
				"a key must be a primitive type or a struct whose fields are all primitive")
			return types.Invalid
		}
		if !c.requireUnrestricted(x.Args[1].Pos(), val, "map") {
			return types.Invalid
		}
		return &types.Map{Key: key, Value: val}

	case "tuple":
		if len(x.Args) == 0 {
			c.errorf(x.Name.NamePos, "tuple takes at least one type argument")
			return types.Invalid
		}
		tup := &types.Tuple{}
		for _, a := range x.Args {
			el := c.resolveType(scope, a)
			if !c.requireUnrestricted(a.Pos(), el, "tuple") {
				return types.Invalid
			}
			tup.Elems = append(tup.Elems, el)
		}
		return tup

	case "matrix":
		elem := c.resolveType(scope, x.Args[0])
		if !types.IsInvalid(elem) && !types.IsValidMatrixElem(elem) {
			c.errorf(x.Args[0].Pos(),
				"matrix element type must be float or complex, got %s", elem)
			return types.Invalid
		}
		return &types.Matrix{Elem: elem}

	case "chan":
		elem := c.resolveType(scope, x.Args[0])
		if !c.requireUnrestricted(x.Args[0].Pos(), elem, "chan") {
			return types.Invalid
		}
		return &types.Chan{Elem: elem}
	}

	c.errorf(x.Name.NamePos, "undefined type: %s", name)
	return types.Invalid
}

func (c *checker) resolveQReg(x *ast.GenericType) types.Type {
	if x.Width == nil {
		c.hint(x.Name.NamePos,
			"qreg takes a constant integer width",
			"write qreg[4]")
		return types.Invalid
	}
	n, err := strconv.Atoi(x.Width.Value)
	if err != nil || n <= 0 {
		c.errorf(x.Width.Pos(), "qreg width must be a positive integer, got %s", x.Width.Value)
		return types.Invalid
	}
	return &types.QReg{N: n}
}

// requireUnrestricted enforces R8: a container of a linear type is ill-formed.
//
// Rule L1 requires proving that every linear value is consumed exactly once, and a
// container's length is a runtime value, so no such proof exists for one. `qreg[N]`
// is the collection-of-qubits type, with N a compile-time constant.
func (c *checker) requireUnrestricted(pos token.Position, elem types.Type, container string) bool {
	if types.IsInvalid(elem) || !types.IsLinear(elem) {
		return true
	}
	hint := "a linear value must be consumed exactly once, which cannot be proved for a container of runtime length"
	if _, isQubit := elem.(*types.Qubit); isQubit {
		hint = "use qreg[N], the collection-of-qubits type, whose width is a compile-time constant"
	}
	c.hint(pos, container+" cannot hold "+elem.String()+", which is linear", hint)
	return false
}

// resolveUnion builds a union, enforcing that every member is an enum
// (chapter 02 §Union types: `int | string` is not a type).
func (c *checker) resolveUnion(scope *Scope, x *ast.UnionType) types.Type {
	members := make([]types.Type, 0, len(x.Members))
	bad := false
	for _, m := range x.Members {
		mt := c.resolveType(scope, m)
		if types.IsInvalid(mt) {
			bad = true
			continue
		}
		if !types.IsErrorSet(mt) {
			c.hint(m.Pos(),
				"union members must be enums, and "+mt.String()+" is not",
				"Ymir has no general union types; only enums can be unioned")
			bad = true
			continue
		}
		members = append(members, mt)
	}
	if bad {
		return types.Invalid
	}
	return types.NewUnion(members...)
}

func plural(n int, noun string) string {
	if n == 1 {
		return "1 " + noun
	}
	return strconv.Itoa(n) + " " + noun + "s"
}
