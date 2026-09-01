package types

// The universe scope: the names every Ymir program starts with, before it
// imports anything. Chapter 01 §Keywords ("type names are not keywords") and
// chapter 03 §Scope level 5.
//
// compiler/check turns these maps into a real Scope. They live here because
// they are types, and because the checker should not be the place that decides
// what `int` means.

// ErrorEnum is the predeclared `enum error { Msg(string) }`.
//
// Chapter 06 §The predeclared error: `Error(s)` is sugar for `error.Msg(s)`.
// It is an ordinary enum, so it participates in unions like any other and
// ?(IOError | error) is a valid error position. There is no privileged
// "any error" type.
var ErrorEnum = &Named{
	Kind: Enum,
	Name: "error",
	Variants: []*Variant{
		{Name: "Msg", Payload: []Type{String}},
	},
}

// Predeclared maps the type names bound in universe scope to their types.
//
// The parameterized built-ins — array, map, tuple, matrix, chan, qreg — are not
// here: they are not types until applied to arguments, so the checker resolves
// them from the *ast.GenericType spelling instead. GenericNames lists them.
var Predeclared = map[string]Type{
	"int":     Int,
	"float":   Float,
	"complex": Complex,
	"bool":    Bool,
	"string":  String,
	"error":   ErrorEnum,
	"qubit":   QubitType,
}

// GenericNames are the predeclared parameterized type constructors, mapped to
// the number of type arguments each takes. qreg's argument is a compile-time
// integer constant rather than a type.
//
// A user cannot declare one of these until Q3 is answered; the parser accepts
// any arity, so the checker enforces these numbers.
var GenericNames = map[string]int{
	"array":  1,
	"map":    2,
	"matrix": 1,
	"chan":   1,
	"qreg":   1,
	"tuple":  -1, // variadic
}

// Builtins are the predeclared functions.
//
// Most are polymorphic in a way no Func can express before Q3, so the checker
// types each call ad hoc rather than through Assignable. print is variadic,
// which chapter 04 calls a wart to be removed once generics land.
var Builtins = map[string]*Builtin{
	"print":     {Name: "print"},
	"len":       {Name: "len"},
	"append":    {Name: "append"},
	"copy":      {Name: "copy"},
	"delete":    {Name: "delete"},
	"chars":     {Name: "chars"},
	"range":     {Name: "range"},
	"enumerate": {Name: "enumerate"},
	"str":       {Name: "str"},
	"panic":     {Name: "panic"},
	"Error":     {Name: "Error"},
	"make_chan": {Name: "make_chan"},
	"close":     {Name: "close"},

	// The explicit numeric conversions of chapter 02 §Numeric conversion.
	// float, int and complex are also type names, and the checker tells the
	// two apart by position: a type in a type, a conversion in a call.
	"float":   {Name: "float"},
	"int":     {Name: "int"},
	"complex": {Name: "complex"},
	"real":    {Name: "real"},
	"imag":    {Name: "imag"},

	// Quantum. Declared now per decision D3, rejected by the checker until
	// Phase 7 so that a program cannot construct a linear value yet. The
	// allocator `qubit()` shares its name with the type, like the numeric
	// conversions above, so it is not listed separately.
	"measure":     {Name: "measure"},
	"measure_all": {Name: "measure_all"},
	"reset":       {Name: "reset"},
	"discard":     {Name: "discard"},
}
