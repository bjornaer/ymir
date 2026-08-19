# 00 — Overview

## What Ymir is

Ymir is a statically typed, imperative, compiled language with algebraic data types,
Go-style concurrency, and a linearly typed quantum fragment. It targets a bytecode
virtual machine distributed as a single static binary.

The intended user is someone writing hybrid classical/quantum programs who wants the
compiler to catch quantum-mechanical errors — cloning a qubit, using a measured
qubit, dropping an entangled register — before the program runs. No mainstream
quantum framework can do this, because they are libraries, and a library cannot
enforce linearity in its host language's type system.

## Goals

1. **Correctness is checkable.** A program that typechecks does not violate
   no-cloning, does not use a consumed qubit, and does not ignore an error.
2. **One implementation, one semantics.** Exactly one execution engine is normative.
   Every divergence between engines is a bug class we are choosing not to have.
3. **Trivial to install and fast to compile.** `ymir` is one static binary with no
   runtime dependencies, no toolchain to install, no linker required. Compilation is
   measured in milliseconds.
4. **Everything normative is executable.** Every rule in this spec has a
   conformance case that asserts it.

## Non-goals

- **Peak native performance.** A bytecode VM is 10–50× slower than optimized native
  code. That is an accepted cost. An AOT backend is roadmapped, never a prerequisite.
- **Python compatibility.** Ymir is not Python with braces. Ymir values are Ymir
  values, not host-language values.
- **Being a general-purpose systems language.** No manual memory management, no
  pointers, no unsafe escape hatch in v1.
- **Object orientation.** No classes, no inheritance, no method resolution order.

## Locked decisions

These four are settled. Reopening any of them means rewriting large parts of the spec,
so they are recorded here with their reasoning.

### D1 — Errors are values, not exceptions

Functions signal recoverable failure by returning it. There is no exception type, no
`except`/`finally`, and no `throw`.

```ymr
enum DivError { ByZero, }

func divide(a: int, b: int) -> (int, DivError) {
    if b == 0 {
        return 0, DivError.ByZero
    }
    return a / b, nil
}

result, err := divide(10, 0)
if err != nil {
    match err {
        ByZero => print("division by zero"),
    }
    return
}
```

Error types compose by union, and `try` propagates:

```ymr
func loadConfig(path: string) -> (Config, IOError | ParseError) {
    data := try readFile(path)     # readFile fails with IOError
    cfg  := try parse(data)        # parse fails with ParseError
    return cfg, nil
}
```

*Why:* the VM needs no unwinding machinery; callers cannot silently skip a failure
path; and — decisively — exception unwinding through a scope holding a live qubit is
a question with no good answer. Linear types and stack unwinding are hostile to each
other. See [06-errors.md](06-errors.md).

*Cost, stated plainly:* the legacy implementation's exception subsystem and roughly
350 lines of passing tests are discarded.

The type of the error position is an **error set** — a single enum or a union of enums,
with subset assignability — and `try` propagates one. Both are specified in
[06-errors.md](06-errors.md); the reasoning is under *Resolved questions* below.

### D2 — Data is structs and enums, destructured by `match`

No classes and no inheritance. Product types are `struct`; sum types are `enum` with
payloads. `match` destructures them and **MUST** be exhaustive.

```ymr
enum Shape {
    Circle(float),
    Rect(float, float),
    Point,
}

func area(s: Shape) -> float {
    match s {
        Circle(r)    => return 3.14159 * r * r,
        Rect(w, h)   => return w * h,
        Point        => return 0.0,
    }
}
```

*Why:* exhaustiveness checking is the mechanism that makes measurement outcomes and
error cases impossible to forget. It also lowers to a jump table trivially, where a
method resolution order does not.

### D3 — The quantum fragment is normative now, implemented later

[Chapter 08](08-quantum.md) is part of v0.1 of this spec even though no
implementation will support it for months. Linear typing is not a feature that can be
bolted onto a finished type checker — it constrains how bindings, assignment, calls,
and scope exit are all defined. The checker is built to accommodate it from the first
commit, and the classical language is validated against it.

Chapter 08 is marked *unimplemented*. That is a schedule statement, not a
tentativeness statement.

### D4 — Bytecode VM in Go, single binary

The normative implementation compiles source to Ymir bytecode and executes it on a VM
written in Go.

*Why Go over LLVM:* LLVM requires users to have a toolchain and linker, optimization
passes dominate compile time, and native codegen is per-architecture work. All three
directly contradict Goal 3. *Why Go over Rust:* goroutines and channels host Ymir's
concurrency model 1:1 instead of emulating it, and Go's garbage collector is Ymir's
garbage collector — writing a GC is the single hardest part of a VM, and this deletes
that work item entirely.

