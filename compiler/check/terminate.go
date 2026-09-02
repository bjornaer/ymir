package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
)

// Definite return. Chapter 05 §Returning on every path.
//
// "A function with a declared return type MUST return on every path. Falling off
// the end is a compile error."
//
// Legacy returned "the last evaluated value" from a function that fell off the
// end, which made a function's result depend on the shape of its final
// statement. This is the rule that forecloses that.
//
// The analysis is deliberately syntactic — it proves a statement always
// transfers control, and never tries to prove a condition is true. A `for` and a
// `while` with any condition other than the literal `true` do not terminate,
// because the checker does not prove they run at all.

// terminates reports whether a statement always transfers control away, so
// nothing after it can be reached.
func terminates(s ast.Stmt) bool {
	switch x := s.(type) {
	case *ast.ReturnStmt:
		return true

	case *ast.ExprStmt:
		// A call to panic(...) terminates. It is a builtin, so the name is
		// enough — a local binding named panic would shadow it, and the
		// checker reports that separately.
		return isPanicCall(x.X)

	case *ast.BlockStmt:
		return blockTerminates(x)

	case *ast.IfStmt:
		// "An if that has an else, where both the then block and the else
		// branch terminate — an if with no else never terminates, however its
		// branch ends."
		return x.Else != nil && blockTerminates(x.Then) && terminates(x.Else)

	case *ast.MatchStmt:
		// "A match in which every arm's body terminates. Exhaustiveness
		// already guarantees the arms cover the scrutinee, so no fall-through
		// case remains."
		if len(x.Arms) == 0 {
			return false
		}
		for _, arm := range x.Arms {
			if !terminates(arm.Body) {
				return false
			}
		}
		return true

	case *ast.WhileStmt:
		// "A while true { ... } whose body contains no break that leaves it."
		lit, ok := x.Cond.(*ast.BoolLit)
		return ok && lit.Value && !hasEscapingBreak(x.Body)
	}

	return false
}

func blockTerminates(b *ast.BlockStmt) bool {
	if b == nil || len(b.Stmts) == 0 {
		return false
	}
	return terminates(b.Stmts[len(b.Stmts)-1])
}

func isPanicCall(e ast.Expr) bool {
	call, ok := e.(*ast.CallExpr)
	if !ok {
		return false
	}
	id, ok := call.Fun.(*ast.Ident)
	return ok && id.Name == "panic"
}

// hasEscapingBreak reports whether a loop body contains a `break` that leaves
// *this* loop. A break inside a nested loop belongs to that one.
func hasEscapingBreak(s ast.Stmt) bool {
	switch x := s.(type) {
	case *ast.BranchStmt:
		return x.Tok == token.BREAK

	case *ast.BlockStmt:
		for _, st := range x.Stmts {
			if hasEscapingBreak(st) {
				return true
			}
		}

	case *ast.IfStmt:
		if hasEscapingBreak(x.Then) {
			return true
		}
		if x.Else != nil {
			return hasEscapingBreak(x.Else)
		}

	case *ast.MatchStmt:
		for _, arm := range x.Arms {
			if hasEscapingBreak(arm.Body) {
				return true
			}
		}

	case *ast.SelectStmt:
		for _, cc := range x.Cases {
			for _, st := range cc.Body {
				if hasEscapingBreak(st) {
					return true
				}
			}
		}

		// A nested loop swallows its own break, so WhileStmt, ForStmt and
		// RangeStmt are deliberately absent from this switch.
	}
	return false
}

// checkReturns reports a function that can fall off its end.
func (c *checker) checkReturns(name *ast.Ident, results []ast.Type, body *ast.BlockStmt) {
	if len(results) == 0 || body == nil {
		return
	}
	if blockTerminates(body) {
		return
	}
	pos := body.Rbrace
	c.hint(pos,
		"missing return at the end of "+name.Name,
		"every path must return; an `if` with no `else` does not count as returning")
}

// ---------------------------------------------------------------------------
// main

// checkMain enforces chapter 03 §main: "main takes no parameters. Exactly one
// module in a program declares it. main is invoked automatically; it MUST NOT
// be called explicitly."
//
// Resolved question R9 gives it exactly two forms — `func main()` and
// `func main() -> ?error` — and nothing else. The error form exists so `try` is
// usable in the entry point, which is the one function that calls everything
// else; a non-nil result writes str(err) to stderr and exits 1.
//
// The "exactly one module" half needs a whole-program view and arrives with the
// module loader in Phase 6.
func (c *checker) checkMain(d *ast.FuncDecl) {
	if d.Name.Name != "main" || d.Recv != nil {
		return
	}
	if len(d.Params) > 0 {
		c.hint(d.Params[0].Pos(),
			"main takes no parameters",
			"it is invoked by the runtime, which has nothing to pass")
	}
	if d.Export {
		c.errorf(d.Name.Pos(), "main cannot be exported")
	}

	switch len(d.Results) {
	case 0:
		return
	case 1:
		if sig := c.sigs[d]; sig != nil && errorSetOf(sig.Results) != nil {
			return
		}
		c.hint(d.Results[0].Pos(),
			"main returns either nothing or an error set",
			"write `func main()` or `func main() -> ?error`")
	default:
		c.hint(d.Results[0].Pos(),
			"main returns either nothing or an error set, not "+plural(len(d.Results), "value"),
			"write `func main()` or `func main() -> ?error`")
	}
}
