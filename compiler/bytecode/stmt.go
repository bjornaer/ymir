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

	case *ast.IfStmt:
		c.ifStmt(x)

	case *ast.WhileStmt:
		c.whileStmt(x)

	case *ast.ForStmt:
		c.forStmt(x)

	case *ast.BranchStmt:
		c.branchStmt(x)

	case *ast.IncDecStmt:
		c.incDec(x)

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

// ifStmt compiles a conditional.
//
//	<cond>
//	JumpIfFalse -> else
//	<then>
//	Jump -> end
//	else: <else>
//	end:
func (c *compiler) ifStmt(x *ast.IfStmt) {
	c.expr(x.Cond)
	toElse := c.emit(OpJumpIfFalse, -1, x.Keyword)

	c.block(x.Then)

	if x.Else == nil {
		c.fn.Chunk.Patch(toElse, int32(c.fn.Chunk.Len()))
		return
	}

	toEnd := c.emit(OpJump, -1, x.Keyword)
	c.fn.Chunk.Patch(toElse, int32(c.fn.Chunk.Len()))
	c.stmt(x.Else)
	c.fn.Chunk.Patch(toEnd, int32(c.fn.Chunk.Len()))
}

// loop holds the patch targets a `break` and a `continue` need.
type loop struct {
	start     int   // where `continue` jumps to
	breaks    []int // jumps to patch to the loop's end
	continues []int // jumps to patch to the post clause, for a C-style for
}

func (c *compiler) whileStmt(x *ast.WhileStmt) {
	start := c.fn.Chunk.Len()
	c.expr(x.Cond)
	toEnd := c.emit(OpJumpIfFalse, -1, x.Keyword)

	c.loops = append(c.loops, &loop{start: start})
	c.block(x.Body)
	l := c.loops[len(c.loops)-1]
	c.loops = c.loops[:len(c.loops)-1]

	// `continue` on a while goes back to the condition.
	for _, pc := range l.continues {
		c.fn.Chunk.Patch(pc, int32(start))
	}
	c.emit(OpJump, int32(start), x.Keyword)

	end := int32(c.fn.Chunk.Len())
	c.fn.Chunk.Patch(toEnd, end)
	for _, pc := range l.breaks {
		c.fn.Chunk.Patch(pc, end)
	}
}

// forStmt compiles the C-style form. The range form needs arrays and arrives in
// Phase 4.
func (c *compiler) forStmt(x *ast.ForStmt) {
	// "The init clause's bindings are scoped to the loop" (chapter 05 §for), so
	// the whole statement is one scope.
	c.beginScope()
	if x.Init != nil {
		c.stmt(x.Init)
	}

	start := c.fn.Chunk.Len()
	toEnd := -1
	if x.Cond != nil {
		c.expr(x.Cond)
		toEnd = c.emit(OpJumpIfFalse, -1, x.Keyword)
	}

	c.loops = append(c.loops, &loop{start: start})
	c.block(x.Body)
	l := c.loops[len(c.loops)-1]
	c.loops = c.loops[:len(c.loops)-1]

	// `continue` skips the rest of the body but still runs the post clause.
	post := int32(c.fn.Chunk.Len())
	for _, pc := range l.continues {
		c.fn.Chunk.Patch(pc, post)
	}
	if x.Post != nil {
		c.stmt(x.Post)
	}
	c.emit(OpJump, int32(start), x.Keyword)

	end := int32(c.fn.Chunk.Len())
	if toEnd >= 0 {
		c.fn.Chunk.Patch(toEnd, end)
	}
	for _, pc := range l.breaks {
		c.fn.Chunk.Patch(pc, end)
	}
	c.endScope(x.Body.Rbrace)
}

func (c *compiler) branchStmt(x *ast.BranchStmt) {
	if len(c.loops) == 0 {
		// The checker already rejected this (chapter 05 §break and continue),
		// so reaching here means the two disagree.
		c.errs.Addf(x.Keyword, "internal: %s outside a loop reached the compiler", x.Tok)
		return
	}
	l := c.loops[len(c.loops)-1]
	pc := c.emit(OpJump, -1, x.Keyword)
	if x.Tok == token.BREAK {
		l.breaks = append(l.breaks, pc)
	} else {
		l.continues = append(l.continues, pc)
	}
}

// incDec compiles `x++` and `x--`, which chapter 05 defines as `x += 1`.
func (c *compiler) incDec(x *ast.IncDecStmt) {
	id, ok := x.X.(*ast.Ident)
	if !ok {
		c.unsupported(x.X.Pos(), "`++` on this target")
		return
	}

	c.expr(x.X)
	c.constant(Const{Kind: ConstInt, I: 1}, x.TokPos)
	if x.Tok == token.INC {
		c.emit(OpAddInt, 0, x.TokPos)
	} else {
		c.emit(OpSubInt, 0, x.TokPos)
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
