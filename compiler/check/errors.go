package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/types"
)

// Error sets, `try`, and unhandled errors. Chapter 06.
//
// The design this enforces: "A function's error set is the union of the sets of
// everything it calls, and returning a callee's error directly typechecks
// without wrapping." That composition is what subset assignability buys, and
// `try` is where it has to be checked rather than merely permitted.

// errorSetOf returns the error set occupying a result list's error position, or
// nil when the list has none.
//
// "The error position is the final component of a function's result type. Its
// type is written ?E for an error set E" (chapter 06 §The error position). A
// function returning only `?IOError` has one; a function returning `?int` does
// not, because int is not an error set.
func errorSetOf(results []types.Type) types.Type {
	if len(results) == 0 {
		return nil
	}
	n, ok := results[len(results)-1].(*types.Nullable)
	if !ok || !types.IsErrorSet(n.Elem) {
		return nil
	}
	return n.Elem
}

// tryResults types `try e` and enforces the rules of chapter 06 §Rules.
//
// The result is the callee's results with the error position removed: one value
// in the common case, several in the multi-valued one, none when the callee
// returns only an error.
func (c *checker) tryResults(scope *Scope, x *ast.TryExpr) []types.Type {
	call, ok := x.Call.(*ast.CallExpr)
	if !ok {
		// The parser already requires a call, so this is defensive.
		c.expr(scope, x.Call)
		return []types.Type{types.Invalid}
	}

	rs := c.call(scope, call)
	callee := errorSetOf(rs)

	if callee == nil {
		// "try on a call with no error position is a compile error."
		if !hasInvalid(rs) {
			c.hint(x.Keyword,
				"try needs a call that can fail, and "+calleeName(call.Fun)+" has no error position",
				"a fallible function's last result is ?E for an error set E")
		}
		return rs
	}

	c.checkTryEnclosing(x, callee)
	return rs[:len(rs)-1]
}

// checkTryEnclosing checks `try` against the function it would return from.
func (c *checker) checkTryEnclosing(x *ast.TryExpr, callee types.Type) {
	enclosing := errorSetOf(c.curResults)

	if enclosing == nil {
		// "The enclosing function MUST have an error position."
		c.hint(x.Keyword,
			"try returns early with an error, and this function has no error position to return it in",
			"give it one: -> ("+resultsBefore(c.curResults)+"?"+callee.String()+")")
		return
	}

	// "The callee's error set MUST be a subset of the enclosing function's.
	// This is checked statically; try never widens a set implicitly beyond what
	// is declared."
	if !types.Subset(callee, enclosing) {
		c.hint(x.Keyword,
			"try propagates "+callee.String()+", which is not a subset of this function's "+enclosing.String(),
			"widen the declared set to ?("+types.NewUnion(callee, enclosing).String()+"), or handle the error here")
		return
	}

	// "Every non-error result of the enclosing function MUST have a zero value.
	// try in a function returning an enum or a linear type is a compile error,
	// since there is nothing to return on the error path."
	for _, r := range c.curResults[:len(c.curResults)-1] {
		if types.IsInvalid(r) || types.HasZeroValue(r) {
			continue
		}
		c.hint(x.Keyword,
			"try returns the zero value of every other result, and "+r.String()+" has none",
			"return the error explicitly instead, or make that result ?"+r.String())
		return
	}
}

// resultsBefore renders a result list without its last component, for the hint
// that suggests adding an error position.
func resultsBefore(results []types.Type) string {
	out := ""
	for _, r := range results {
		out += r.String() + ", "
	}
	return out
}

func hasInvalid(ts []types.Type) bool {
	for _, t := range ts {
		if types.IsInvalid(t) {
			return true
		}
	}
	return false
}

// ---------------------------------------------------------------------------
// Unhandled errors

// checkUnhandled reports a fallible call whose error result nobody bound.
//
// "If a call's result type has an error position, the caller MUST bind it.
// Discarding requires the blank identifier explicitly." (chapter 06 §Unhandled
// errors are a compile error)
//
//	result, err := divide(10, 2)     legal
//	divide(10, 2)                    ERROR: unhandled error result
//	_, _ = divide(10, 2)             legal — deliberate, visible, greppable
//	data := try readFile(path)       legal — propagates
func (c *checker) checkUnhandled(e ast.Expr, results []types.Type) {
	call, ok := e.(*ast.CallExpr)
	if !ok || errorSetOf(results) == nil {
		return
	}
	c.hint(call.Pos(),
		"unhandled error result from "+calleeName(call.Fun),
		"bind it with `_, err := ...`, propagate it with `try`, or discard it deliberately with `_, _ = ...`")
}

// markRead records that a binding's value was read, for the unused-error check.
func (c *checker) markRead(o *Object) {
	if orig := c.narrowedFrom[o]; orig != nil {
		o = orig
	}
	c.read[o] = true
}

// trackErrorBinding remembers a binding whose type is an error position, so a
// never-read one can be reported when checking finishes.
//
// "Binding an error and never reading it is also a compile error (it is an
// unused binding). An error must be checked, propagated, or explicitly
// discarded."
//
// Scoped to error bindings deliberately. Chapter 06 words it as though a general
// unused-binding rule existed, but no chapter states one, and inventing it here
// would reject programs the spec permits.
func (c *checker) trackErrorBinding(o *Object) {
	if o == nil || o.Kind != Var {
		return
	}
	if errorSetOf([]types.Type{o.Type}) == nil {
		return
	}
	c.errBindings = append(c.errBindings, o)
}

// reportUnreadErrors runs once, after every body has been checked.
func (c *checker) reportUnreadErrors() {
	for _, o := range c.errBindings {
		if c.read[o] {
			continue
		}
		c.hint(o.Pos,
			o.Name+" holds an error that is never read",
			"check it, propagate it with `try`, or discard it with `_` instead of naming it")
	}
}
