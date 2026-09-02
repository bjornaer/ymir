package types

// This file holds every question the checker asks about a type. Chapter 02 of
// docs/spec is normative throughout; each function names the section it
// implements.

// IsInvalid reports whether t is the recovery type. Invalid propagates through
// assignability in both directions so that one type error does not cascade.
func IsInvalid(t Type) bool {
	b, ok := t.(*Basic)
	return ok && b.Kind == KindInvalid
}

// ---------------------------------------------------------------------------
// Identity

// Identical implements chapter 02 §Assignability: identity is structural for
// array, map, tuple, chan, func and matrix, and nominal for struct and enum.
func Identical(a, b Type) bool {
	if a == nil || b == nil {
		return false
	}
	if a == b {
		return true
	}

	switch x := a.(type) {
	case *Basic:
		y, ok := b.(*Basic)
		return ok && x.Kind == y.Kind

	case *Named:
		// Nominal: pointer identity is the whole rule. Reaching here with
		// a != b means two different declarations.
		return false

	case *nilType:
		_, ok := b.(*nilType)
		return ok

	case *Array:
		y, ok := b.(*Array)
		return ok && Identical(x.Elem, y.Elem)

	case *Map:
		y, ok := b.(*Map)
		return ok && Identical(x.Key, y.Key) && Identical(x.Value, y.Value)

	case *Tuple:
		y, ok := b.(*Tuple)
		return ok && identicalList(x.Elems, y.Elems)

	case *Matrix:
		y, ok := b.(*Matrix)
		return ok && Identical(x.Elem, y.Elem)

	case *Chan:
		y, ok := b.(*Chan)
		return ok && Identical(x.Elem, y.Elem)

	case *Func:
		y, ok := b.(*Func)
		if !ok || !identicalList(x.Params, y.Params) || !identicalList(x.Results, y.Results) {
			return false
		}
		// `mut` is part of the type: a function that borrows its argument is
		// not interchangeable with one that copies it.
		for i := range x.Params {
			if x.MutAt(i) != y.MutAt(i) {
				return false
			}
		}
		return true

	case *Union:
		y, ok := b.(*Union)
		if !ok || len(x.Members) != len(y.Members) {
			return false
		}
		// Members are normalized: deduplicated and sorted by Key. Equal sets
		// are therefore equal sequences.
		for i := range x.Members {
			if x.Members[i] != y.Members[i] {
				return false
			}
		}
		return true

	case *Nullable:
		y, ok := b.(*Nullable)
		return ok && Identical(x.Elem, y.Elem)

	case *Qubit:
		_, ok := b.(*Qubit)
		return ok

	case *QReg:
		y, ok := b.(*QReg)
		return ok && x.N == y.N
	}

	return false
}

func identicalList(a, b []Type) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if !Identical(a[i], b[i]) {
			return false
		}
	}
	return true
}

// ---------------------------------------------------------------------------
// Assignability

// Assignable reports whether a value of type src may be assigned to a location
// of type dst.
//
// Chapter 02 §Assignability states it as the smallest relation satisfying four
// rules, and they compose:
//
//  1. src is assignable to dst when they are identical;
//  2. src is assignable to ?T when src is assignable to T;
//  3. nil is assignable to any ?T;
//  4. a union S is assignable to a union T when S ⊆ T, a bare enum being the
//     one-member union of itself.
//
// Rules 2 and 4 together are what make `var e: ?(IOError | ParseError) = someIOError`
// legal. There is no other subtyping, no coercion, and no numeric promotion.
func Assignable(src, dst Type) bool {
	if src == nil || dst == nil {
		return false
	}
	// Recovery: never report a second error about a type we already failed to
	// determine.
	if IsInvalid(src) || IsInvalid(dst) {
		return true
	}
	if Identical(src, dst) {
		return true
	}

	if _, isNil := src.(*nilType); isNil {
		// Rule 3. nil belongs to nullable types and to nothing else (N3).
		_, ok := dst.(*Nullable)
		return ok
	}

	if d, ok := dst.(*Nullable); ok {
		// Rule 2, applied to ?S -> ?T as well as S -> ?T. The former is what
		// lets a function declaring ?(IOError | ParseError) return a callee's
		// ?IOError directly.
		return Assignable(Underlying(src), d.Elem)
	}

	// Rule 4. Note this is reached only when dst is not nullable, so a bare
	// union assigns to a bare union.
	return Subset(src, dst)
}

