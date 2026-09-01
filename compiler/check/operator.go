package check

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Operators, per the table in chapter 04 §Operand typing.
//
// The rule underneath all of it: "Both operands of a binary operator MUST have
// identical types (chapter 02 — no implicit conversion)." There is no promotion
// and no coercion, so `1 + 2.0` is an error rather than a float.

func (c *checker) unaryExpr(scope *Scope, x *ast.UnaryExpr) types.Type {
	operand := c.expr(scope, x.X)
	if types.IsInvalid(operand) {
		return types.Invalid
	}

	switch x.Op {
	case token.SUB:
		if !types.IsNumeric(operand) {
			c.errorf(x.OpPos, "invalid operation: - on %s", operand)
			return types.Invalid
		}
		// Fold now, so that -9223372036854775808 written as a negation of a
		// literal is caught rather than silently wrapping.
		c.constOf(x)
		return operand

	case token.NOT:
		if !types.Identical(operand, types.Bool) {
			c.errorf(x.OpPos, "invalid operation: ! on %s, want bool", operand)
			return types.Invalid
		}
		return types.Bool

	case token.CHAN_OP: // <-ch
		ch, ok := operand.(*types.Chan)
		if !ok {
			c.errorf(x.OpPos, "invalid operation: receive from %s, want a channel", operand)
			return types.Invalid
		}
		return ch.Elem
	}

	c.errorf(x.OpPos, "invalid unary operator %s", x.Op)
	return types.Invalid
}

func (c *checker) binaryExpr(scope *Scope, x *ast.BinaryExpr) types.Type {
	lhs := c.expr(scope, x.X)
	rhs := c.expr(scope, x.Y)

	// Comparing against nil is its own rule, because nil has no type of its
	// own to match against (N3).
	if isNilType(lhs) || isNilType(rhs) {
		return c.nilComparison(x, lhs, rhs)
	}

	if types.IsInvalid(lhs) || types.IsInvalid(rhs) {
		return c.resultOfInvalid(x)
	}

	if !types.Identical(lhs, rhs) {
		// Rule N4 is the common case worth naming: a ?T must be narrowed before
		// it is used as a T, and `x + 1` where x is ?int is exactly that.
		if n, ok := lhs.(*types.Nullable); ok && types.Identical(n.Elem, rhs) {
			c.narrowFirst(x.OpPos, lhs, n.Elem)
			return c.resultOfInvalid(x)
		}
		if n, ok := rhs.(*types.Nullable); ok && types.Identical(n.Elem, lhs) {
			c.narrowFirst(x.OpPos, rhs, n.Elem)
			return c.resultOfInvalid(x)
		}
		c.hint(x.OpPos,
			"invalid operation: mismatched types "+lhs.String()+" and "+rhs.String(),
			"there is no implicit conversion; write "+conversionHint(lhs, rhs))
		return c.resultOfInvalid(x)
	}

	t := lhs
	switch x.Op {
	case token.ADD:
		// int, float, complex, string, matrix
		if types.IsNumeric(t) || types.Identical(t, types.String) || isMatrix(t) {
			return c.foldedResult(x, t)
		}

	case token.SUB, token.MUL:
		if types.IsNumeric(t) || isMatrix(t) {
			return c.foldedResult(x, t)
		}

	case token.QUO, token.POW:
		if types.IsNumeric(t) {
			return c.foldedResult(x, t)
		}

	case token.REM:
		// "% is defined only on int."
		if types.Identical(t, types.Int) {
			return c.foldedResult(x, t)
		}
		c.errorf(x.OpPos, "invalid operation: %% is defined only on int, got %s", t)
		return types.Invalid

	case token.AT:
		if isMatrix(t) {
			return t
		}
		c.errorf(x.OpPos, "invalid operation: @ is matrix multiplication, got %s", t)
		return types.Invalid

	case token.LSS, token.LEQ, token.GTR, token.GEQ:
		// int, float and string are ordered; complex is not.
		if types.IsOrdered(t) {
			return types.Bool
		}
		if types.Identical(t, types.Complex) {
			c.hint(x.OpPos,
				"complex is not ordered, so "+x.Op.String()+" is not defined on it",
				"compare real(z) or imag(z), or use == and !=")
			return types.Bool
		}
		c.errorf(x.OpPos, "invalid operation: %s is not defined on %s", x.Op, t)
		return types.Bool

	case token.EQL, token.NEQ:
		// "any unrestricted type", so everything except a linear one.
		if types.IsLinear(t) {
			c.hint(x.OpPos,
				"linear values must not be compared, and "+t.String()+" is linear",
				"comparison would read the value without consuming it (rule L1)")
		}
		return types.Bool

	case token.LAND, token.LOR:
		if types.Identical(t, types.Bool) {
			return types.Bool
		}
		c.errorf(x.OpPos, "invalid operation: %s is defined only on bool, got %s", x.Op, t)
		return types.Bool
	}

	c.errorf(x.OpPos, "invalid operation: %s is not defined on %s", x.Op, t)
	return types.Invalid
}

