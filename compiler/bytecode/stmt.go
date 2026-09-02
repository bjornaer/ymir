package bytecode

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
)

// Statements.
//
// M3 compiles only what the end-to-end slice needs: a block, an expression
// statement, and a return. Everything else reports itself as unimplemented with
// a position, rather than compiling to nothing — which is how legacy's `main`
// became a silent no-op.

func (c *compiler) block(b *ast.BlockStmt) {
	c.beginScope()
	for _, s := range b.Stmts {
		c.stmt(s)
	}
	c.endScope(b.Rbrace)
}

func (c *compiler) stmt(s ast.Stmt) {
	switch x := s.(type) {
	case nil:
		return

	case *ast.BlockStmt:
		c.block(x)

	case *ast.ExprStmt:
		c.exprStatement(x.X)

	case *ast.ReturnStmt:
		c.returnStmt(x)

	case *ast.VarDecl:
		c.varDecl(x)

	case *ast.AssignStmt:
		c.assign(x)

	default:
		c.unsupported(s.Pos(), describeStmt(s))
	}
}

// exprStatement compiles a call whose results nobody wants, popping whatever it
// leaves. The checker has already rejected a bare non-call expression here
// (chapter 05 §Statement-level expressions) and an unhandled error result
// (chapter 06), so anything reaching this point is a deliberate discard.
func (c *compiler) exprStatement(e ast.Expr) {
	call, ok := e.(*ast.CallExpr)
	if !ok {
		c.unsupported(e.Pos(), "this statement")
		return
	}

	results := c.call(call)
	for i := 0; i < results; i++ {
		c.emit(OpPop, 0, call.Rparen)
	}
}

// varDecl compiles `var x: T = e`, `var x := e`, and `var x: T`.
//
// A local needs no store instruction: its initializer is already on top of the
// stack, and that slot *is* the local. The invariant this rests on is that after
// every statement the stack holds exactly the frame's live locals, which
// endScope maintains by popping.
func (c *compiler) varDecl(x *ast.VarDecl) {
	if x.Value != nil {
		c.expr(x.Value)
	} else {
		// The checker has already refused a type with no zero value
		// (chapter 02 §Zero values), so nil is the zero of whatever this is
		// until Phase 4 gives the other types theirs.
		c.emit(OpNil, 0, x.Name.Pos())
	}
	c.declareLocal(x.Name)
}

// assign compiles `=`, `op=`, and `:=`.
func (c *compiler) assign(x *ast.AssignStmt) {
	if x.Tok == token.DEFINE {
		// Same as a var: the values are on the stack and become the slots.
		if len(x.Lhs) != len(x.Rhs) {
			c.unsupported(x.TokPos, "destructuring a multi-valued call")
			return
		}
		for i := range x.Lhs {
			c.expr(x.Rhs[i])
		}
		for _, l := range x.Lhs {
			id, ok := l.(*ast.Ident)
			if !ok {
				c.unsupported(l.Pos(), "this declaration target")
				return
			}
			c.declareLocal(id)
		}
		return
	}

	if x.Tok != token.ASSIGN {
		c.unsupported(x.TokPos, "compound assignment")
		return
	}
	if len(x.Lhs) != 1 || len(x.Rhs) != 1 {
		c.unsupported(x.TokPos, "multiple assignment")
		return
	}

	id, ok := x.Lhs[0].(*ast.Ident)
	if !ok {
		c.unsupported(x.Lhs[0].Pos(), "assigning to this target")
		return
	}
	c.expr(x.Rhs[0])

	if id.Name == "_" {
		// A deliberate discard (chapter 06). Evaluate for the effect, drop it.
		c.emit(OpPop, 0, x.TokPos)
		return
	}
	if slot, ok := c.resolveLocal(id); ok {
		c.emit(OpSetLocal, slot, x.TokPos)
		return
	}
	if slot, ok := c.globals[id.Name]; ok {
		c.emit(OpSetGlobal, slot, x.TokPos)
		return
	}
	c.errs.Addf(id.Pos(), "internal: %s resolved by the checker but not by the compiler", id.Name)
}

func (c *compiler) returnStmt(x *ast.ReturnStmt) {
	for _, r := range x.Results {
		c.expr(r)
	}
	c.emit(OpReturn, int32(len(x.Results)), x.Keyword)
}

// describeStmt names a statement for the unimplemented diagnostic, so the
// message says what is missing rather than printing a Go type.
func describeStmt(s ast.Stmt) string {
	switch x := s.(type) {
	case *ast.VarDecl:
		return "a `var` declaration"
	case *ast.AssignStmt:
		if x.Tok == token.DEFINE {
			return "a `:=` declaration"
		}
		return "an assignment"
	case *ast.IncDecStmt:
		return "`++` and `--`"
	case *ast.IfStmt:
		return "`if`"
	case *ast.WhileStmt:
		return "`while`"
	case *ast.ForStmt, *ast.RangeStmt:
		return "`for`"
	case *ast.MatchStmt:
		return "`match`"
	case *ast.BranchStmt:
		return "`break` and `continue`"
	case *ast.SpawnStmt:
		return "`spawn`"
	case *ast.SendStmt:
		return "a channel send"
	case *ast.SelectStmt:
		return "`select`"
	}
	return "this statement"
}
