package bytecode

import (
	"strconv"
	"strings"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Expressions.
//
// M3 compiles literals and calls to `print` — the thinnest slice that gets a
// program from source to stdout. Arithmetic is M4, control flow M5, user
// functions and variables M6.

func (c *compiler) expr(e ast.Expr) {
	switch x := e.(type) {
	case nil:
		return

	case *ast.ParenExpr:
		c.expr(x.X)

	case *ast.BasicLit:
		c.basicLit(x)

	case *ast.BoolLit:
		if x.Value {
			c.emit(OpTrue, 0, x.Pos())
		} else {
			c.emit(OpFalse, 0, x.Pos())
		}

	case *ast.NilLit:
		c.emit(OpNil, 0, x.Pos())

	case *ast.Ident:
		c.ident(x)

	case *ast.UnaryExpr:
		c.unary(x)

	case *ast.BinaryExpr:
		c.binary(x)

	case *ast.CallExpr:
		// In expression position a call must leave exactly one value; the
		// checker has already rejected the multi-valued and void cases
		// (chapter 04 §Calls).
		c.call(x)

	default:
		c.unsupported(e.Pos(), describeExpr(e))
	}
}

func (c *compiler) basicLit(x *ast.BasicLit) {
	switch x.Kind {
	case token.INT:
		n, err := strconv.ParseInt(strings.ReplaceAll(x.Value, "_", ""), 0, 64)
		if err != nil {
			// The checker folds and rejects an out-of-range literal (R5), so
			// reaching here means the two disagree.
			c.errs.Addf(x.Pos(), "internal: integer literal %s does not fit an int64", x.Value)
			return
		}
		c.constant(Const{Kind: ConstInt, I: n}, x.Pos())

	case token.FLOAT:
		f, err := strconv.ParseFloat(strings.ReplaceAll(x.Value, "_", ""), 64)
		if err != nil {
			c.errs.Addf(x.Pos(), "internal: malformed float literal %s", x.Value)
			return
		}
		c.constant(Const{Kind: ConstFloat, F: f}, x.Pos())

	case token.STRING:
		// Already decoded by the lexer, escapes and all.
		c.constant(Const{Kind: ConstString, S: x.Value}, x.Pos())

	case token.IMAG:
		re, im, ok := parseComplex(x.Value)
		if !ok {
			c.errs.Addf(x.Pos(), "internal: malformed complex literal %s", x.Value)
			return
		}
		c.constant(Const{Kind: ConstComplex, F: re, G: im}, x.Pos())

	default:
		c.unsupported(x.Pos(), "this literal")
	}
}

// ident loads a variable.
func (c *compiler) ident(x *ast.Ident) {
	if slot, ok := c.resolveLocal(x); ok {
		c.emit(OpGetLocal, slot, x.Pos())
		return
	}
	if slot, ok := c.globals[x.Name]; ok {
		c.emit(OpGetGlobal, slot, x.Pos())
		return
	}
	// The checker resolved every name, so an unresolved one here means the
	// compiler and the checker disagree about scope.
	c.errs.Addf(x.Pos(), "internal: %s resolved by the checker but not by the compiler", x.Name)
}

func (c *compiler) unary(x *ast.UnaryExpr) {
	c.expr(x.X)
	t := c.typeOf(x.X)

	switch x.Op {
	case token.SUB:
		switch {
		case types.Identical(t, types.Int):
			c.emit(OpNegInt, 0, x.OpPos)
		case types.Identical(t, types.Float):
			c.emit(OpNegFloat, 0, x.OpPos)
		default:
			c.unsupported(x.OpPos, "negating a "+t.String())
		}
	case token.NOT:
		c.emit(OpNot, 0, x.OpPos)
	default:
		c.unsupported(x.OpPos, "the unary operator "+x.Op.String())
	}
}

// binary compiles an operator, choosing the opcode from the operand type the
// checker already proved.
//
// Both operands have identical types (chapter 04 §Operand typing), so one
// lookup decides the instruction.
func (c *compiler) binary(x *ast.BinaryExpr) {
	t := c.typeOf(x.X)
	if types.IsInvalid(t) {
		t = c.typeOf(x.Y)
	}

	// && and || evaluate their right operand only if the result is not already
	// determined. Chapter 04 §Short-circuit evaluation makes that normative,
	// not an optimization: the right operand may have effects.
	switch x.Op {
	case token.LAND, token.LOR:
		c.shortCircuit(x)
		return
	}

	c.expr(x.X)
	c.expr(x.Y)

	switch x.Op {
	// Equality is not typed: chapter 04 defines it on any unrestricted type,
	// so it dispatches on the value's kind at runtime.
	case token.EQL:
		c.emit(OpEq, 0, x.OpPos)
		return
	case token.NEQ:
		c.emit(OpNe, 0, x.OpPos)
		return
	}

	if op, ok := c.opFor(x.Op, t); ok {
		c.emit(op, 0, x.OpPos)
		return
	}
	c.unsupported(x.OpPos, "`"+x.Op.String()+"` on "+t.String())
}

// shortCircuit compiles `&&` and `||`, whose right operand is evaluated only
// when the left did not already decide the answer.
func (c *compiler) shortCircuit(x *ast.BinaryExpr) {
	c.expr(x.X)

	skip := OpJumpIfFalse // && : a false left decides it
	decided := OpFalse
	if x.Op == token.LOR {
		skip = OpJumpIfTrue // || : a true left decides it
		decided = OpTrue
	}

	toDecided := c.emit(skip, -1, x.OpPos)
	c.expr(x.Y)
	toEnd := c.emit(OpJump, -1, x.OpPos)

	c.fn.Chunk.Patch(toDecided, int32(c.fn.Chunk.Len()))
	c.emit(decided, 0, x.OpPos)
	c.fn.Chunk.Patch(toEnd, int32(c.fn.Chunk.Len()))
}

// opFor maps an operator and its operand type to an opcode.
func (c *compiler) opFor(op token.Kind, t types.Type) (Op, bool) {
	switch {
	case types.Identical(t, types.Int):
		switch op {
		case token.ADD:
			return OpAddInt, true
		case token.SUB:
			return OpSubInt, true
		case token.MUL:
			return OpMulInt, true
		case token.QUO:
			return OpDivInt, true
		case token.REM:
			return OpModInt, true
		case token.POW:
			return OpPowInt, true
		case token.LSS:
			return OpLtInt, true
		case token.LEQ:
			return OpLeInt, true
		case token.GTR:
			return OpGtInt, true
		case token.GEQ:
			return OpGeInt, true
		}

	case types.Identical(t, types.Float):
		switch op {
		case token.ADD:
			return OpAddFloat, true
		case token.SUB:
			return OpSubFloat, true
		case token.MUL:
			return OpMulFloat, true
		case token.QUO:
			return OpDivFloat, true
		case token.POW:
			return OpPowFloat, true
		case token.LSS:
			return OpLtFloat, true
		case token.LEQ:
			return OpLeFloat, true
		case token.GTR:
			return OpGtFloat, true
		case token.GEQ:
			return OpGeFloat, true
		}

	case types.Identical(t, types.String):
		switch op {
		case token.ADD:
			return OpConcat, true
		case token.LSS:
			return OpLtString, true
		case token.LEQ:
			return OpLeString, true
		case token.GTR:
			return OpGtString, true
		case token.GEQ:
			return OpGeString, true
		}
	}
	return OpNop, false
}

// call compiles a call and reports how many values it leaves on the stack.
func (c *compiler) call(x *ast.CallExpr) int {
	if id, ok := x.Fun.(*ast.Ident); ok {
		switch id.Name {
		case "print":
			for _, a := range x.Args {
				c.expr(a)
			}
			c.emit(OpPrint, int32(len(x.Args)), x.Fun.Pos())
			return 0

		case "panic":
			for _, a := range x.Args {
				c.expr(a)
			}
			c.emit(OpPanic, 0, x.Fun.Pos())
			return 0
		}

		if idx, ok := c.funcIdx[id.Name]; ok {
			for _, a := range x.Args {
				c.expr(a)
			}
			c.emit(OpCall, int32(idx), x.Fun.Pos())
			return c.program.Funcs[idx].Results
		}
	}

	c.unsupported(x.Fun.Pos(), "this call")
	return 0
}

// parseComplex reads the text of a complex literal, which the parser folded
// into one token (R7): "2.0i", "1.0+2.0i", "-1.0-3.0i".
//
// A deliberate second implementation of the checker's. The two are small, the
// alternative is exporting one from compiler/check purely for this, and a
// disagreement between them shows up immediately as a wrong constant.
func parseComplex(text string) (re, im float64, ok bool) {
	t := strings.ReplaceAll(text, "_", "")
	if !strings.HasSuffix(t, "i") {
		return 0, 0, false
	}
	t = t[:len(t)-1]

	split := -1
	for i := 1; i < len(t); i++ {
		if (t[i] == '+' || t[i] == '-') && t[i-1] != 'e' && t[i-1] != 'E' {
			split = i
		}
	}
	if split < 0 {
		f, err := strconv.ParseFloat(t, 64)
		if err != nil {
			return 0, 0, false
		}
		return 0, f, true
	}

	r, err := strconv.ParseFloat(t[:split], 64)
	if err != nil {
		return 0, 0, false
	}
	m, err := strconv.ParseFloat(t[split:], 64)
	if err != nil {
		return 0, 0, false
	}
	return r, m, true
}

// describeExpr names an expression for the unimplemented diagnostic.
func describeExpr(e ast.Expr) string {
	switch e.(type) {
	case *ast.Ident:
		return "a variable reference"
	case *ast.UnaryExpr:
		return "a unary operator"
	case *ast.BinaryExpr:
		return "a binary operator"
	case *ast.TryExpr:
		return "`try`"
	case *ast.IndexExpr:
		return "indexing"
	case *ast.SelectorExpr:
		return "field or method selection"
	case *ast.TupleIndexExpr:
		return "tuple indexing"
	case *ast.ArrayLit:
		return "an array literal"
	case *ast.MapLit:
		return "a map literal"
	case *ast.TupleLit:
		return "a tuple literal"
	case *ast.StructLit:
		return "a struct literal"
	case *ast.FuncLit:
		return "a function literal"
	}
	return "this expression"
}
