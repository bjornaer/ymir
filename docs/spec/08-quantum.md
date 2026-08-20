# 08 — The Quantum Fragment

> **Status: normative, unimplemented.** This chapter is part of v0.1 of the spec by
> decision D3. No implementation supports it yet, and none is scheduled before Phase 7
> of `/PLAN.md`. It is here because linear typing constrains the design of bindings,
> assignment, calls, and scope exit — it cannot be retrofitted onto a finished type
> checker. Chapter 02 defines the linearity rules; this chapter supplies the types
> that use them.

## Why this is in the language and not a library

Qiskit, Cirq, and Braket are libraries. A library cannot stop you from writing
`q2 = q1` and then operating on both, because Python's type system has no notion of a
value that may be used once. Every quantum framework in wide use therefore detects
no-cloning violations, use-after-measurement, and dropped entangled registers at
runtime, or not at all.

Ymir makes them compile errors. That is the entire argument for Ymir existing.

**Prior art to read before changing this chapter.** Ymir is not first here and should
not pretend to be. **Silq** (ETH Zurich, PLDI 2020) is the closest — its automatic
uncomputation of temporary values is the strongest idea in the space, and Ymir does
**not** currently have it. **Q#** (Microsoft) has the most mature tooling and a
qubit-borrowing discipline worth studying. **Quipper** (Haskell, embedded) established
linear typing for circuits. Anyone extending this chapter should be able to say what
Ymir does that these do not.

## Types

| Type | Multiplicity | Meaning |
|---|---|---|
| `qubit` | **linear** | a single two-level quantum system |
| `qreg[N]` | **linear** | `N` qubits, `N` a compile-time constant |
| `bit` | unrestricted | a classical measurement outcome; an enum, see below |

```ymr
enum bit {
    Zero,
    One,
}
```

`bit` is an enum rather than a `bool` so that `match` exhaustiveness applies to
measurement outcomes — forgetting the `One` case is a compile error.

## Allocation and disposal

```ymr
q := qubit()             # allocates one qubit in state |0>
r := qreg[4]()           # allocates 4 qubits, each in |0>
```

Every allocated qubit **MUST** be consumed exactly once (rule L1). The consuming
operations are:

| Operation | Effect |
|---|---|
| `measure(q) -> bit` | projects onto the computational basis; consumes `q` |
| `reset(q)` | returns `q` to \|0⟩ and releases it; consumes `q` |
| `discard(q)` | releases `q` without measuring; consumes `q` |
| `return q` | transfers the obligation to the caller |
| passing `q` by value | transfers the obligation to the callee |

`discard` exists and is spelled deliberately loudly. Dropping a qubit that is entangled
with another is physically meaningful — it decoheres the partner — so it **MUST** be
explicit. A qubit going out of scope unconsumed is a compile error, never an implicit
discard.

```ymr
func leaky() {
    q := qubit()
}                        # ERROR: linear value 'q' not consumed
```

## Gates

A gate borrows its qubits mutably; it does not consume them. This is what makes
circuits read naturally while keeping single-use verifiable:

```ymr
func h(q: mut qubit)                     # Hadamard
func x(q: mut qubit)                     # Pauli-X
func y(q: mut qubit)
func z(q: mut qubit)
func s(q: mut qubit)
func t(q: mut qubit)
func rx(q: mut qubit, theta: float)      # rotations
func ry(q: mut qubit, theta: float)
func rz(q: mut qubit, theta: float)
func cnot(c: mut qubit, t: mut qubit)    # controlled-NOT
func cz(c: mut qubit, t: mut qubit)
func swap(a: mut qubit, b: mut qubit)
func toffoli(a: mut qubit, b: mut qubit, t: mut qubit)
```

Two `mut` borrows in one call **MUST** refer to distinct qubits. `cnot(q, q)` is a
compile error where aliasing is statically visible, and a panic otherwise.

### User-defined gates

```ymr
gate bell(a: mut qubit, b: mut qubit) {
    h(a)
    cnot(a, b)
}
```

