package types

import "testing"

// Test fixtures mirroring the enums the conformance suite uses, so the
// assignability cases below are the same ones docs/spec/06-errors.md argues
// about.
var (
	ioError = &Named{Kind: Enum, Module: "m", Name: "IOError", Variants: []*Variant{
		{Name: "NotFound", Payload: []Type{String}},
	}}
	parseError = &Named{Kind: Enum, Module: "m", Name: "ParseError", Variants: []*Variant{
		{Name: "UnexpectedEOF"},
	}}
	configError = &Named{Kind: Enum, Module: "m", Name: "ConfigError", Variants: []*Variant{
		{Name: "Bad"},
	}}

	point = &Named{Kind: Struct, Module: "m", Name: "Point", Fields: []*Field{
		{Name: "x", Type: Float}, {Name: "y", Type: Float},
	}}
	// Same fields, different name: a different type (nominal identity).
	vec2 = &Named{Kind: Struct, Module: "m", Name: "Vec2", Fields: []*Field{
		{Name: "x", Type: Float}, {Name: "y", Type: Float},
	}}
)

func TestUnionNormalization(t *testing.T) {
	tests := []struct {
		name    string
		members []Type
		want    string
	}{
		{"one member collapses to the enum", []Type{ioError}, "IOError"},
		{"sorted, not source order", []Type{parseError, ioError}, "IOError | ParseError"},
		{"idempotent", []Type{ioError, ioError}, "IOError"},
		{"flattened", []Type{NewUnion(ioError, parseError), configError}, "ConfigError | IOError | ParseError"},
		{"dedup across a nested union", []Type{NewUnion(ioError, parseError), ioError}, "IOError | ParseError"},
		{"non-enum member is invalid", []Type{ioError, Int}, "invalid type"},
		{"struct member is invalid", []Type{ioError, point}, "invalid type"},
		{"no members is invalid", nil, "invalid type"},
	}
	for _, tc := range tests {
		if got := NewUnion(tc.members...).String(); got != tc.want {
			t.Errorf("%s: NewUnion = %q, want %q", tc.name, got, tc.want)
		}
	}
}

func TestUnionOrderDoesNotAffectIdentity(t *testing.T) {
	a := NewUnion(ioError, parseError)
	b := NewUnion(parseError, ioError)
	if !Identical(a, b) {
		t.Errorf("A | B and B | A must be the same type, got %s and %s", a, b)
	}
	if Identical(a, NewUnion(ioError, parseError, configError)) {
		t.Error("a union must not be identical to a strict superset")
	}
}

func TestIdentity(t *testing.T) {
	tests := []struct {
		name string
		a, b Type
		want bool
	}{
		{"same primitive", Int, Int, true},
		{"different primitives", Int, Float, false},
		{"structural array", &Array{Int}, &Array{Int}, true},
		{"array element differs", &Array{Int}, &Array{Float}, false},
		{"structural map", &Map{String, Int}, &Map{String, Int}, true},
		{"map key differs", &Map{String, Int}, &Map{Int, Int}, false},
		{"structural func", &Func{Params: []Type{Int}, Results: []Type{Bool}}, &Func{Params: []Type{Int}, Results: []Type{Bool}}, true},
		{"func arity differs", &Func{Params: []Type{Int}, Results: nil}, &Func{Params: nil, Results: nil}, false},
		{"structural tuple", &Tuple{[]Type{Int, String}}, &Tuple{[]Type{Int, String}}, true},
		{"tuple order matters", &Tuple{[]Type{Int, String}}, &Tuple{[]Type{String, Int}}, false},
		{"structural chan", &Chan{Int}, &Chan{Int}, true},
		{"nominal struct, same decl", point, point, true},
		{"nominal struct, same shape different name", point, vec2, false},
		{"nullable of identical", NewNullable(Int), NewNullable(Int), true},
		{"nullable vs bare", NewNullable(Int), Int, false},
		{"qreg width matters", &QReg{2}, &QReg{4}, false},
		{"same qreg width", &QReg{4}, &QReg{4}, true},
		// `mut` is part of a function's type: one that borrows is not
		// interchangeable with one that copies (rule L3).
		{"mut parameter differs", &Func{Params: []Type{Int}, Mut: []bool{true}}, &Func{Params: []Type{Int}}, false},
		{"same mut parameters", &Func{Params: []Type{Int}, Mut: []bool{true}}, &Func{Params: []Type{Int}, Mut: []bool{true}}, true},
		{"absent mut is not mut", &Func{Params: []Type{Int}, Mut: []bool{false}}, &Func{Params: []Type{Int}}, true},
	}
	for _, tc := range tests {
		if got := Identical(tc.a, tc.b); got != tc.want {
			t.Errorf("%s: Identical(%s, %s) = %v, want %v", tc.name, tc.a, tc.b, got, tc.want)
		}
	}
}

