package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Name resolution: every identifier resolves at compile time or the program
// does not build (chapter 03 §Variables).
//
// The traversal here is hand-written rather than ast.Walk, because resolution
// is context-sensitive in ways a uniform walk cannot express. An *ast.Ident is
// a variable reference in `x + 1`, a declaration in `x := 1`, a field name in
// `Point{x: 1.0}`, a variant name in `Circle(r)`, and a selector in `p.x` —
// five different meanings for one node type. ast.Walk is for passes that treat
// every node alike; this is not one.
//
// Expression *typing* lands in M5. Until then c.expr resolves names, records
// what it can, and returns types.Invalid for everything it does not yet
// understand — which is assignable in both directions, so it produces no
// follow-on errors.

func (c *checker) checkFile(file *ast.File) {
	if file == nil {
		return
	}

	universe := newUniverse()
	module := NewScope(universe, ModuleScope)
	fileScope := NewScope(module, FileScope)

	moduleName := ""
	if file.Module != nil {
		moduleName = file.Module.Name.String()
	}
	c.module = moduleName

	c.collectImports(fileScope, file)
	c.collectTypeNames(module, file)
	c.resolveTypeBodies(fileScope, file)
	c.indexVariants(file)
	c.collectValues(fileScope, module, file)
	c.collectMethods(file)
	c.checkBodies(fileScope, file)
}

// ---------------------------------------------------------------------------
// Module-scope pre-passes
//
// Module-scope declarations are visible regardless of textual order
// (chapter 03 §Scope), so names are collected before any body is checked. Types
// are collected before values, and their fields resolved in between, so that
// two structs may name each other.

func (c *checker) collectImports(fileScope *Scope, file *ast.File) {
	for _, imp := range file.Imports {
		name := imp.Alias
		if name == nil {
			// `import a.b.c` binds `c`.
			name = imp.Path.Parts[len(imp.Path.Parts)-1]
		}
		o := &Object{
			Kind: Module,
			Name: name.Name,
			Type: types.Invalid, // a module is not a value
			Pos:  name.Pos(),
		}
		c.declare(fileScope, o)
		c.info.Defs[name] = o
	}
}

// collectTypeNames allocates one *types.Named per struct and enum declaration
// and binds it, with no fields or variants yet. Nominal identity is pointer
// identity, so this must happen exactly once per declaration.
func (c *checker) collectTypeNames(module *Scope, file *ast.File) {
	for _, d := range file.Decls {
		var (
			id   *ast.Ident
			kind types.NamedKind
			exp  bool
		)
		switch x := d.(type) {
		case *ast.StructDecl:
			id, kind, exp = x.Name, types.Struct, x.Export
		case *ast.EnumDecl:
			id, kind, exp = x.Name, types.Enum, x.Export
		default:
			continue
		}

		named := &types.Named{Kind: kind, Module: c.module, Name: id.Name}
		o := &Object{
			Kind:     TypeName,
			Name:     id.Name,
			Type:     named,
			Pos:      id.Pos(),
			Exported: exp,
		}
		c.declare(module, o)
		c.info.Defs[id] = o
	}
}

// resolveTypeBodies fills in fields and variants, now that every type name is
// bound.
func (c *checker) resolveTypeBodies(scope *Scope, file *ast.File) {
	for _, d := range file.Decls {
		switch x := d.(type) {
		case *ast.StructDecl:
			named := c.namedFor(x.Name)
			if named == nil {
				continue
			}
			seen := map[string]token.Position{}
			for _, f := range x.Fields {
				if prev, dup := seen[f.Name.Name]; dup {
					c.hint(f.Name.Pos(),
						"duplicate field "+f.Name.Name+" in struct "+x.Name.Name,
						"the first one is at "+prev.String())
					continue
				}
				seen[f.Name.Name] = f.Name.Pos()
				named.Fields = append(named.Fields, &types.Field{
					Name: f.Name.Name,
					Type: c.resolveType(scope, f.Type),
				})
			}

		case *ast.EnumDecl:
			named := c.namedFor(x.Name)
			if named == nil {
				continue
			}
			seen := map[string]token.Position{}
			for _, v := range x.Variants {
				if prev, dup := seen[v.Name.Name]; dup {
					c.hint(v.Name.Pos(),
						"duplicate variant "+v.Name.Name+" in enum "+x.Name.Name,
						"the first one is at "+prev.String())
					continue
				}
				seen[v.Name.Name] = v.Name.Pos()
				vt := &types.Variant{Name: v.Name.Name}
				for _, p := range v.Payload {
					vt.Payload = append(vt.Payload, c.resolveType(scope, p))
				}
				named.Variants = append(named.Variants, vt)
			}
		}
	}
}

