package vm

import (
	"math"
	"strings"

	"github.com/bjornaer/ymir/compiler/bytecode"
)

// Arithmetic and comparison.
//
// The int operations trap on overflow, per resolved question R5: "Arithmetic on
// int that overflows the signed 64-bit range MUST panic. It MUST NOT wrap and
// MUST NOT saturate — both produce a silently wrong answer." That is the cost
// R5 accepted, and it is why the opcodes are typed: float is left to IEEE, where
// chapter 04 says division by zero yields an infinity rather than trapping.

// arith executes a binary or unary arithmetic opcode, or reports that it is not
// one. The bool result says whether the opcode was handled.
func (v *VM) arith(op bytecode.Op) (bool, error) {
	switch op {

	// --- int, each trapping on overflow (R5)
	case bytecode.OpAddInt:
		b, a := v.pop(), v.pop()
		r := a.N + b.N
		if (a.N > 0 && b.N > 0 && r < 0) || (a.N < 0 && b.N < 0 && r >= 0) {
			return true, v.overflow("+")
		}
		v.push(Int(r))

	case bytecode.OpSubInt:
		b, a := v.pop(), v.pop()
		r := a.N - b.N
		if (a.N >= 0 && b.N < 0 && r < 0) || (a.N < 0 && b.N > 0 && r >= 0) {
			return true, v.overflow("-")
		}
		v.push(Int(r))

	case bytecode.OpMulInt:
		b, a := v.pop(), v.pop()
		if a.N == 0 || b.N == 0 {
			v.push(Int(0))
			break
		}
		r := a.N * b.N
		if r/a.N != b.N || (a.N == -1 && b.N == math.MinInt64) || (b.N == -1 && a.N == math.MinInt64) {
			return true, v.overflow("*")
		}
		v.push(Int(r))

	case bytecode.OpDivInt:
		b, a := v.pop(), v.pop()
		if b.N == 0 {
			// Chapter 06 §panic lists integer division by zero.
			return true, v.newPanic("integer division by zero")
		}
		if a.N == math.MinInt64 && b.N == -1 {
			return true, v.overflow("/")
		}
		v.push(Int(a.N / b.N)) // truncating, per chapter 04

	case bytecode.OpModInt:
		b, a := v.pop(), v.pop()
		if b.N == 0 {
			return true, v.newPanic("integer modulo by zero")
		}
		if a.N == math.MinInt64 && b.N == -1 {
			v.push(Int(0))
			break
		}
		v.push(Int(a.N % b.N)) // sign of the dividend, per chapter 04

	case bytecode.OpPowInt:
		b, a := v.pop(), v.pop()
		if b.N < 0 {
			return true, v.newPanic("negative exponent in an int power")
		}
		r := int64(1)
		for i := int64(0); i < b.N; i++ {
			if r != 0 && (r*a.N)/r != a.N {
				return true, v.overflow("**")
			}
			r *= a.N
		}
		v.push(Int(r))

	case bytecode.OpNegInt:
		a := v.pop()
		if a.N == math.MinInt64 {
			return true, v.overflow("-")
		}
		v.push(Int(-a.N))

	// --- float: IEEE throughout, no traps
	case bytecode.OpAddFloat:
		b, a := v.pop(), v.pop()
		v.push(Float(a.F + b.F))
	case bytecode.OpSubFloat:
		b, a := v.pop(), v.pop()
		v.push(Float(a.F - b.F))
	case bytecode.OpMulFloat:
		b, a := v.pop(), v.pop()
		v.push(Float(a.F * b.F))
	case bytecode.OpDivFloat:
		// "float division by zero yields IEEE infinity and does not panic."
		b, a := v.pop(), v.pop()
		v.push(Float(a.F / b.F))
	case bytecode.OpPowFloat:
		b, a := v.pop(), v.pop()
		v.push(Float(math.Pow(a.F, b.F)))
	case bytecode.OpNegFloat:
		a := v.pop()
		v.push(Float(-a.F))

	// --- string
	case bytecode.OpConcat:
		b, a := v.pop(), v.pop()
		var sb strings.Builder
		sb.WriteString(a.String())
		sb.WriteString(b.String())
		v.push(Str(sb.String()))

	// --- equality, dispatched on kind because chapter 04 defines == on any
	// unrestricted type
	case bytecode.OpEq:
		b, a := v.pop(), v.pop()
		v.push(Bool(Equal(a, b)))
	case bytecode.OpNe:
		b, a := v.pop(), v.pop()
		v.push(Bool(!Equal(a, b)))

	// --- ordered comparison, typed like arithmetic
	case bytecode.OpLtInt:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.N < b.N))
	case bytecode.OpLeInt:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.N <= b.N))
	case bytecode.OpGtInt:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.N > b.N))
	case bytecode.OpGeInt:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.N >= b.N))

	case bytecode.OpLtFloat:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.F < b.F))
	case bytecode.OpLeFloat:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.F <= b.F))
	case bytecode.OpGtFloat:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.F > b.F))
	case bytecode.OpGeFloat:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.F >= b.F))

	case bytecode.OpLtString:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.String() < b.String()))
	case bytecode.OpLeString:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.String() <= b.String()))
	case bytecode.OpGtString:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.String() > b.String()))
	case bytecode.OpGeString:
		b, a := v.pop(), v.pop()
		v.push(Bool(a.String() >= b.String()))

	case bytecode.OpNot:
		a := v.pop()
		v.push(Bool(!a.IsTrue()))

	default:
		return false, nil
	}
	return true, nil
}

// overflow is R5's panic. The message names the operator, because a trace line
// alone does not say which of several operations on one line overflowed.
func (v *VM) overflow(op string) error {
	return v.newPanic("integer overflow in `" + op + "`")
}