// Subset reports whether error set src is a subset of error set dst. Both must
// be error sets — an enum or a union of enums — or the answer is false.
func Subset(src, dst Type) bool {
	sm, ok := Members(src)
	if !ok {
		return false
	}
	dm, ok := Members(dst)
	if !ok {
		return false
	}
	for _, m := range sm {
		found := false
		for _, d := range dm {
			if m == d {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

// ---------------------------------------------------------------------------
// Linearity

// IsLinear reports whether values of t must be consumed exactly once
// (chapter 02 §Type classification).
//
// That is qubit, qreg[N], a struct transitively containing one, and an enum with
// a linear payload.
//
// Containers are answered honestly here — an array of qubits would be linear —
// but compiler/check rejects such a type where it is written (R8), so no value
// ever has one. Rule L1 needs each linear value proved consumed exactly once, and
// a container's length is a runtime value, so the proof does not exist. This
// stays as a backstop rather than an assumption that the formation check is
// exhaustive.
func IsLinear(t Type) bool { return isLinear(t, nil) }

func isLinear(t Type, seen map[*Named]bool) bool {
	switch x := t.(type) {
	case *Qubit, *QReg:
		return true

	case *Named:
		if seen[x] {
			return false // already being examined further up the stack
		}
		if seen == nil {
			seen = map[*Named]bool{}
		}
		seen[x] = true
		defer delete(seen, x)

		for _, f := range x.Fields {
			if isLinear(f.Type, seen) {
				return true
			}
		}
		for _, v := range x.Variants {
			for _, p := range v.Payload {
				if isLinear(p, seen) {
					return true
				}
			}
		}
		return false

	case *Array:
		return isLinear(x.Elem, seen)
	case *Matrix:
		return isLinear(x.Elem, seen)
	case *Chan:
		return isLinear(x.Elem, seen)
	case *Map:
		return isLinear(x.Value, seen)
	case *Tuple:
		for _, e := range x.Elems {
			if isLinear(e, seen) {
				return true
			}
		}
		return false
	case *Nullable:
		// Rejected by N5, but answer honestly if one is built anyway.
		return isLinear(x.Elem, seen)
	case *Union:
		for _, m := range x.Members {
			if isLinear(m, seen) {
				return true
			}
		}
		return false
	}

	return false
}

// IsUnrestricted is the complement of IsLinear. Chapter 02 gives every type
// exactly one multiplicity, so this is total.
func IsUnrestricted(t Type) bool { return !IsLinear(t) }

// ---------------------------------------------------------------------------
// Zero values

// HasZeroValue reports whether `var x: T` without an initializer is legal
// (chapter 02 §Zero values and definite assignment).
//
// Types with no zero value: enum and bare union (no privileged variant), chan
// and func (nil belongs only to nullable types, rule N3), and every linear
// type.
func HasZeroValue(t Type) bool { return hasZero(t, nil) }

func hasZero(t Type, seen map[*Named]bool) bool {
	if IsLinear(t) {
		return false
	}

	switch x := t.(type) {
	case *Basic:
		return true
	case *nilType:
		return true
	case *Nullable:
		return true // nil
	case *Array, *Map, *Matrix:
		return true // empty
	case *Chan, *Func:
		return false
	case *Union:
		return false
	case *Qubit, *QReg:
		return false

	case *Named:
		if x.Kind == Enum {
			return false
		}
		if seen[x] {
			return true // a cycle can only run through a container, which is zeroable
		}
		if seen == nil {
			seen = map[*Named]bool{}
		}
		seen[x] = true
		defer delete(seen, x)
		for _, f := range x.Fields {
			if !hasZero(f.Type, seen) {
				return false
			}
		}
		return true

	case *Tuple:
		for _, e := range x.Elems {
			if !hasZero(e, seen) {
				return false
			}
		}
		return true
	}

	return false
}

// ---------------------------------------------------------------------------
// Formation constraints

// IsValidMapKey implements chapter 02 §map[K, V]: a key must be a primitive
// type or a struct whose fields are all primitive. The spec's wording is not
// transitive, so a struct of structs is rejected.
func IsValidMapKey(t Type) bool {
	switch x := t.(type) {
	case *Basic:
		return x.Kind != KindInvalid
	case *Named:
		if x.Kind != Struct {
			return false
		}
		for _, f := range x.Fields {
			if b, ok := f.Type.(*Basic); !ok || b.Kind == KindInvalid {
				return false
			}
		}
		return true
	}
	return false
}

// IsValidMatrixElem implements chapter 02 §matrix[T]: T is float or complex.
func IsValidMatrixElem(t Type) bool {
	b, ok := t.(*Basic)
	return ok && (b.Kind == KindFloat || b.Kind == KindComplex)
}

// IsErrorSet reports whether t may occupy a function's error position: an enum,
// or a union of enums. Chapter 06 §The error position.
func IsErrorSet(t Type) bool {
	_, ok := Members(t)
	return ok
}

// IsOrdered reports whether <, <=, > and >= are defined on t. Chapter 04
// §Operand typing: int, float and string are ordered; complex is not.
func IsOrdered(t Type) bool {
	b, ok := t.(*Basic)
	return ok && (b.Kind == KindInt || b.Kind == KindFloat || b.Kind == KindString)
}

// IsNumeric reports whether arithmetic operators are defined on t.
func IsNumeric(t Type) bool {
	b, ok := t.(*Basic)
	return ok && (b.Kind == KindInt || b.Kind == KindFloat || b.Kind == KindComplex)
}
