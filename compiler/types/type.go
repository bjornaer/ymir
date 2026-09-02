// Package types defines Ymir's semantic types.
//
// These are distinct from ast.Type, which records what a programmer wrote. A
// *ast.NullableType is syntax; a *types.Nullable is meaning. The checker in
// compiler/check resolves one to the other and keeps the result in a side table
// rather than writing it back onto the AST, so the tree stays a faithful record
// of the source.
//
// The package has no dependency on compiler/ast, compiler/token, or
// compiler/diag: it answers questions about types and never reports anything.
// Diagnostics, and the positions they need, belong to the caller.
//
// Chapter 02 of docs/spec is normative for everything here.
package types

import (
	"sort"
	"strconv"
	"strings"
)

// A Type is a semantic type. The set of implementations is closed; the
// unexported marker method keeps it that way.
type Type interface {
	String() string
	typ()
}

// ---------------------------------------------------------------------------
// Basic types

// BasicKind identifies a primitive type.
type BasicKind int

const (
	// KindInvalid is the type of an expression the checker could not type. It
	// is assignable in both directions so that one error does not cascade into
	// a dozen more.
	KindInvalid BasicKind = iota
	KindInt
	KindFloat
	KindComplex
	KindBool
	KindString
)

// Basic is a primitive type. Chapter 02 §Primitive types.
//
// Note that error is NOT here: it is a predeclared enum (see ErrorEnum), and
// like every enum it has no zero value and no nil.
type Basic struct {
	Kind BasicKind
	name string
}

func (*Basic) typ()             {}
func (b *Basic) String() string { return b.name }

// The predeclared primitive types. Compare against these by pointer.
var (
	Invalid = &Basic{KindInvalid, "invalid type"}
	Int     = &Basic{KindInt, "int"}
	Float   = &Basic{KindFloat, "float"}
	Complex = &Basic{KindComplex, "complex"}
	Bool    = &Basic{KindBool, "bool"}
	String  = &Basic{KindString, "string"}
)

// nilType is the type of the nil literal. It is not writable in source: `nil`
// is a value that belongs to every ?T (rule N3) and to nothing else.
type nilType struct{}

func (*nilType) typ()           {}
func (*nilType) String() string { return "nil" }

// Nil is the type of the nil literal.
var Nil Type = &nilType{}

// ---------------------------------------------------------------------------
// Named types: struct and enum

// NamedKind distinguishes the two nominal type forms.
type NamedKind int

const (
	Struct NamedKind = iota
	Enum
)

// A Field is one struct field. Chapter 02 §Structs.
type Field struct {
	Name string
	Type Type
}

// A Variant is one enum variant, with a positional payload that may be empty.
// Chapter 02 §Enums.
type Variant struct {
	Name    string
	Payload []Type
}

// Named is a struct or an enum.
//
// Identity is nominal (chapter 02 §Assignability): two *Named denote the same
// type only when they are the same pointer. Two structs with identical fields
// but different names are different types. The checker therefore allocates
// exactly one *Named per declaration.
type Named struct {
	Kind     NamedKind
	Module   string     // declaring module, for the sort key and qualified rendering
	Name     string     // as written
	Fields   []*Field   // Struct only
	Variants []*Variant // Enum only
}

func (*Named) typ()             {}
func (n *Named) String() string { return n.Name }

// Key is the module-qualified name. It orders union members deterministically
// and disambiguates two enums that share a short name.
func (n *Named) Key() string {
	if n.Module == "" {
		return n.Name
	}
	return n.Module + "." + n.Name
}

// LookupField returns the named field, or nil.
func (n *Named) LookupField(name string) *Field {
	for _, f := range n.Fields {
		if f.Name == name {
			return f
		}
	}
	return nil
}

// LookupVariant returns the named variant, or nil.
func (n *Named) LookupVariant(name string) *Variant {
	for _, v := range n.Variants {
		if v.Name == name {
			return v
		}
	}
	return nil
}

// ---------------------------------------------------------------------------
// Composite types
//
// Identity for all of these is structural (chapter 02 §Assignability).

// Array is array[T]: dynamically sized, homogeneous, reference semantics.
type Array struct{ Elem Type }

func (*Array) typ()             {}
func (a *Array) String() string { return "array[" + a.Elem.String() + "]" }

// Map is map[K, V]. K must satisfy IsValidMapKey.
type Map struct{ Key, Value Type }

func (*Map) typ() {}
func (m *Map) String() string {
	return "map[" + m.Key.String() + ", " + m.Value.String() + "]"
}

// Tuple is tuple[T1, T2, ...]: fixed length, heterogeneous, immutable.
//
// A function's result list is NOT a Tuple. Chapter 04 forbids a multi-valued
// call in expression position, so multiple results are not a first-class value
// and are kept as Func.Results instead.
type Tuple struct{ Elems []Type }

func (*Tuple) typ()             {}
func (t *Tuple) String() string { return "tuple[" + joinTypes(t.Elems, ", ") + "]" }

// Matrix is matrix[T], two-dimensional and rectangular. T must satisfy
// IsValidMatrixElem.
type Matrix struct{ Elem Type }

func (*Matrix) typ()             {}
func (m *Matrix) String() string { return "matrix[" + m.Elem.String() + "]" }

// Chan is chan[T]. It has no zero value; write ?chan[T] for one that may be
// absent (chapter 02 §Zero values).
type Chan struct{ Elem Type }

func (*Chan) typ()             {}
func (c *Chan) String() string { return "chan[" + c.Elem.String() + "]" }

