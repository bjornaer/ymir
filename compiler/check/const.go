package check

import (
	"math"
	"strconv"
	"strings"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
)

// Constant expressions.
//
// "An expression is constant if it is a literal, a `const`, or an operator
// applied to constant operands. Constant expressions are evaluated at compile
// time. Division by zero in a constant expression is a compile error, not a
// runtime panic." (chapter 04 §Constant expressions)
//
// Resolved question R5 adds the other half: overflow of an `int` constant
// expression is a compile error too, on the same grounds. At runtime the same
// overflow panics; the VM implements that in Phase 3.

type constKind int

const (
	constNone constKind = iota
	constInt
	constFloat
	constComplex
	constBool
	constString
)

// A constVal is the compile-time value of a constant expression. ok is false
// for anything that is not constant, which is the common case and not an error.
type constVal struct {
	kind constKind
	i    int64
	f    float64
	re   float64 // constComplex
	im   float64 // constComplex
	b    bool
	s    string
}

// constOf evaluates e if it is constant.
//
// It reports overflow and division by zero, because those are compile errors
// rather than reasons to give up on folding. Everything else that is simply not
// constant returns ok=false silently.
func (c *checker) constOf(e ast.Expr) (constVal, bool) {
	// Folding is memoized because it reports. Both the operator check and the
	// const declaration check ask for the value of the same initializer, and
	// without this an overflowing constant is reported twice.
	if r, done := c.folds[e]; done {
		return r.val, r.ok
	}
	v, ok := c.constOfUncached(e)
	if c.folds == nil {
		c.folds = map[ast.Expr]foldResult{}
	}
	c.folds[e] = foldResult{val: v, ok: ok}
	return v, ok
}

type foldResult struct {
	val constVal
	ok  bool
}

func (c *checker) constOfUncached(e ast.Expr) (constVal, bool) {
	switch x := e.(type) {
	case *ast.ParenExpr:
		return c.constOf(x.X)

	case *ast.BasicLit:
		return c.constLit(x)

	case *ast.BoolLit:
		return constVal{kind: constBool, b: x.Value}, true

	case *ast.Ident:
		o := c.info.Uses[x]
		if o == nil || o.Kind != Const {
			return constVal{}, false
		}
		v, ok := c.constVals[o]
		return v, ok

	case *ast.UnaryExpr:
		v, ok := c.constOf(x.X)
		if !ok {
			return constVal{}, false
		}
		return c.constUnary(x, v)

	case *ast.BinaryExpr:
		a, ok := c.constOf(x.X)
		if !ok {
			return constVal{}, false
		}
		b, ok := c.constOf(x.Y)
		if !ok {
			return constVal{}, false
		}
		return c.constBinary(x, a, b)
	}
	return constVal{}, false
}

func (c *checker) constLit(x *ast.BasicLit) (constVal, bool) {
	switch x.Kind {
	case token.INT:
		n, err := strconv.ParseInt(strings.ReplaceAll(x.Value, "_", ""), 0, 64)
		if err != nil {
			c.errorf(x.Pos(), "integer literal %s overflows int", x.Value)
			return constVal{}, false
		}
		return constVal{kind: constInt, i: n}, true

	case token.FLOAT:
		f, err := strconv.ParseFloat(strings.ReplaceAll(x.Value, "_", ""), 64)
		if err != nil {
			return constVal{}, false
		}
		return constVal{kind: constFloat, f: f}, true

	case token.STRING:
		return constVal{kind: constString, s: x.Value}, true

	case token.IMAG:
		// A complex literal, either a bare imaginary (`2.0i`) or a folded
		// `a ± bi` (resolved question R7). The parser stores the whole thing
		// as one token's text.
		re, im, ok := parseComplex(x.Value)
		if !ok {
			c.errorf(x.Pos(), "malformed complex literal %s", x.Value)
			return constVal{}, false
		}
		return constVal{kind: constComplex, re: re, im: im}, true
	}
	return constVal{}, false
}

// parseComplex reads the text of a complex literal: "2.0i", "1.0+2.0i",
// "-1.0-3.0i". The imaginary part is always last and always carries the `i`.
func parseComplex(text string) (re, im float64, ok bool) {
	t := strings.ReplaceAll(text, "_", "")
	if !strings.HasSuffix(t, "i") {
		return 0, 0, false
	}
	t = t[:len(t)-1]

	// Find the sign joining the two parts: the last + or - that is neither the
	// leading sign nor an exponent marker.
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

	rePart, imPart := t[:split], t[split:]
	if imPart == "+" || imPart == "-" {
		imPart += "1" // `1.0+i` is not written today, but do not divide by zero on it
	}
	r, err := strconv.ParseFloat(rePart, 64)
	if err != nil {
		return 0, 0, false
	}
	m, err := strconv.ParseFloat(imPart, 64)
	if err != nil {
		return 0, 0, false
	}
	return r, m, true
}

