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