// indexVariants records every variant of every enum declared in this module,
// keyed by its bare name.
//
// Chapter 02 §Enums: "Construction names the variant, qualified where
// ambiguous." Unqualified is therefore the normal spelling, and the qualifier
// is required only when two enums in the module share a variant name. Variants
// are deliberately not inserted into module scope: they are reached through
// this index only after ordinary name resolution fails, so a local binding
// named Circle still shadows the variant.
func (c *checker) indexVariants(file *ast.File) {
	for _, d := range file.Decls {
		x, isEnum := d.(*ast.EnumDecl)
		if !isEnum {
			continue
		}
		named := c.namedFor(x.Name)
		if named == nil {
			continue
		}
		for _, v := range named.Variants {
			c.variants[v.Name] = append(c.variants[v.Name], &Object{
				Kind: EnumVariant,
				Name: v.Name,
				Type: named, // constructing it yields the enum
				Pos:  x.Name.Pos(),
			})
		}
	}
}

// collectValues binds functions, constants and module-level vars.
//
// It resolves types through fileScope (so a signature may name an imported
// type) but inserts into moduleScope (so the name is visible everywhere in the
// module, which is what case scope/module_var_mutation asserts).
func (c *checker) collectValues(fileScope, module *Scope, file *ast.File) {
	for _, d := range file.Decls {
		switch x := d.(type) {
		case *ast.FuncDecl:
			sig := c.signature(fileScope, x)
			c.sigs[x] = sig
			if x.Recv != nil {
				// A method is reached through its receiver, not through module
				// scope. Method sets land with expression typing in M5.
				if x.Recv.Type != nil {
					c.recvs[x] = c.resolveType(fileScope, x.Recv.Type)
				}
				continue
			}
			o := &Object{
				Kind:     Func,
				Name:     x.Name.Name,
				Type:     sig,
				Pos:      x.Name.Pos(),
				Exported: x.Export,
			}
			c.declare(module, o)
			c.info.Defs[x.Name] = o

		case *ast.ConstDecl:
			o := &Object{
				Kind:     Const,
				Name:     x.Name.Name,
				Type:     c.resolveType(fileScope, x.Type),
				Pos:      x.Name.Pos(),
				Exported: x.Export,
				Mutable:  false,
			}
			c.declare(module, o)
			c.info.Defs[x.Name] = o

		case *ast.VarDecl:
			var t types.Type = types.Invalid
			if x.Type != nil {
				t = c.resolveType(fileScope, x.Type)
			}
			o := &Object{
				Kind:    Var,
				Name:    x.Name.Name,
				Type:    t,
				Pos:     x.Name.Pos(),
				Mutable: true, // R6: bindings are mutable by default
			}
			c.declare(module, o)
			c.info.Defs[x.Name] = o
		}
	}
}

// signature resolves a function's parameter and result types.
func (c *checker) signature(scope *Scope, d *ast.FuncDecl) *types.Func {
	f := &types.Func{}
	for _, p := range d.Params {
		f.Params = append(f.Params, c.resolveType(scope, p.Type))
	}
	for _, r := range d.Results {
		f.Results = append(f.Results, c.resolveType(scope, r))
	}
	return f
}

func (c *checker) litSignature(scope *Scope, d *ast.FuncLit) *types.Func {
	f := &types.Func{}
	for _, p := range d.Params {
		f.Params = append(f.Params, c.resolveType(scope, p.Type))
	}
	for _, r := range d.Results {
		f.Results = append(f.Results, c.resolveType(scope, r))
	}
	return f
}

// namedFor returns the *types.Named allocated for a declaration's name.
func (c *checker) namedFor(id *ast.Ident) *types.Named {
	o := c.info.Defs[id]
	if o == nil {
		return nil
	}
	named, _ := o.Type.(*types.Named)
	return named
}

// ---------------------------------------------------------------------------
// Bodies

func (c *checker) checkBodies(fileScope *Scope, file *ast.File) {
	// Module-level initializers first. A `const` or a `var` with no annotation
	// only learns its type here, and a function body checked before that would
	// see it as unknown.
	for _, d := range file.Decls {
		switch x := d.(type) {
		case *ast.ConstDecl:
			c.constDeclBody(fileScope, x)
		case *ast.VarDecl:
			c.varDeclBody(fileScope, x, c.info.Defs[x.Name])
		}
	}

	for _, d := range file.Decls {
		x, isFunc := d.(*ast.FuncDecl)
		if !isFunc {
			continue
		}
		sig := c.sigs[x]
		var params, results []types.Type
		if sig != nil {
			params, results = sig.Params, sig.Results
		}
		c.funcBody(fileScope, x.Recv, c.recvs[x], x.Params, params, results, x.Body)
	}
}

