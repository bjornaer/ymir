package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/types"
)

// Builtin calls.
//
// Each is typed ad hoc rather than through a types.Func, because most are
// polymorphic in a way no Func can express before Q3 answers whether users can
// write generic functions. `print` is variadic for the same reason, which
// chapter 04 calls a wart to be removed once generics land.

func (c *checker) builtinCall(scope *Scope, x *ast.CallExpr, name string) []types.Type {
	args := c.argTypes(scope, x)

	switch name {
	case "print":
		// Variadic over anything that may be read. A linear value may not be:
		// printing one would read it without consuming it.
		for i, a := range args {
			if types.IsLinear(a) {
				c.errorf(x.Args[i].Pos(), "cannot print %s, which is linear", a)
			}
		}
		return nil

	case "len":
		if !c.wantArity(x, "len", 1, args) {
			return []types.Type{types.Int}
		}
		switch args[0].(type) {
		case *types.Array, *types.Map, *types.QReg:
		default:
			if types.Identical(args[0], types.String) || types.IsInvalid(args[0]) {
				break
			}
			c.errorf(x.Args[0].Pos(), "len is defined on array, map, string and qreg, got %s", args[0])
		}
		return []types.Type{types.Int}

	case "append":
		// "append(xs, 4) # mutates xs in place" (chapter 02 §array), so it
		// yields nothing.
		if !c.wantArity(x, "append", 2, args) {
			return nil
		}
		arr, ok := args[0].(*types.Array)
		if !ok {
			if !types.IsInvalid(args[0]) {
				c.errorf(x.Args[0].Pos(), "append needs an array, got %s", args[0])
			}
			return nil
		}
		c.requireMutable(x.Args[0], "append to")
		c.assignableTo(x.Args[1].Pos(), args[1], arr.Elem, "the call to append")
		return nil

	case "copy":
		if !c.wantArity(x, "copy", 1, args) {
			return []types.Type{types.Invalid}
		}
		// "There is no copy(q) and no way to write one — copy is defined only
		// on unrestricted types" (chapter 08 §No-cloning).
		if types.IsLinear(args[0]) {
			c.hint(x.Args[0].Pos(),
				"copy is defined only on unrestricted types, and "+args[0].String()+" is linear",
				"this is the no-cloning theorem; there is no way to duplicate it")
			return []types.Type{types.Invalid}
		}
		return []types.Type{args[0]}

	case "delete":
		if !c.wantArity(x, "delete", 2, args) {
			return nil
		}
		m, ok := args[0].(*types.Map)
		if !ok {
			if !types.IsInvalid(args[0]) {
				c.errorf(x.Args[0].Pos(), "delete needs a map, got %s", args[0])
			}
			return nil
		}
		c.requireMutable(x.Args[0], "delete from")
		c.assignableTo(x.Args[1].Pos(), args[1], m.Key, "the call to delete")
		return nil

	case "chars":
		if !c.wantArity(x, "chars", 1, args) {
			return []types.Type{&types.Array{Elem: types.Int}}
		}
		if !types.IsInvalid(args[0]) && !types.Identical(args[0], types.String) {
			c.errorf(x.Args[0].Pos(), "chars needs a string, got %s", args[0])
		}
		return []types.Type{&types.Array{Elem: types.Int}}

	case "range":
		// range(a, b) and range(a, b, step). Chapter 05 §for shows both.
		if len(args) < 1 || len(args) > 3 {
			c.errorf(x.Rparen, "range takes 1 to 3 int arguments, got %d", len(args))
			return []types.Type{&types.Array{Elem: types.Int}}
		}
		for i, a := range args {
			if !types.IsInvalid(a) && !types.Identical(a, types.Int) {
				c.errorf(x.Args[i].Pos(), "range takes int arguments, got %s", a)
			}
		}
		return []types.Type{&types.Array{Elem: types.Int}}

	case "enumerate":
		if !c.wantArity(x, "enumerate", 1, args) {
			return []types.Type{types.Invalid}
		}
		arr, ok := args[0].(*types.Array)
		if !ok {
			if !types.IsInvalid(args[0]) {
				c.errorf(x.Args[0].Pos(), "enumerate needs an array, got %s", args[0])
			}
			return []types.Type{types.Invalid}
		}
		return []types.Type{&types.Array{Elem: &types.Tuple{Elems: []types.Type{types.Int, arr.Elem}}}}

	case "str":
		if !c.wantArity(x, "str", 1, args) {
			return []types.Type{types.String}
		}
		if types.IsLinear(args[0]) {
			c.errorf(x.Args[0].Pos(), "cannot convert %s to string, it is linear", args[0])
		}
		return []types.Type{types.String}

	case "panic":
		if !c.wantArity(x, "panic", 1, args) {
			return nil
		}
		if !types.IsInvalid(args[0]) && !types.Identical(args[0], types.String) {
			c.errorf(x.Args[0].Pos(), "panic takes a string message, got %s", args[0])
		}
		return nil

	case "Error":
		// "Error(s) is sugar for error.Msg(s)" (chapter 06).
		if !c.wantArity(x, "Error", 1, args) {
			return []types.Type{types.ErrorEnum}
		}
		if !types.IsInvalid(args[0]) && !types.Identical(args[0], types.String) {
			c.errorf(x.Args[0].Pos(), "Error takes a string message, got %s", args[0])
		}
		return []types.Type{types.ErrorEnum}

	case "close":
		if !c.wantArity(x, "close", 1, args) {
			return nil
		}
		if _, ok := args[0].(*types.Chan); !ok && !types.IsInvalid(args[0]) {
			c.errorf(x.Args[0].Pos(), "close needs a channel, got %s", args[0])
		}
		return nil

	case "real", "imag":
		if !c.wantArity(x, name, 1, args) {
			return []types.Type{types.Float}
		}
		if !types.IsInvalid(args[0]) && !types.Identical(args[0], types.Complex) {
			c.errorf(x.Args[0].Pos(), "%s needs a complex, got %s", name, args[0])
		}
		return []types.Type{types.Float}

	case "make_chan":
		c.hint(x.Fun.Pos(),
			"make_chan needs an element type",
			"write make_chan[int]() or make_chan[int](capacity)")
		return []types.Type{types.Invalid}

	case "measure", "measure_all", "reset", "discard":
		c.hint(x.Fun.Pos(),
			"the quantum fragment is not implemented yet",
			"chapter 08 is normative but unimplemented; see PLAN.md phase 7")
		return []types.Type{types.Invalid}
	}

	c.errorf(x.Fun.Pos(), "internal: builtin %s has no signature", name)
	return []types.Type{types.Invalid}
}
