package check

import (
	"strconv"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Calls.
//
// "Argument count and types MUST match exactly. There are no default
// parameters, no variadic user functions, and no keyword arguments in v1."
// (chapter 04 §Calls)
//
// A callee is an arbitrary expression, so `f(a)`, `p.magnitude()`,
// `math.sqrt(2.0)`, `Circle(2.0)`, `fs[0](1)` and `get()()` all arrive here.
// Sorting out which is which is most of the work.

// call types a call and returns its result list, which may be empty.
func (c *checker) call(scope *Scope, x *ast.CallExpr) []types.Type {
	// A few callees are not values and must be recognized before the operand
	// is typed, or resolving them as values would report a spurious error.
	switch fun := x.Fun.(type) {
	case *ast.Ident:
		if fun.Name == "main" {
			// "main is invoked automatically; it MUST NOT be called
			// explicitly." (chapter 03 §main)
			if o, _ := scope.LookupParent("main"); o != nil && o.Kind == Func {
				c.hint(fun.Pos(),
					"main is invoked by the runtime and must not be called explicitly",
					"move the work into a function both main and this caller can call")
			}
		}
		if o, _ := scope.LookupParent(fun.Name); o != nil {
			switch o.Kind {
			case Builtin:
				c.info.Uses[fun] = o
				c.info.Types[fun] = types.Invalid
				return c.builtinCall(scope, x, fun.Name)
			case TypeName:
				c.info.Uses[fun] = o
				c.info.Types[fun] = types.Invalid
				return c.conversionCall(scope, x, fun.Name, o.Type)
			}
		}
		if o := c.variants[fun.Name]; len(o) > 0 {
			if v := c.variant(fun); v != nil {
				c.info.Uses[fun] = v
				c.info.Types[fun] = types.Invalid
				return c.variantCall(scope, x, v, fun.Name)
			}
		}

	case *ast.SelectorExpr:
		if rs, handled := c.qualifiedCall(scope, x, fun); handled {
			return rs
		}

	case *ast.IndexExpr:
		// `make_chan[int](10)`: a builtin applied to a type argument. It is the
		// only one, and it exists because Q3 has not answered whether users can
		// write generic functions.
		if id, ok := fun.X.(*ast.Ident); ok && id.Name == "make_chan" {
			if o, _ := scope.LookupParent(id.Name); o != nil && o.Kind == Builtin {
				c.info.Uses[id] = o
				c.info.Types[id] = types.Invalid
				return c.makeChanCall(scope, x, fun)
			}
		}
		// `qreg[3]()` allocates a register (chapter 08 §Registers). Its width
		// is a compile-time constant, not a type argument, which is why it does
		// not go through the generic-type path.
		if id, ok := fun.X.(*ast.Ident); ok && id.Name == "qreg" {
			c.info.Types[id] = types.Invalid
			return c.qregCall(scope, x, fun)
		}
	}

	// An ordinary value that must be callable. The callee is typed first, so
	// the arguments can be typed against its parameters.
	fnType := c.expr(scope, x.Fun)
	if types.IsInvalid(fnType) {
		c.argTypes(scope, x)
		return []types.Type{types.Invalid}
	}
	sig, ok := fnType.(*types.Func)
	if !ok {
		c.argTypes(scope, x)
		c.errorf(x.Fun.Pos(), "cannot call %s, which is not a function", fnType)
		return []types.Type{types.Invalid}
	}
	saved := c.callSig
	c.callSig = sig
	args := c.argTypesWant(scope, x, sig.Params)
	c.callSig = saved
	c.checkArgs(x, calleeName(x.Fun), sig.Params, args)
	c.checkNoAliasedBorrows(x, calleeName(x.Fun), sig)
	return sig.Results
}

// callWithParams types arguments against known parameter types and checks them.
func (c *checker) callWithParams(scope *Scope, x *ast.CallExpr, name string, params []types.Type) {
	args := c.argTypesWant(scope, x, params)
	c.checkArgs(x, name, params, args)
}

// callWithSig is callWithParams for a signature that carries `mut` markers, so
// a borrowed argument is not consumed (rule L3).
func (c *checker) callWithSig(scope *Scope, x *ast.CallExpr, name string, sig *types.Func) {
	saved := c.callSig
	c.callSig = sig
	args := c.argTypesWant(scope, x, sig.Params)
	c.callSig = saved
	c.checkArgs(x, name, sig.Params, args)
}

// qualifiedCall handles `a.b(...)`: a module member, a qualified enum variant,
// or a method.
func (c *checker) qualifiedCall(scope *Scope, x *ast.CallExpr, sel *ast.SelectorExpr) ([]types.Type, bool) {
	if id, ok := sel.X.(*ast.Ident); ok {
		if o, _ := scope.LookupParent(id.Name); o != nil {
			switch o.Kind {
			case Module:
				// The member's signature lives in the imported module, which
				// does not exist before Phase 6. Type the arguments so their
				// own errors are still found, then give up on the result.
				c.info.Uses[id] = o
				c.argTypes(scope, x)
				return []types.Type{types.Invalid}, true

			case TypeName:
				named, isNamed := o.Type.(*types.Named)
				if isNamed && named.Kind == types.Enum {
					c.info.Uses[id] = o
					v := named.LookupVariant(sel.Sel.Name)
					if v == nil {
						c.errorf(sel.Sel.Pos(), "enum %s has no variant %s", named.Name, sel.Sel.Name)
						c.argTypes(scope, x)
						return []types.Type{types.Invalid}, true
					}
					c.callWithParams(scope, x, named.Name+"."+v.Name, v.Payload)
					return []types.Type{named}, true
				}
			}
		}
	}

	// A method. The receiver is an ordinary expression.
	recv := c.expr(scope, sel.X)
	if types.IsInvalid(recv) {
		c.argTypes(scope, x)
		return []types.Type{types.Invalid}, true
	}
	m := c.lookupMethod(recv, sel.Sel.Name)
	if m == nil {
		// Not a method. It may be a function-valued field, which the ordinary
		// path below handles.
		return nil, false
	}
	c.callWithSig(scope, x, recv.String()+"."+sel.Sel.Name, m.sig)
	if m.mutRecv {
		c.requireMutable(sel.X, "call "+sel.Sel.Name+", which takes a mut receiver")
	}
	return m.sig.Results, true
}

// variantCall constructs an enum variant named without its enum.
func (c *checker) variantCall(scope *Scope, x *ast.CallExpr, o *Object, name string) []types.Type {
	named, ok := o.Type.(*types.Named)
	if !ok {
		return []types.Type{types.Invalid}
	}
	v := named.LookupVariant(name)
	if v == nil {
		return []types.Type{types.Invalid}
	}
	c.callWithParams(scope, x, named.Name+"."+name, v.Payload)
	return []types.Type{named}
}

// conversionCall handles float(x), int(x), complex(x), and qubit().
//
// These share their names with type names, which is why they are recognized
// from the call site rather than from scope.
func (c *checker) conversionCall(scope *Scope, x *ast.CallExpr, name string, target types.Type) []types.Type {
	args := c.argTypes(scope, x)

	switch name {
	case "float", "int", "complex":
		if !c.wantArity(x, name, 1, args) {
			return []types.Type{target}
		}
		if !types.IsInvalid(args[0]) && !types.IsNumeric(args[0]) {
			c.errorf(x.Args[0].Pos(), "cannot convert %s to %s", args[0], name)
		}
		return []types.Type{target}

	case "qubit":
		// Allocation: `q := qubit()` yields a fresh qubit in |0>, which the
		// linearity checker then requires be consumed exactly once.
		c.wantArity(x, "qubit", 0, args)
		return []types.Type{types.QubitType}
	}

	// A struct or enum name used as a call. Struct literals are written
	// Point{...}, not Point(...), and an enum is constructed by variant.
	c.hint(x.Fun.Pos(),
		name+" is a type, not a function",
		"a struct is built with "+name+"{field: value}, an enum by naming a variant")
	return []types.Type{types.Invalid}
}

// qregCall types `qreg[N]()`, whose width is a compile-time constant.
func (c *checker) qregCall(scope *Scope, x *ast.CallExpr, idx *ast.IndexExpr) []types.Type {
	args := c.argTypes(scope, x)
	c.wantArity(x, "qreg", 0, args)

	lit, ok := idx.Index.(*ast.BasicLit)
	if !ok || lit.Kind != token.INT {
		c.hint(idx.Index.Pos(),
			"qreg takes a constant integer width",
			"write qreg[4]()")
		return []types.Type{types.Invalid}
	}
	n, err := strconv.Atoi(lit.Value)
	if err != nil || n <= 0 {
		c.errorf(idx.Index.Pos(), "qreg width must be a positive integer, got %s", lit.Value)
		return []types.Type{types.Invalid}
	}
	return []types.Type{&types.QReg{N: n}}
}

// checkNoAliasedBorrows enforces chapter 08 §Gates: "Two `mut` borrows in one
// call MUST refer to distinct qubits. cnot(q, q) is a compile error where
// aliasing is statically visible, and a panic otherwise."
func (c *checker) checkNoAliasedBorrows(x *ast.CallExpr, name string, sig *types.Func) {
	seen := map[*Object]*ast.Ident{}
	for i, a := range x.Args {
		if !sig.MutAt(i) {
			continue
		}
		id, ok := a.(*ast.Ident)
		if !ok {
			continue // not statically visible; a runtime check per chapter 08
		}
		o := c.info.Uses[id]
		if o == nil {
			continue
		}
		if prev, dup := seen[o]; dup {
			c.hint(id.Pos(),
				name+" borrows "+id.Name+" twice, and two mut borrows must be distinct",
				"the first is at "+prev.Pos().String())
			continue
		}
		seen[o] = id
	}
}

// makeChanCall types `make_chan[T]()` and `make_chan[T](capacity)`.
func (c *checker) makeChanCall(scope *Scope, x *ast.CallExpr, idx *ast.IndexExpr) []types.Type {
	elem := c.typeArgument(scope, idx.Index)
	args := c.argTypes(scope, x)

	switch len(args) {
	case 0:
		// Unbuffered.
	case 1:
		if !types.IsInvalid(args[0]) && !types.Identical(args[0], types.Int) {
			c.errorf(x.Args[0].Pos(), "channel capacity must be int, got %s", args[0])
		}
	default:
		c.errorf(x.Rparen, "make_chan takes at most one argument, the capacity")
	}

	if types.IsInvalid(elem) {
		return []types.Type{types.Invalid}
	}
	return []types.Type{&types.Chan{Elem: elem}}
}

// typeArgument reads a type written in expression position, as in the `int` of
// `make_chan[int](10)`. The parser cannot know it is a type there.
func (c *checker) typeArgument(scope *Scope, e ast.Expr) types.Type {
	switch x := e.(type) {
	case *ast.Ident:
		return c.resolveTypeName(scope, x.Name, x.NamePos)
	case *ast.IndexExpr:
		// A nested parameterized type, as in make_chan[array[int]].
		if id, ok := x.X.(*ast.Ident); ok {
			return c.resolveGeneric(scope, &ast.GenericType{
				Name:   id,
				Args:   []ast.Type{exprAsTypeNode(x.Index)},
				Rbrack: x.Rbrack,
			})
		}
	}
	c.errorf(e.Pos(), "expected a type argument")
	return types.Invalid
}

// exprAsTypeNode reinterprets an expression as the type it spells. Only names
// and nested applications can be types, which is all the built-ins need.
func exprAsTypeNode(e ast.Expr) ast.Type {
	switch x := e.(type) {
	case *ast.Ident:
		return &ast.NamedType{Name: &ast.QualifiedIdent{Parts: []*ast.Ident{x}}}
	case *ast.IndexExpr:
		if id, ok := x.X.(*ast.Ident); ok {
			return &ast.GenericType{
				Name:   id,
				Args:   []ast.Type{exprAsTypeNode(x.Index)},
				Rbrack: x.Rbrack,
			}
		}
	}
	return nil
}

// argTypes types every argument, left to right, which is the normative
// evaluation order (chapter 04 §Evaluation order).
func (c *checker) argTypes(scope *Scope, x *ast.CallExpr) []types.Type {
	return c.argTypesWant(scope, x, nil)
}

// argTypesWant types arguments against the parameter types, so a composite
// literal argument can be typed from the parameter it fills.
func (c *checker) argTypesWant(scope *Scope, x *ast.CallExpr, params []types.Type) []types.Type {
	args := make([]types.Type, len(x.Args))
	for i, a := range x.Args {
		var want types.Type
		if i < len(params) {
			want = params[i]
		}
		if c.paramBorrows(i) {
			// Rule L3: "Passing a linear value as an argument consumes it,
			// unless the parameter is declared `mut`, which borrows it for the
			// call's duration."
			c.borrow(func() { args[i] = c.exprWant(scope, a, want) })
			continue
		}
		args[i] = c.exprWant(scope, a, want)
	}
	return args
}

// paramBorrows reports whether the parameter at index i of the signature
// currently being applied is declared `mut`.
func (c *checker) paramBorrows(i int) bool {
	return c.callSig != nil && c.callSig.MutAt(i)
}

// checkArgs enforces exact arity and assignability.
func (c *checker) checkArgs(x *ast.CallExpr, name string, params, args []types.Type) {
	if !c.wantArity(x, name, len(params), args) {
		return
	}
	for i, p := range params {
		c.assignableTo(x.Args[i].Pos(), args[i], p, "the call to "+name)
	}
}

func (c *checker) wantArity(x *ast.CallExpr, name string, want int, args []types.Type) bool {
	if len(args) == want {
		return true
	}
	pos := x.Rparen
	if len(args) > want && want < len(x.Args) {
		pos = x.Args[want].Pos()
	}
	c.errorf(pos, "%s takes %s, got %d", name, plural(want, "argument"), len(args))
	return false
}

// calleeName renders a callee for a diagnostic.
func calleeName(e ast.Expr) string {
	switch x := e.(type) {
	case *ast.Ident:
		return x.Name
	case *ast.SelectorExpr:
		return calleeName(x.X) + "." + x.Sel.Name
	}
	return "this call"
}

// requireMutable reports when a mutable receiver is taken from something that
// cannot provide one.
func (c *checker) requireMutable(e ast.Expr, what string) {
	id, ok := e.(*ast.Ident)
	if !ok {
		return // a field or index target; M6 tracks their mutability
	}
	o := c.info.Uses[id]
	if o == nil {
		return
	}
	if o.Kind == Const || (o.Kind == Var && !o.Mutable) {
		c.hint(e.Pos(),
			"cannot "+what+": "+id.Name+" is not mutable",
			"mark the parameter `mut` to take a mutable reference")
	}
}

// ---------------------------------------------------------------------------
// Method sets

// method is one declared method.
type method struct {
	sig     *types.Func
	mutRecv bool
	name    string
}

// collectMethods records every method against its receiver type.
//
// "Methods are not virtual — the receiver's type is statically known at every
// call site" (chapter 02 §Structs), so a flat table per named type is the whole
// mechanism. There is no embedding and no promotion.
func (c *checker) collectMethods(file *ast.File) {
	for _, d := range file.Decls {
		x, isFunc := d.(*ast.FuncDecl)
		if !isFunc || x.Recv == nil {
			continue
		}
		recv := c.recvs[x]
		named, ok := recv.(*types.Named)
		if !ok {
			if !types.IsInvalid(recv) {
				c.hint(x.Recv.Pos(),
					"cannot declare a method on "+recv.String(),
					"a receiver must be a struct or enum declared in this module")
			}
			continue
		}
		set := c.methods[named]
		if set == nil {
			set = map[string]*method{}
			c.methods[named] = set
		}
		if _, dup := set[x.Name.Name]; dup {
			c.errorf(x.Name.Pos(), "%s already has a method %s", named.Name, x.Name.Name)
			continue
		}
		if named.LookupField(x.Name.Name) != nil {
			c.errorf(x.Name.Pos(), "%s already has a field %s", named.Name, x.Name.Name)
			continue
		}
		set[x.Name.Name] = &method{sig: c.sigs[x], mutRecv: x.Recv.Mut, name: x.Name.Name}
	}
}

// lookupMethod finds a method on a receiver type, seeing through a nullable
// only insofar as reporting is concerned: a ?T must be narrowed first (N4), and
// that error is reported where the receiver is used.
func (c *checker) lookupMethod(recv types.Type, name string) *method {
	named, ok := recv.(*types.Named)
	if !ok {
		return nil
	}
	return c.methods[named][name]
}
