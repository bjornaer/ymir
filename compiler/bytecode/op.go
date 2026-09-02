// Package bytecode defines Ymir's instruction set and compiles a checked
// syntax tree into it.
//
// The machine is a stack machine. Registers would be faster and are harder to
// compile to and to read; Phase 3 exists to pin down semantics, and a stack
// makes both the compiler and a disassembly listing obvious. Nothing here
// forecloses a register pass later, because the bytecode is not a distributed
// artifact — it is produced and consumed in the same process.
//
// Arithmetic opcodes are **typed**: AddInt and AddFloat, not one polymorphic
// Add. The checker has already proved the operand types and recorded them in
// check.Info, so emitting a typed opcode spends information the compiler
// already has instead of re-deriving it at runtime. It also puts resolved
// question R5's overflow trap exactly where it belongs — on the int opcodes
// only, with float left to IEEE.
//
// This package does not import vm. The dependency runs the other way.
package bytecode

// Op is an instruction opcode.
type Op uint8

const (
	// OpNop does nothing. Never emitted; it makes a zero-valued Instr
	// harmless rather than an accidental Const 0.
	OpNop Op = iota

	// --- constants and literals. A is a constant index for OpConst.
	OpConst
	OpNil
	OpTrue
	OpFalse

	// --- stack
	OpPop

	// --- variables. A is a slot for locals, an index for globals.
	OpGetLocal
	OpSetLocal
	OpGetGlobal
	OpSetGlobal

	// --- int arithmetic. Each traps on overflow (R5); OpDivInt and OpModInt
	// also trap on a zero divisor.
	OpAddInt
	OpSubInt
	OpMulInt
	OpDivInt
	OpModInt
	OpPowInt
	OpNegInt

	// --- float arithmetic. IEEE throughout: no trap, and division by zero
	// yields an infinity (chapter 04 §Operand typing).
	OpAddFloat
	OpSubFloat
	OpMulFloat
	OpDivFloat
	OpPowFloat
	OpNegFloat

	// --- string
	OpConcat

	// --- comparison. Ordered comparison is typed for the same reason
	// arithmetic is; equality is not, because it is defined on every
	// unrestricted type and dispatches on the value's kind.
	OpEq
	OpNe
	OpLtInt
	OpLeInt
	OpGtInt
	OpGeInt
	OpLtFloat
	OpLeFloat
	OpGtFloat
	OpGeFloat
	OpLtString
	OpLeString
	OpGtString
	OpGeString

	// --- logic. && and || short-circuit, which the compiler lowers to jumps;
	// OpNot is the only logical instruction.
	OpNot

	// --- control flow. A is an absolute pc within the same chunk.
	OpJump
	OpJumpIfFalse
	OpJumpIfTrue

	// --- calls. A is an index into Program.Funcs. Arity is fixed at compile
	// time and lives on the callee, so it is not encoded here. Calling a
	// function *value* needs an operand for the argument count and arrives
	// with closures in Phase 4.
	OpCall
	OpReturn

	// --- builtins. A is the argument count, because print is variadic
	// (chapter 04 calls that a wart to be removed once generics land).
	OpPrint
	OpPanic

	// OpHalt ends execution. Emitted at the end of the entry sequence.
	OpHalt
)

// opNames is indexed by Op. A missing entry is a bug, not a fallback, so
// Op.String reports the number rather than inventing a name.
var opNames = [...]string{
	OpNop:         "Nop",
	OpConst:       "Const",
	OpNil:         "Nil",
	OpTrue:        "True",
	OpFalse:       "False",
	OpPop:         "Pop",
	OpGetLocal:    "GetLocal",
	OpSetLocal:    "SetLocal",
	OpGetGlobal:   "GetGlobal",
	OpSetGlobal:   "SetGlobal",
	OpAddInt:      "AddInt",
	OpSubInt:      "SubInt",
	OpMulInt:      "MulInt",
	OpDivInt:      "DivInt",
	OpModInt:      "ModInt",
	OpPowInt:      "PowInt",
	OpNegInt:      "NegInt",
	OpAddFloat:    "AddFloat",
	OpSubFloat:    "SubFloat",
	OpMulFloat:    "MulFloat",
	OpDivFloat:    "DivFloat",
	OpPowFloat:    "PowFloat",
	OpNegFloat:    "NegFloat",
	OpConcat:      "Concat",
	OpEq:          "Eq",
	OpNe:          "Ne",
	OpLtInt:       "LtInt",
	OpLeInt:       "LeInt",
	OpGtInt:       "GtInt",
	OpGeInt:       "GeInt",
	OpLtFloat:     "LtFloat",
	OpLeFloat:     "LeFloat",
	OpGtFloat:     "GtFloat",
	OpGeFloat:     "GeFloat",
	OpLtString:    "LtString",
	OpLeString:    "LeString",
	OpGtString:    "GtString",
	OpGeString:    "GeString",
	OpNot:         "Not",
	OpJump:        "Jump",
	OpJumpIfFalse: "JumpIfFalse",
	OpJumpIfTrue:  "JumpIfTrue",
	OpCall:        "Call",
	OpReturn:      "Return",
	OpPrint:       "Print",
	OpPanic:       "Panic",
	OpHalt:        "Halt",
}

func (o Op) String() string {
	if int(o) < len(opNames) && opNames[o] != "" {
		return opNames[o]
	}
	return "Op(" + itoa(int(o)) + ")"
}

// HasOperand reports whether an opcode reads its A field. Used by the
// disassembler, and by tests that assert an encoding carries no junk.
func (o Op) HasOperand() bool {
	switch o {
	case OpConst, OpGetLocal, OpSetLocal, OpGetGlobal, OpSetGlobal,
		OpJump, OpJumpIfFalse, OpJumpIfTrue, OpCall, OpPrint:
		return true
	}
	return false
}

// IsJump reports whether A is a program counter rather than an index. The
// compiler patches these after the target is known.
func (o Op) IsJump() bool {
	return o == OpJump || o == OpJumpIfFalse || o == OpJumpIfTrue
}