*Deliberately deferred:* a native AOT backend, added only after the VM has frozen the
semantics, and gated on passing the identical conformance suite. Two backends where
neither is authoritative is precisely what produced the legacy implementation's
entry-point divergence.

## Resolved questions

### R1 — How do user types occupy the `error` position? → **error sets** (2026-08-20)

D1 gave `error` a normative role, D2 removed interfaces, and so nothing let a
user-defined type *be* an error. The first draft made `error` a concrete
`{message, kind}` struct with richer failures modeled as module-local enums. That
design does not work: a function calling two fallible things from different modules has
no type to name for its own error position, and the draft's own example was incoherent
— its `ParseError` enum had no success variant, so a successful `parseInt` had nothing
to return.

**Resolution: error sets.** The error position holds a single enum or a union of enums
(`IOError | ParseError`), with assignability by subset. A function's error set is the
union of its callees', and returning a callee's error propagates without wrapping.

*Why over interfaces (Go's answer):* recovering the concrete type from an interface
needs a downcast, which needs runtime type information — and Ymir has none. Without the
downcast you only ever get a string back, which is where the rejected struct design
already was. Error sets stay fully static, reusing the tagged-union representation
enums already require: no vtables, no dynamic dispatch, no RTTI.

*Why over keeping it closed:* stringly-typed module boundaries, permanently.

*Prior art:* Zig's error sets, in a language with near-identical constraints — small
compiler, no interfaces, no runtime type information. Ymir's variant unions
payload-carrying enums rather than payload-free error values, which is more expressive
and costs qualified patterns in `match`.

*Cost, stated plainly:* union assignability and exhaustiveness-over-unions are the two
hardest things in the type checker — harder than linearity. This moves Phase 2.

### R2 — Error propagation → **`try`** (2026-08-20)

`data := try readFile(path)` returns early with the error if non-nil. Adopted with R1,
because the checker work overlaps and because R1 without it is most of the cost for
less of the benefit. Go's verbosity reputation is overwhelmingly about lacking this
operator, not about its error interface.

## Open questions

Unresolved. Do not treat any of these as decided.

### Q2 — Is `Result[T, E]` in the stdlib alongside `(T, error)`?

Largely mooted by R1 — error sets cover what `Result` was wanted for. Kept open only
in case a chaining/combinator API turns out to be wanted. Current lean: no. Requires
generics (Q3).

### Q3 — Generics: in v1, or after?

`array[T]` and `map[K, V]` are built-in generic types. Whether *users* can write
`func map(xs, f)` generically is unanswered. Monomorphizing in a bytecode compiler is
straightforward; the type checker cost is real, and R1 already added to it. Deferring
means the stdlib is written against concrete types and later needs revision.

### Q4 — Does `main` return anything?

Currently `func main()`, exit code 0 on normal return, non-zero on panic. Should it be
`func main() -> int`, or `-> (error)` so `try` works in it? R1 makes the last option
more attractive than it was. The legacy CLI's habit of always exiting 0 is the bug this
needs to foreclose.

### Q5 — Integer semantics

`int` is 64-bit signed. Overflow behavior is **not decided**: wrap, trap, or saturate.
Trapping is safest and matches "no undefined behavior"; it costs a branch per
arithmetic op in the VM. Must be decided before the VM's arithmetic opcodes.

### Q6 — Data races on shared `array` / `map` between tasks

Currently *unspecified* — the one hole in "no undefined behavior in safe code". Options:
a race detector in the VM (cheap for a bytecode interpreter, unlike native code), or
making those types non-sendable so sharing is impossible. **Blocks Phase 5.**

### Q7 — Structured concurrency instead of Go's detached `spawn`?

`main` returning does not wait for spawned tasks. Go's choice here is widely regarded as
its worst concurrency decision.

### Q8 — Immutability by default for locals?

Bindings are currently mutable by default with no `let`/`mut` distinction.
Immutability-by-default is the better default but changes every example in this spec.

### Q10 — Should error-position nullability be written into the type?

R1 makes nullability **positional**: a union or enum in the final component of a result
type is nullable, the same type elsewhere is not. This is a wart. The alternative is an
explicit marker — `-> (Config, ?(IOError | ParseError))` — which is honest but noisier
on every fallible signature. Decide before Phase 2 finalizes the type representation.

### Q11 — Should error sets be inferred?

v1 requires sets to be written explicitly. Zig infers them (`!T`), which removes the
annotation burden but makes a function's failure modes invisible at its signature and
turns any change to a callee into a silent change in the caller's public type. Inference
is additive later; explicit-first is the reversible choice.

## Relationship to the legacy implementation

`/ymir-legacy-py/` holds the frozen Python implementation. It is a *reference for what
the language used to do*, not an authority on what it should do. Its known defects are
catalogued in `/ymir-legacy-py/README.md`; several conformance cases exist specifically
to assert the opposite of what it does.