A `gate` is a function restricted to unitary operations: its body **MUST NOT** measure,
allocate, discard, branch on a measurement outcome, or perform I/O. This restriction
is what makes a gate mechanically invertible:

```ymr
adjoint(bell)          # the inverse gate, derived by the compiler
controlled(bell)       # adds a control qubit
```

`adjoint` and `controlled` are compile-time gate combinators and apply **only** to
`gate` declarations, never to ordinary functions. This is Q#'s functor design and it
is the reason `gate` is a distinct declaration form rather than an annotation.

## Measurement

```ymr
q := qubit()
h(q)
outcome := measure(q)     # q is consumed here

match outcome {
    Zero => print("0"),
    One  => print("1"),
}

h(q)                      # ERROR: use of consumed value 'q'
```

Use-after-measurement is caught by rule L1, at compile time. This is the second error
class a library cannot catch.

## No-cloning

```ymr
q1 := qubit()
q2 := q1                  # moves; q1 is now invalid
h(q1)                     # ERROR: use of moved value 'q1'
```

Rule L2 (chapter 02) is the no-cloning theorem expressed as a typing rule. There is no
`copy(q)` and no way to write one — `copy` is defined only on unrestricted types.

## Registers

```ymr
r := qreg[3]()
h(r[0])
cnot(r[0], r[1])
cnot(r[1], r[2])

results := measure_all(r)      # -> array[bit]; consumes r
```

Indexing a `qreg` yields a mutable borrow of one qubit, not a move — the register
retains the obligation. `measure_all` consumes the whole register. Indexing with a
non-constant expression is legal, and the aliasing check for two `mut` borrows then
becomes a runtime check.

## Control flow on measurement

Branching on a measurement outcome is ordinary classical control flow, subject to rule
L4 — every branch must leave the same linear bindings live:

```ymr
m := measure(a)
match m {
    Zero => { },
    One  => x(b),          # b is borrowed, not consumed, in both arms: legal
}
discard(b)
```

```ymr
match m {
    Zero => discard(b),
    One  => { },           # ERROR: 'b' consumed in one arm but not the other
}
```

## Worked example: teleportation

```ymr
module teleport

gate bell(a: mut qubit, b: mut qubit) {
    h(a)
    cnot(a, b)
}

func teleport(payload: qubit) -> qubit {
    alice := qubit()
    bob   := qubit()
    bell(alice, bob)

    cnot(payload, alice)
    h(payload)

    m1 := measure(payload)
    m2 := measure(alice)

    match m2 {
        One  => x(bob),
        Zero => { },
    }
    match m1 {
        One  => z(bob),
        Zero => { },
    }

    return bob
}
```

`payload` and `alice` are consumed by `measure`; `bob` is returned, transferring its
obligation to the caller. The function typechecks precisely because every linear
binding has exactly one fate on every path.

## Execution

The reference backend is a **state-vector simulator** in the VM: a `matrix[complex]`
amplitude vector of length 2^n, with gates applied as sparse index-pair updates. This
is a few hundred lines and needs no external numerical library. Practical limit is
roughly 30 qubits on a laptop.

Real hardware backends are out of scope for v1. The intended shape is that a program
targeting hardware is the same program, with the simulator swapped for a transpiler
emitting the vendor's IR — which is why `gate` bodies are restricted to unitary
operations.

## Not yet designed

- **Automatic uncomputation.** Silq's central contribution. Ymir has no story for
  temporaries, so ancilla management is manual and error-prone. This is the largest
  known gap and the strongest candidate for what Ymir could do better than Q#.
- **Ancilla borrowing.** Q#'s `borrowing` block, for qubits whose state need only be
  restored, not zeroed.
- **`qreg[N]` with runtime `N`.** Currently compile-time constant only.
- **Density matrices / noise models.** Pure states only.
- **Classical/quantum optimization loops** (VQE, QAOA), which are the actual workload
  most users have. Needs the classical side to be pleasant first.