func (c *checker) constUnary(x *ast.UnaryExpr, v constVal) (constVal, bool) {
	switch x.Op {
	case token.SUB:
		switch v.kind {
		case constInt:
			if v.i == math.MinInt64 {
				c.errorf(x.OpPos, "constant expression overflows int")
				return constVal{}, false
			}
			return constVal{kind: constInt, i: -v.i}, true
		case constFloat:
			return constVal{kind: constFloat, f: -v.f}, true
		case constComplex:
			return constVal{kind: constComplex, re: -v.re, im: -v.im}, true
		}
	case token.NOT:
		if v.kind == constBool {
			return constVal{kind: constBool, b: !v.b}, true
		}
	}
	return constVal{}, false
}

func (c *checker) constBinary(x *ast.BinaryExpr, a, b constVal) (constVal, bool) {
	if a.kind != b.kind {
		return constVal{}, false // a type error the operand check already reported
	}

	switch a.kind {
	case constInt:
		return c.constIntOp(x, a.i, b.i)

	case constComplex:
		switch x.Op {
		case token.ADD:
			return constVal{kind: constComplex, re: a.re + b.re, im: a.im + b.im}, true
		case token.SUB:
			return constVal{kind: constComplex, re: a.re - b.re, im: a.im - b.im}, true
		case token.MUL:
			return constVal{kind: constComplex, re: a.re*b.re - a.im*b.im, im: a.re*b.im + a.im*b.re}, true
		}

	case constFloat:
		switch x.Op {
		case token.ADD:
			return constVal{kind: constFloat, f: a.f + b.f}, true
		case token.SUB:
			return constVal{kind: constFloat, f: a.f - b.f}, true
		case token.MUL:
			return constVal{kind: constFloat, f: a.f * b.f}, true
		case token.QUO:
			// "float division by zero yields IEEE infinity and does not
			// panic" (chapter 04). So it is not a compile error either.
			return constVal{kind: constFloat, f: a.f / b.f}, true
		case token.POW:
			return constVal{kind: constFloat, f: math.Pow(a.f, b.f)}, true
		}

	case constString:
		if x.Op == token.ADD {
			return constVal{kind: constString, s: a.s + b.s}, true
		}

	case constBool:
		switch x.Op {
		case token.LAND:
			return constVal{kind: constBool, b: a.b && b.b}, true
		case token.LOR:
			return constVal{kind: constBool, b: a.b || b.b}, true
		}
	}

	// Comparisons fold too, but nothing in Phase 2 needs their value, and a
	// half-folded comparison would be worse than none.
	return constVal{}, false
}

func (c *checker) constIntOp(x *ast.BinaryExpr, a, b int64) (constVal, bool) {
	overflow := func() (constVal, bool) {
		c.hint(x.OpPos,
			"constant expression overflows int",
			"int is 64-bit signed; overflow traps at runtime and is an error here (R5)")
		return constVal{}, false
	}

	switch x.Op {
	case token.ADD:
		r := a + b
		if (a > 0 && b > 0 && r < 0) || (a < 0 && b < 0 && r >= 0) {
			return overflow()
		}
		return constVal{kind: constInt, i: r}, true

	case token.SUB:
		r := a - b
		if (a >= 0 && b < 0 && r < 0) || (a < 0 && b > 0 && r >= 0) {
			return overflow()
		}
		return constVal{kind: constInt, i: r}, true

	case token.MUL:
		if a == 0 || b == 0 {
			return constVal{kind: constInt, i: 0}, true
		}
		r := a * b
		if r/a != b || (a == -1 && b == math.MinInt64) || (b == -1 && a == math.MinInt64) {
			return overflow()
		}
		return constVal{kind: constInt, i: r}, true

	case token.QUO, token.REM:
		if b == 0 {
			c.errorf(x.OpPos, "division by zero in a constant expression")
			return constVal{}, false
		}
		if a == math.MinInt64 && b == -1 {
			return overflow()
		}
		if x.Op == token.QUO {
			return constVal{kind: constInt, i: a / b}, true // truncating
		}
		return constVal{kind: constInt, i: a % b}, true // sign of the dividend

	case token.POW:
		if b < 0 {
			c.errorf(x.OpPos, "negative exponent in an int constant expression")
			return constVal{}, false
		}
		r := int64(1)
		for i := int64(0); i < b; i++ {
			if r != 0 && (r*a)/r != a {
				return overflow()
			}
			r *= a
		}
		return constVal{kind: constInt, i: r}, true
	}
	return constVal{}, false
}
