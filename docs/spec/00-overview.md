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

Functions signal recoverable failure by returning it. There is no `try`, `except`,
`finally`, `throw`, or user-defined exception type.

```ymr
func divide(a: int, b: int) -> (int, error) {
    if b == 0 {
        return 0, Error("division by zero")
    }
    return a / b, nil
}

result, err := divide(10, 0)
if err != nil {
    print(err.message)
    return
}
```

*Why:* the VM needs no unwinding machinery; callers cannot silently skip a failure
path; and — decisively — exception unwinding through a scope holding a live qubit is
a question with no good answer. Linear types and stack unwinding are hostile to each
other. See [06-errors.md](06-errors.md).

*Cost, stated plainly:* the legacy implementation's exception subsystem and roughly
350 lines of passing tests are discarded.

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

## Open questions

Unresolved. Do not treat any of these as decided.

### Q1 — How do user-defined types satisfy `error`? *(highest priority)*

D1 gives `error` a normative role but D2 removed interfaces, so there is no mechanism
for a user type to *be* an error. Chapter 06 currently specs `error` as a built-in
struct `{ message: string, kind: string }`, with richer failures modeled as
module-local enums returned in the error position (`-> (int, DivError)`).

That works, but it means there is no single type that holds "any error", so error
propagation across module boundaries has to re-wrap. The alternatives:

- **(a)** Add minimal structural interfaces, used only for `error`. Proven (this is
  Go). Contradicts the spirit of D2.
- **(b)** Make `error` a built-in open enum that user enums can be lifted into.
  Coherent with D2; requires designing subtyping between enums.
- **(c)** Keep it closed as currently spec'd, and accept re-wrapping at boundaries.

**This must be answered before Phase 2 of `/PLAN.md` (type checker).**

### Q2 — Is `Result[T, E]` in the stdlib alongside `(T, error)`?

D2 makes `Result[T, E]` natural and it chains well. But two ways to express failure
is the thing D1 was chosen to avoid. Current lean: normative `(T, error)`; `Result`
exists only if a concrete need appears. Requires generics (Q3).

### Q3 — Generics: in v1, or after?

`array[T]` and `map[K, V]` are built-in generic types. Whether *users* can write
`func map[T, U](xs: array[T], f: func(T) -> U) -> array[U]` is unanswered. Monomorphizing
in a bytecode compiler is straightforward; the type checker cost is real. Deferring
means the stdlib is written against concrete types and later needs revision.

### Q4 — Does `main` return anything?

Currently spec'd as `func main()`, exit code 0 on normal return, non-zero on panic.
Should it be `func main() -> int` or `func main() -> error`? The legacy CLI's habit of
always exiting 0 is the bug this needs to foreclose.

### Q5 — Integer semantics

`int` is spec'd as 64-bit signed. Overflow behavior is **not yet decided**: wrap, trap,
or saturate. Trapping is safest and matches "no undefined behavior"; it costs a branch
per arithmetic op in the VM. Must be decided before the VM's arithmetic opcodes.

## Relationship to the legacy implementation

`/ymir-legacy-py/` holds the frozen Python implementation. It is a *reference for what
the language used to do*, not an authority on what it should do. Its known defects are
catalogued in `/ymir-legacy-py/README.md`; several conformance cases exist specifically
to assert the opposite of what it does.