// funcBody checks a function, method, gate, or function literal.
//
// paramTypes are the types already resolved from the signature. Resolving them
// a second time here would report every bad annotation twice, once from the
// signature pass and once from the body pass.
func (c *checker) funcBody(outer *Scope, recv *ast.Param, recvType types.Type, params []*ast.Param, paramTypes []types.Type, results []types.Type, body *ast.BlockStmt) {
	// A function literal nests inside its enclosing function, so the result
	// list is saved and restored rather than assigned.
	savedResults, savedLoop := c.curResults, c.loopDepth
	c.curResults, c.loopDepth = results, 0
	defer func() { c.curResults, c.loopDepth = savedResults, savedLoop }()

	scope := NewScope(outer, FuncScope)
	if recv != nil {
		c.declareParam(scope, recv, recvType)
	}
	for i, p := range params {
		var t types.Type = types.Invalid
		if i < len(paramTypes) {
			t = paramTypes[i]
		}
		c.declareParam(scope, p, t)
	}
	if body != nil {
		c.block(scope, body)
	}
}

func (c *checker) declareParam(scope *Scope, p *ast.Param, t types.Type) {
	o := &Object{
		Kind: Var,
		Name: p.Name.Name,
		Type: t,
		Pos:  p.Name.Pos(),
		// A receiver or parameter marked `mut` is a mutable reference;
		// otherwise it is a copy the callee may not write through (R6).
		Mutable: p.Mut,
	}
	c.declare(scope, o)
	c.info.Defs[p.Name] = o
}

// block checks a statement list in a fresh block scope.
func (c *checker) block(outer *Scope, b *ast.BlockStmt) {
	scope := NewScope(outer, BlockScope)
	for _, s := range b.Stmts {
		c.stmt(scope, s)
	}
}

func (c *checker) stmt(scope *Scope, s ast.Stmt) {
	switch x := s.(type) {
	case nil, *ast.BadStmt:
		return

	case *ast.BlockStmt:
		c.block(scope, x)

	case *ast.ExprStmt:
		c.exprStatement(scope, x.X)

	case *ast.VarDecl:
		// The initializer is checked before the name is bound, so `var x := x`
		// refers to an outer x rather than to itself.
		t := c.varType(scope, x)
		c.declareLocal(scope, x.Name, t)

	case *ast.AssignStmt:
		c.assign(scope, x)

	case *ast.IncDecStmt:
		c.expr(scope, x.X)

	case *ast.IfStmt:
		c.condition(scope, x.Cond, "if")
		// Rule N6: `if x != nil` narrows x to T in the then branch, and
		// `if x == nil` narrows it in the else branch.
		thenScope, elseScope := c.narrowScopes(scope, x.Cond)
		c.block(thenScope, x.Then)
		if x.Else != nil {
			c.stmt(elseScope, x.Else)
		}

	case *ast.WhileStmt:
		c.condition(scope, x.Cond, "while")
		c.loopBody(scope, x.Body)

	case *ast.RangeStmt:
		c.expr(scope, x.X)
		// The loop variables are scoped to the loop.
		inner := NewScope(scope, BlockScope)
		for _, n := range x.Names {
			c.declareLocal(inner, n, types.Invalid)
		}
		c.loopBody(inner, x.Body)

	case *ast.ForStmt:
		// "The init clause's bindings are scoped to the loop" (chapter 05).
		inner := NewScope(scope, BlockScope)
		if x.Init != nil {
			c.stmt(inner, x.Init)
		}
		if x.Cond != nil {
			c.condition(inner, x.Cond, "for")
		}
		if x.Post != nil {
			c.stmt(inner, x.Post)
		}
		c.loopBody(inner, x.Body)

	case *ast.MatchStmt:
		c.matchStmt(scope, x)

	case *ast.ReturnStmt:
		c.returnStmt(scope, x)

	case *ast.BranchStmt:
		// "Legal only inside a loop body, applying to the innermost enclosing
		// loop" (chapter 05 §break and continue). There are no labels in v1.
		if c.loopDepth == 0 {
			c.errorf(x.Keyword, "%s outside a loop", token.Kind(x.Tok))
		}

	case *ast.SpawnStmt:
		c.exprStatement(scope, x.Call)

	case *ast.SendStmt:
		c.expr(scope, x.Chan)
		c.expr(scope, x.Value)

	case *ast.SelectStmt:
		for _, cc := range x.Cases {
			// Each case gets its own scope: `case v := <-ch:` binds v for that
			// case only.
			inner := NewScope(scope, BlockScope)
			if cc.Comm != nil {
				c.stmt(inner, cc.Comm)
			}
			for _, s := range cc.Body {
				c.stmt(inner, s)
			}
		}

	default:
		c.errorf(s.Pos(), "internal: unchecked statement %T", s)
	}
}