// Func is a function type. Results holds every result component including the
// error position, which is simply the last one when it is a nullable error set.
//
// Mut records which parameters are declared `mut`, and is part of the type: a
// function taking a mutable reference is not the same type as one taking a copy,
// and rule L3 turns on the difference — passing a linear value consumes it
// unless the parameter borrows it. A nil or short Mut means "not mut".
type Func struct {
	Params  []Type
	Results []Type
	Mut     []bool
}

// MutAt reports whether parameter i is declared `mut`.
func (f *Func) MutAt(i int) bool { return i < len(f.Mut) && f.Mut[i] }

func (*Func) typ() {}
func (f *Func) String() string {
	s := "func(" + joinTypes(f.Params, ", ") + ")"
	switch len(f.Results) {
	case 0:
		return s
	case 1:
		return s + " -> " + f.Results[0].String()
	default:
		return s + " -> (" + joinTypes(f.Results, ", ") + ")"
	}
}

// ---------------------------------------------------------------------------
// Unions

// Union is A | B. Chapter 02 §Union types.
//
// Members are always enums, always at least two, deduplicated, and sorted by
// Key. Build one only with NewUnion, which establishes all of that; a Union
// assembled by hand will compare wrong.
type Union struct{ Members []*Named }

func (*Union) typ() {}
func (u *Union) String() string {
	parts := make([]string, len(u.Members))
	for i, m := range u.Members {
		parts[i] = m.Name
	}
	return strings.Join(parts, " | ")
}

// NewUnion normalizes a union per chapter 02 §Union types: nested unions are
// flattened, duplicates collapse, members are sorted so that A | B and B | A
// are the same value, and a one-member union is the bare enum itself.
//
// A member that is not an enum yields Invalid. The checker validates members
// individually first, because only it has the position to report.
func NewUnion(members ...Type) Type {
	var flat []*Named
	for _, m := range members {
		switch x := m.(type) {
		case *Named:
			if x.Kind != Enum {
				return Invalid
			}
			flat = append(flat, x)
		case *Union:
			flat = append(flat, x.Members...)
		default:
			// Members MUST all be enum types; int | string is not a type.
			return Invalid
		}
	}

	sort.SliceStable(flat, func(i, j int) bool { return flat[i].Key() < flat[j].Key() })

	uniq := flat[:0]
	for i, m := range flat {
		if i == 0 || m != flat[i-1] {
			uniq = append(uniq, m)
		}
	}

	switch len(uniq) {
	case 0:
		return Invalid
	case 1:
		return uniq[0]
	default:
		return &Union{Members: uniq}
	}
}

// Members returns the member set of an error set. A single enum is the
// one-member set of itself (chapter 02 §Union types). ok is false for anything
// that is not an error set.
func Members(t Type) (members []*Named, ok bool) {
	switch x := t.(type) {
	case *Named:
		if x.Kind == Enum {
			return []*Named{x}, true
		}
	case *Union:
		return x.Members, true
	}
	return nil, false
}

// ---------------------------------------------------------------------------
// Nullables

// Nullable is ?T. Chapter 02 §Nullable types.
type Nullable struct{ Elem Type }

func (*Nullable) typ() {}
func (n *Nullable) String() string {
	// Parenthesize a union so the rendering round-trips: `?A | B` would read as
	// a union of `?A` and `B` (rule N1).
	if _, isUnion := n.Elem.(*Union); isUnion {
		return "?(" + n.Elem.String() + ")"
	}
	return "?" + n.Elem.String()
}

// NewNullable applies ? to a type, collapsing per rule N2: ??T is ?T.
//
// It does not enforce rule N5 (? requires an unrestricted type), because
// rejecting ?qubit needs a position for the diagnostic. Callers check IsLinear
// first.
func NewNullable(t Type) Type {
	if t == nil {
		return Invalid
	}
	if b, ok := t.(*Basic); ok && b.Kind == KindInvalid {
		return Invalid
	}
	if _, already := t.(*Nullable); already {
		return t
	}
	return &Nullable{Elem: t}
}

// Underlying strips one ? from a nullable, which is what narrowing yields
// (rule N6). Any other type is returned unchanged.
func Underlying(t Type) Type {
	if n, ok := t.(*Nullable); ok {
		return n.Elem
	}
	return t
}

// ---------------------------------------------------------------------------
// Quantum types
//
// Present from Phase 2 per decision D3, with no way to construct a value until
// Phase 7. Linearity is a property of the type system (chapter 02
// §Type classification), not of the quantum fragment, so the checker is built
// around them long before they can appear in a program.

// Qubit is the qubit type. Linear.
type Qubit struct{}

func (*Qubit) typ()           {}
func (*Qubit) String() string { return "qubit" }

// QubitType is the single qubit type value.
var QubitType = &Qubit{}

// QReg is qreg[N], a register of N qubits. Linear.
type QReg struct{ N int }

func (*QReg) typ()             {}
func (q *QReg) String() string { return "qreg[" + strconv.Itoa(q.N) + "]" }

// ---------------------------------------------------------------------------
// Builtins

// Builtin is a predeclared function. Several of them (len, append, make_chan)
// are polymorphic in a way no Func can express until Q3 is answered, so the
// checker types every call to one ad hoc rather than by assignability.
type Builtin struct {
	Name string
}

func (*Builtin) typ()             {}
func (b *Builtin) String() string { return "builtin " + b.Name }

// ---------------------------------------------------------------------------

func joinTypes(ts []Type, sep string) string {
	parts := make([]string, len(ts))
	for i, t := range ts {
		parts[i] = t.String()
	}
	return strings.Join(parts, sep)
}