// narrowFirst is rule N4's diagnostic: a nullable used where its element type
// is wanted.
func (c *checker) narrowFirst(pos token.Position, nullable, elem types.Type) {
	c.hint(pos,
		nullable.String()+" must be narrowed before it is used as "+elem.String(),
		"guard it: `if x != nil { ... }` narrows x to "+elem.String()+" in that branch")
}

// nilComparison handles `x == nil` and `x != nil`, the only place nil may
// appear as an operand.
func (c *checker) nilComparison(x *ast.BinaryExpr, lhs, rhs types.Type) types.Type {
	if x.Op != token.EQL && x.Op != token.NEQ {
		c.errorf(x.OpPos, "invalid operation: %s with nil; only == and != are defined", x.Op)
		return types.Invalid
	}

	other := lhs
	if isNilType(lhs) {
		other = rhs
	}
	if isNilType(other) {
		// `nil == nil`. Vacuous, and there is no nullable type to check.
		return types.Bool
	}
	if types.IsInvalid(other) {
		return types.Bool
	}

	// Rule N3: "int, string, struct, enum, and bare unions have no nil and
	// MUST NOT be compared to it."
	if _, nullable := other.(*types.Nullable); !nullable {
		c.hint(x.OpPos,
			other.String()+" is never nil, so comparing it to nil is an error",
			"only a nullable type has nil; write ?"+other.String()+" if it may be absent")
		return types.Bool
	}
	return types.Bool
}

// foldedResult evaluates a constant expression for its side effect of reporting
// overflow and division by zero, then returns the operand type.
func (c *checker) foldedResult(x *ast.BinaryExpr, t types.Type) types.Type {
	c.constOf(x)
	return t
}

// resultOfInvalid keeps a comparison's bool result even when its operands did
// not type, so `if a == b { ... }` does not also complain about the condition.
func (c *checker) resultOfInvalid(x *ast.BinaryExpr) types.Type {
	switch x.Op {
	case token.EQL, token.NEQ, token.LSS, token.LEQ, token.GTR, token.GEQ, token.LAND, token.LOR:
		return types.Bool
	}
	return types.Invalid
}

// conversionHint suggests the explicit conversion for a mismatched pair.
func conversionHint(lhs, rhs types.Type) string {
	switch {
	case types.Identical(lhs, types.Int) && types.Identical(rhs, types.Float):
		return "float(x) on the int operand"
	case types.Identical(lhs, types.Float) && types.Identical(rhs, types.Int):
		return "float(x) on the int operand"
	case types.Identical(lhs, types.Int) && types.Identical(rhs, types.Complex),
		types.Identical(lhs, types.Float) && types.Identical(rhs, types.Complex):
		return "complex(x) on the other operand"
	}
	return "an explicit conversion, or change one of the types"
}

func isNilType(t types.Type) bool { return t == types.Nil }

func isMatrix(t types.Type) bool {
	_, ok := t.(*types.Matrix)
	return ok
}
