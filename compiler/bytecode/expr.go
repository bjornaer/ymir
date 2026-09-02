package bytecode

import (
	"strconv"
	"strings"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
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
