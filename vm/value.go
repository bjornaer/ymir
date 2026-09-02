// Package vm executes Ymir bytecode.
//
// There is exactly one execution engine. No interpreter mode, no fallback path,
// no "fast path" that handles a subset. Legacy's worst defect was `func main()`
// running under one engine and silently doing nothing under the other, and the
// only reliable way not to have that bug is not to have a second engine.
//
// `ymir run` type-checks before it compiles, so nothing the checker rejects ever
// reaches this package. Every panic here is therefore a bug in the compiler or
// the VM, not a program error the checker should have caught — except the ones
// chapter 06 §panic enumerates, which are genuine runtime failures.
package vm

import (
	"strconv"
	"strings"
)

// Kind tags a runtime value.
type Kind uint8

const (
	KindNil Kind = iota
	KindBool
	KindInt
	KindFloat
	KindComplex
	KindString
)

// A Value is any Ymir value at runtime.
//
// Resolved question R10: one uniform tagged representation, not unboxed
// primitives. That dissolves the `?int` problem R3 flagged rather than solving
// it — `?int` needs no special case, because absent is KindNil and present is
// KindInt, and every opcode that touches one already handles both kinds.
//
// The cost is memory and speed against a bare int64. Non-goal 1 already accepts
// that a bytecode VM is 10-50x slower than optimized native code; this is part
// of the same bill. Unboxing stays available later behind frozen semantics.
type Value struct {
	Kind Kind
	N    int64   // KindInt, and 0/1 for KindBool
	F    float64 // KindFloat, and the real part of KindComplex
	G    float64 // the imaginary part of KindComplex
	Ref  any     // KindString holds a string; heap values arrive in Phase 4
}

// Constructors. Used by the VM and by tests; a Value is never built field-wise
// outside this file, so an inconsistent Kind cannot be spelled by accident.

func Nil() Value            { return Value{Kind: KindNil} }
func Int(n int64) Value     { return Value{Kind: KindInt, N: n} }
func Float(f float64) Value { return Value{Kind: KindFloat, F: f} }
func Str(s string) Value    { return Value{Kind: KindString, Ref: s} }

func Complex(re, im float64) Value {
	return Value{Kind: KindComplex, F: re, G: im}
}

func Bool(b bool) Value {
	v := Value{Kind: KindBool}
	if b {
		v.N = 1
	}
	return v
}

// IsNil reports whether a value is the absent one. This is the only test the
// runtime makes about nullability: the checker has already proved that a `nil`
// can only reach a location whose type admits it (rule N3).
func (v Value) IsNil() bool { return v.Kind == KindNil }

// IsTrue reports the truth of a bool. It is not a truthiness test — the checker
// has already required the value to be a bool (chapter 05 §if), so anything
// else here is a compiler bug.
func (v Value) IsTrue() bool { return v.Kind == KindBool && v.N != 0 }

// String returns the string a KindString holds. Calling it on another kind is a
// compiler bug, and returning "" would hide it, so it reports what it got.
func (v Value) String() string {
	if v.Kind != KindString {
		return v.Display()
	}
	s, _ := v.Ref.(string)
	return s
}

// Display renders a value the way `print` and `str()` do.
//
// This is user-visible output, so it is part of the language's observable
// behaviour and the conformance suite asserts it.
func (v Value) Display() string {
	switch v.Kind {
	case KindNil:
		return "nil"
	case KindBool:
		if v.N != 0 {
			return "true"
		}
		return "false"
	case KindInt:
		return strconv.FormatInt(v.N, 10)
	case KindFloat:
		return formatFloat(v.F)
	case KindComplex:
		return formatFloat(v.F) + signOf(v.G) + formatFloat(abs(v.G)) + "i"
	case KindString:
		s, _ := v.Ref.(string)
		return s
	}
	return "<value>"
}

// formatFloat renders a float so that a whole number keeps a decimal point.
//
// `3.5` prints as "3.5" and `4.0` as "4.0", not "4" — otherwise a float and an
// int would be indistinguishable in output, and case
// types/float_literal_arithmetic asserts the difference.
func formatFloat(f float64) string {
	s := strconv.FormatFloat(f, 'g', -1, 64)
	if !strings.ContainsAny(s, ".eE") && !strings.Contains(s, "Inf") && !strings.Contains(s, "NaN") {
		s += ".0"
	}
	return s
}

func signOf(f float64) string {
	if f < 0 {
		return "-"
	}
	return "+"
}

func abs(f float64) float64 {
	if f < 0 {
		return -f
	}
	return f
}

// Equal implements `==`, which chapter 04 defines on any unrestricted type.
//
// Float and complex equality is IEEE, so nan != nan. Deep structural equality
// for array, map, struct and enum arrives with those types in Phase 4.
func Equal(a, b Value) bool {
	if a.Kind != b.Kind {
		// Only nil compares across kinds, and the checker has already required
		// the other side to be nullable (rule N3).
		return false
	}
	switch a.Kind {
	case KindNil:
		return true
	case KindBool, KindInt:
		return a.N == b.N
	case KindFloat:
		return a.F == b.F
	case KindComplex:
		return a.F == b.F && a.G == b.G
	case KindString:
		return a.String() == b.String()
	}
	return false
}