// returnStmt checks a return against the enclosing function's declared results.
//
// Whether every path returns is a separate question, answered in M9. This is
// only about the values a return that does happen produces.
func (c *checker) returnStmt(scope *Scope, x *ast.ReturnStmt) {
	want := c.curResults

	if len(x.Results) == 0 {
		if len(want) > 0 {
			c.hint(x.Keyword,
				"bare return in a function declared to return "+plural(len(want), "value"),
				"return "+describeResults(want))
		}
		return
	}

	if len(want) == 0 {
		for _, r := range x.Results {
			c.expr(scope, r)
		}
		c.errorf(x.Results[0].Pos(), "this function declares no results, so return takes none")
		return
	}

	var got []types.Type
	if len(x.Results) == 1 && len(want) > 1 {
		// `return divmod(a, b)` — a multi-valued call is legal as the whole
		// return (chapter 04 §Calls).
		values, known := c.multiExpr(scope, x.Results[0])
		got = values
		if !known {
			return
		}
	} else {
		for i, r := range x.Results {
			var w types.Type
			if i < len(want) {
				w = want[i]
			}
			got = append(got, c.exprWant(scope, r, w))
		}
	}

	if len(got) != len(want) {
		c.errorf(x.Keyword, "return has %s, want %s",
			plural(len(got), "value"), plural(len(want), "value"))
		return
	}
	for i, g := range got {
		pos := x.Keyword
		if i < len(x.Results) {
			pos = x.Results[i].Pos()
		}
		c.assignableTo(pos, g, want[i], "the return")
	}
}

// describeResults renders a result list for a hint.
func describeResults(ts []types.Type) string {
	out := ""
	for i, t := range ts {
		if i > 0 {
			out += ", "
		}
		out += "a " + t.String()
	}
	return out
}

// exprStatement checks an expression standing alone as a statement, where any
// number of results is fine — including none, which is how a void-in-effect
// function is called.
//
// The parser already rejects everything but a call here (chapter 05
// §Statement-level expressions). Whether an unused *error* result is legal is
// chapter 06's rule and lands in M8.
func (c *checker) exprStatement(scope *Scope, e ast.Expr) {
	if call, ok := e.(*ast.CallExpr); ok {
		rs := c.call(scope, call)
		c.info.Types[e] = firstOrInvalid(rs)
		return
	}
	c.expr(scope, e)
}

// condition checks a control-flow condition.
//
// "The condition MUST be bool. There is no truthiness: `if x` where `x: int` is
// a type error." (chapter 05 §if)
func (c *checker) condition(scope *Scope, e ast.Expr, keyword string) {
	t := c.expr(scope, e)
	if types.IsInvalid(t) || types.Identical(t, types.Bool) {
		return
	}
	c.hint(e.Pos(),
		"the "+keyword+" condition is "+t.String()+", want bool",
		"there is no truthiness; compare explicitly, as in x != 0")
}

func (c *checker) loopBody(scope *Scope, b *ast.BlockStmt) {
	c.loopDepth++
	c.block(scope, b)
	c.loopDepth--
}

// assign handles `=`, the compound forms, and `:=`.
func (c *checker) assign(scope *Scope, s *ast.AssignStmt) {
	values := c.rhsValues(scope, s)

	if s.Tok != token.DEFINE {
		// `=` and `op=` assign to something that already exists.
		for i, l := range s.Lhs {
			if id, ok := l.(*ast.Ident); ok && id.Name == "_" {
				// `_ = f()` is the deliberate discard of chapter 06.
				continue
			}
			c.assignTarget(scope, l, values[i], s)
		}
		return
	}

	// `:=` declares. Every target must be a plain name, and redeclaring one
	// already bound in this scope is an error — Ymir is stricter than Go here,
	// which permits `x, y := ...` when only y is new (chapter 03 §Variables).
	for i, l := range s.Lhs {
		id, ok := l.(*ast.Ident)
		if !ok {
			c.hint(l.Pos(),
				":= declares a name, and this is not one",
				"use = to assign to an existing location")
			continue
		}
		c.define(scope, id, values[i])
	}
}