func TestAssignability(t *testing.T) {
	both := NewUnion(ioError, parseError)

	tests := []struct {
		name     string
		src, dst Type
		want     bool
	}{
		// Rule 1: identity.
		{"identical", Int, Int, true},
		{"no numeric promotion", Int, Float, false},
		{"no numeric promotion, other way", Float, Int, false},

		// Rule 2: T -> ?T.
		{"T to ?T", Int, NewNullable(Int), true},
		{"?T to T is not the reverse (N4)", NewNullable(Int), Int, false},

		// Rule 3: nil.
		{"nil to ?T", Nil, NewNullable(Int), true},
		{"nil to a plain type (N3)", Nil, Int, false},
		{"nil to a bare enum (N3)", Nil, ioError, false},

		// Rule 4: union subset.
		{"enum to a union containing it", ioError, both, true},
		{"union to itself", both, both, true},
		{"union to a non-superset", both, ioError, false},
		{"enum to a union not containing it", configError, both, false},

		// Rules 2 and 4 composed. These are the two the spec's own examples
		// require and never stated, and the two the conformance suite exercises.
		{"enum to a nullable union", ioError, NewNullable(both), true},
		{"nullable enum to a nullable union", NewNullable(ioError), NewNullable(both), true},
		{"nullable union to a nullable enum", NewNullable(both), NewNullable(ioError), false},

		// Recovery never cascades.
		{"invalid source", Invalid, Int, true},
		{"invalid destination", Int, Invalid, true},
	}
	for _, tc := range tests {
		if got := Assignable(tc.src, tc.dst); got != tc.want {
			t.Errorf("%s: Assignable(%s, %s) = %v, want %v", tc.name, tc.src, tc.dst, got, tc.want)
		}
	}
}

func TestNullableIsIdempotent(t *testing.T) {
	// Rule N2.
	once := NewNullable(Int)
	twice := NewNullable(once)
	if !Identical(once, twice) {
		t.Errorf("??T must be ?T, got %s", twice)
	}
	if got := twice.String(); got != "?int" {
		t.Errorf("String() = %q, want %q", got, "?int")
	}
}

func TestString(t *testing.T) {
	tests := []struct {
		typ  Type
		want string
	}{
		{Int, "int"},
		{NewNullable(Int), "?int"},
		{&Array{NewNullable(String)}, "array[?string]"},
		{&Map{String, Int}, "map[string, int]"},
		{&Tuple{[]Type{Int, String}}, "tuple[int, string]"},
		{&Matrix{Float}, "matrix[float]"},
		{&Chan{Int}, "chan[int]"},
		{&QReg{4}, "qreg[4]"},
		{QubitType, "qubit"},
		{NewUnion(ioError, parseError), "IOError | ParseError"},
		// A union under ? is parenthesized so the rendering round-trips:
		// `?A | B` would read as a union of `?A` and `B` (rule N1).
		{NewNullable(NewUnion(ioError, parseError)), "?(IOError | ParseError)"},
		{&Func{Params: []Type{Int}, Results: []Type{Float}}, "func(int) -> float"},
		{&Func{Params: []Type{String}, Results: []Type{Int, NewNullable(ioError)}}, "func(string) -> (int, ?IOError)"},
		{&Func{Params: nil, Results: nil}, "func()"},
		{ErrorEnum, "error"},
	}
	for _, tc := range tests {
		if got := tc.typ.String(); got != tc.want {
			t.Errorf("String() = %q, want %q", got, tc.want)
		}
	}
}