// rhsValues evaluates the right side of an assignment and pads or trims the
// result to one value per target, so callers may index it by position.
//
// A single multi-valued call on the right is the destructuring form:
// `q, r := divmod(17, 5)`.
func (c *checker) rhsValues(scope *Scope, s *ast.AssignStmt) []types.Type {
	var values []types.Type

	if len(s.Rhs) == 1 && len(s.Lhs) > 1 {
		var known bool
		values, known = c.multiExpr(scope, s.Rhs[0])
		if known && len(values) != len(s.Lhs) {
			c.errorf(s.TokPos, "assignment mismatch: %s on the left, %s on the right",
				plural(len(s.Lhs), "name"), plural(len(values), "value"))
		}
	} else {
		for i, r := range s.Rhs {
			// An `=` to a known location supplies the expected type, which is
			// what lets `xs = []` and `m = {}` be written at all.
			var want types.Type
			if s.Tok == token.ASSIGN && i < len(s.Lhs) {
				want = c.targetType(scope, s.Lhs[i])
			}
			values = append(values, c.exprWant(scope, r, want))
		}
		if len(s.Rhs) != len(s.Lhs) {
			c.errorf(s.TokPos, "assignment mismatch: %s on the left, %s on the right",
				plural(len(s.Lhs), "name"), plural(len(s.Rhs), "value"))
		}
	}

	for len(values) < len(s.Lhs) {
		values = append(values, types.Invalid)
	}
	return values
}

// rootOf walks a selector chain down to the binding it starts from.
func rootOf(e ast.Expr) ast.Expr {
	for {
		sel, ok := e.(*ast.SelectorExpr)
		if !ok {
			return e
		}
		e = sel.X
	}
}

// targetType peeks at an assignment target's type without reporting, so the
// right-hand side can be typed against it.
func (c *checker) targetType(scope *Scope, l ast.Expr) types.Type {
	id, ok := l.(*ast.Ident)
	if !ok {
		return nil
	}
	o, _ := scope.LookupParent(id.Name)
	if o == nil {
		return nil
	}
	return o.Type
}

// assignTarget checks the left side of an `=`, which must be assignable to.
func (c *checker) assignTarget(scope *Scope, l ast.Expr, value types.Type, s *ast.AssignStmt) {
	target := c.expr(scope, l)

	if id, ok := l.(*ast.Ident); ok {
		// Assigning to a narrowed binding ends the narrowing (rule N6), and the
		// value is then checked against the declared ?T rather than against the
		// narrowed T.
		if orig := c.dropNarrowing(scope, id.Name); orig != nil {
			target = orig.Type
			c.info.Uses[id] = orig
		}
	}

	if s.Tok == token.ASSIGN {
		c.assignableTo(l.Pos(), value, target, "an assignment")
	}

	if sel, ok := l.(*ast.SelectorExpr); ok {
		// "Assignment to an index or field is legal where the base is
		// mutable" (chapter 04). A struct has value semantics, so writing a
		// field through a non-mut parameter writes to a copy. array and map
		// have reference semantics, so indexing through one is fine.
		c.requireMutable(rootOf(sel), "assign to "+sel.Sel.Name)
	}

	if id, ok := l.(*ast.Ident); ok {
		if o := c.info.Uses[id]; o != nil {
			switch {
			case o.Kind == Const:
				c.errorf(id.Pos(), "cannot assign to constant %s", id.Name)
			case o.Kind != Var:
				c.errorf(id.Pos(), "cannot assign to %s %s", o.Kind, id.Name)
			case !o.Mutable:
				c.hint(id.Pos(),
					"cannot assign to "+id.Name+", which is not mutable",
					"mark the parameter `mut` to take a mutable reference")
			}
		}
	}
}

func (c *checker) declareLocal(scope *Scope, id *ast.Ident, t types.Type) {
	if id.Name == "_" {
		return // the blank identifier is never bound
	}
	o := &Object{
		Kind:    Var,
		Name:    id.Name,
		Type:    t,
		Pos:     id.Pos(),
		Mutable: true,
	}
	c.declare(scope, o)
	c.info.Defs[id] = o
}

// matchStmt resolves a match. Exhaustiveness is M7; this binds the patterns.
func (c *checker) matchStmt(scope *Scope, m *ast.MatchStmt) {
	c.expr(scope, m.X)
	for _, arm := range m.Arms {
		// "Bindings introduced by a pattern are scoped to that arm."
		inner := NewScope(scope, BlockScope)
		for _, b := range arm.Pattern.Binds {
			if b != nil {
				c.declareLocal(inner, b, types.Invalid)
			}
		}
		c.stmt(inner, arm.Body)
	}
}