func TestLinearity(t *testing.T) {
	linearStruct := &Named{Kind: Struct, Module: "m", Name: "Holder", Fields: []*Field{
		{Name: "q", Type: QubitType},
	}}
	nestedStruct := &Named{Kind: Struct, Module: "m", Name: "Outer", Fields: []*Field{
		{Name: "inner", Type: linearStruct},
	}}
	linearEnum := &Named{Kind: Enum, Module: "m", Name: "Maybe", Variants: []*Variant{
		{Name: "Some", Payload: []Type{QubitType}},
		{Name: "None"},
	}}
	// A struct reachable from itself through a container. IsLinear must
	// terminate rather than recurse forever.
	cyclic := &Named{Kind: Struct, Module: "m", Name: "Node"}
	cyclic.Fields = []*Field{{Name: "kids", Type: &Array{cyclic}}}

	tests := []struct {
		name string
		typ  Type
		want bool
	}{
		{"qubit", QubitType, true},
		{"qreg", &QReg{4}, true},
		{"int", Int, false},
		{"struct with a qubit field", linearStruct, true},
		{"struct transitively containing one", nestedStruct, true},
		{"enum with a linear payload", linearEnum, true},
		{"plain struct", point, false},
		{"plain enum", ioError, false},
		{"array of qubits", &Array{QubitType}, true},
		{"array of ints", &Array{Int}, false},
		{"map with linear values", &Map{String, QubitType}, true},
		{"tuple containing one", &Tuple{[]Type{Int, QubitType}}, true},
		{"cyclic struct terminates", cyclic, false},
	}
	for _, tc := range tests {
		if got := IsLinear(tc.typ); got != tc.want {
			t.Errorf("%s: IsLinear(%s) = %v, want %v", tc.name, tc.typ, got, tc.want)
		}
		if IsUnrestricted(tc.typ) == tc.want {
			t.Errorf("%s: IsUnrestricted must be the complement of IsLinear", tc.name)
		}
	}
}

func TestHasZeroValue(t *testing.T) {
	structOfEnum := &Named{Kind: Struct, Module: "m", Name: "Wrapper", Fields: []*Field{
		{Name: "e", Type: ioError},
	}}

	tests := []struct {
		name string
		typ  Type
		want bool
	}{
		{"int", Int, true},
		{"string", String, true},
		{"array", &Array{Int}, true},
		{"map", &Map{String, Int}, true},
		{"struct of primitives", point, true},
		{"nullable", NewNullable(Int), true},

		{"enum has no privileged variant", ioError, false},
		{"bare union", NewUnion(ioError, parseError), false},
		{"struct field with no zero value", structOfEnum, false},
		{"tuple element with no zero value", &Tuple{[]Type{Int, ioError}}, false},
		{"qubit is linear", QubitType, false},

		// The rule corrected in M0: nil belongs only to nullable types (N3), so
		// a bare chan or func cannot hold it. Write ?chan[int].
		{"chan", &Chan{Int}, false},
		{"func", &Func{Params: nil, Results: nil}, false},
		{"nullable chan", NewNullable(&Chan{Int}), true},
	}
	for _, tc := range tests {
		if got := HasZeroValue(tc.typ); got != tc.want {
			t.Errorf("%s: HasZeroValue(%s) = %v, want %v", tc.name, tc.typ, got, tc.want)
		}
	}
}

func TestFormationConstraints(t *testing.T) {
	structOfStruct := &Named{Kind: Struct, Module: "m", Name: "Nested", Fields: []*Field{
		{Name: "p", Type: point},
	}}

	keys := []struct {
		typ  Type
		want bool
	}{
		{String, true},
		{Int, true},
		{point, true}, // a struct whose fields are all primitive
		{structOfStruct, false},
		{ioError, false}, // an enum is not structurally hashable
		{&Array{Int}, false},
	}
	for _, tc := range keys {
		if got := IsValidMapKey(tc.typ); got != tc.want {
			t.Errorf("IsValidMapKey(%s) = %v, want %v", tc.typ, got, tc.want)
		}
	}

	elems := []struct {
		typ  Type
		want bool
	}{
		{Float, true},
		{Complex, true},
		{Int, false},
		{String, false},
	}
	for _, tc := range elems {
		if got := IsValidMatrixElem(tc.typ); got != tc.want {
			t.Errorf("IsValidMatrixElem(%s) = %v, want %v", tc.typ, got, tc.want)
		}
	}
}

func TestIsErrorSet(t *testing.T) {
	tests := []struct {
		typ  Type
		want bool
	}{
		{ioError, true},
		{NewUnion(ioError, parseError), true},
		{ErrorEnum, true},
		{point, false}, // a struct is not an error set
		{Int, false},
		{NewNullable(ioError), false}, // ?E is the error POSITION; E is the set
	}
	for _, tc := range tests {
		if got := IsErrorSet(tc.typ); got != tc.want {
			t.Errorf("IsErrorSet(%s) = %v, want %v", tc.typ, got, tc.want)
		}
	}
}
