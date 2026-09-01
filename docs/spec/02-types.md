# 02 — Type System

Ymir is statically typed with local inference. Every expression has a type known at
compile time. There is no dynamic dispatch and no runtime type information in v1.

## Type classification

Every type has exactly one **multiplicity**, which governs how values of that type may
be used:

| Multiplicity | Rule | Types |
|---|---|---|
| **Unrestricted** | May be copied and discarded freely | all classical types |
| **Linear** | **MUST** be consumed exactly once | `qubit`, `qreg[N]`, any struct transitively containing one, and any enum with a linear payload |

A **container** of a linear type is ill-formed: `array[qubit]`, `map[K, qubit]`,
`chan[qubit]`, `tuple[qubit, int]` and `matrix` of a linear type are all rejected where
the type is written. Rule L1 requires proving that each linear value is consumed exactly
once, and a container's length is a runtime value, so no such proof exists. `qreg[N]` is
the collection-of-qubits type, with `N` a compile-time constant. A struct **MAY** hold a
linear field, because its shape is static. *(Resolved question R8.)*

Linearity is defined here rather than in chapter 08 because it is a property of the
type system, not of the quantum fragment. Chapter 08 supplies the only linear types in
v1; the rules below are what the checker is built around from day one (decision D3).

## Primitive types

| Type | Description | Zero value |
|---|---|---|
| `int` | 64-bit signed integer | `0` |
| `float` | IEEE-754 binary64 | `0.0` |
| `complex` | pair of binary64, real and imaginary | `0.0 + 0.0i` |
| `bool` | `true` or `false` | `false` |
| `string` | immutable UTF-8 byte sequence | `""` |

`error` is **not** a primitive. It is a predeclared *enum*, `enum error { Msg(string) }`,
defined in [chapter 06](06-errors.md#the-predeclared-error). Like every enum it has no
zero value and no `nil`; the nullable form is `?error`. *(An earlier draft listed it here
as a primitive with zero value `nil`, which contradicted both §Enums below and chapter
06.)*

There is no `any` type. *(Legacy had one; it defeated the checker wherever it appeared
and every use of it in the legacy stdlib was masking a missing feature.)*

### Integer overflow

Arithmetic on `int` that overflows the signed 64-bit range **MUST** panic. It **MUST
NOT** wrap and **MUST NOT** saturate — both produce a silently wrong answer, which Goal 1
of [chapter 00](00-overview.md) exists to exclude.

Overflow while evaluating a **constant expression** is a compile error, not a panic, on
the same grounds as constant division by zero ([chapter 04](04-expressions.md#constant-expressions)).

```ymr
const BIG: int = 9223372036854775807 + 1   # ERROR: constant expression overflows int
```

*(Resolved question R5. The cost is a branch per arithmetic opcode in the VM.)*

### Complex literals

A **complex literal** is a numeric literal, then `+` or `-`, then an imaginary literal:

```ymr
0.0 + 0.0i     # the zero value of complex
1.0 + 2.0i
1 - 3i
2.0i           # a bare imaginary literal is also a complex
```

Both parts **MUST** be literals. `x + 2.0i` where `x` is a `float` binding is a type
error, since §Operand typing requires identical operands and there is no implicit
conversion. *(Resolved question R7. This is folded by the parser rather than lexed as one
token, so it does not depend on whitespace.)*

### Numeric conversion

There is **no** implicit numeric conversion. `int` and `float` do not mix in
arithmetic; `1 + 2.0` is a type error. Conversion is explicit and total:

```ymr
float(x)      # int -> float, exact for |x| < 2^53
int(x)        # float -> int, truncates toward zero
complex(x)    # int or float -> complex, zero imaginary part
real(z)       # complex -> float
imag(z)       # complex -> float
```

`int(x)` where `x` is NaN, infinite, or out of `int` range is a **panic**, not a
wrapped value. This is a deliberate cost.

### `string`

`string` is an immutable sequence of bytes that is **required** to be valid UTF-8.
Indexing `s[i]` yields the `i`th *byte* as an `int`; `chars(s)` yields
`array[int]` of Unicode scalar values. `len(s)` is the byte length. Concatenation is
`+`. Strings are compared by byte sequence.

## Composite types

### `array[T]`

Dynamically sized, homogeneous, mutable, reference semantics. Assigning an array
binds a second reference to the same underlying storage; `copy(a)` makes it distinct.

```ymr
var xs: array[int] = [1, 2, 3]
xs[0] = 99
len(xs)          # 3
append(xs, 4)    # mutates xs in place
```

Indexing out of range is a **panic**. There is no unchecked variant in v1.
*(Legacy's LLVM backend returned zero for an out-of-bounds read. Case
`array/bounds_panic` asserts a panic.)*

### `map[K, V]`

Hash map. `K` **MUST** be a primitive type or a struct whose fields are all primitive
(structurally hashable). Reference semantics, like `array`.

```ymr
var m: map[string, int] = {"a": 1, "b": 2}
v, ok := m["a"]      # two-value form; ok is false if absent
m["c"] = 3
delete(m, "a")
```

Single-value indexing `m[k]` on an absent key is a **panic**. The two-value form is
the safe accessor. Iteration order is **unspecified** and implementations SHOULD
randomize it.

*Syntax change from legacy:* `map[K, V]`, not Go's `map[K]V`. Legacy documented
`map[key_type]value_type` but never implemented it.

### `tuple[T1, T2, ...]`

Fixed-length, heterogeneous, immutable, value semantics. Accessed positionally.

```ymr
var p: tuple[int, string] = (1, "one")
p.0     # 1
p.1     # "one"
```

Multiple return values (chapter 03) are tuples with dedicated destructuring syntax.

### `matrix[T]`

Two-dimensional, rectangular, `T` ∈ {`float`, `complex`}. `@` is matrix
multiplication; `+`, `-`, `*` are element-wise.

```ymr
var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
var b: matrix[complex] = [[1.0+0.0i, 0.0+0.0i], [0.0+0.0i, 1.0+0.0i]]
c := a @ a
```

`matrix[complex]` is what quantum state vectors and gate matrices are built from.
Dimension mismatch in `@` is a compile error where both operands' shapes are known
statically, and a panic otherwise.

### `chan[T]`

See chapter 07.

### `func(...) -> ...`

Function types are first class. Functions are values; they may be stored, passed, and
returned.

```ymr
var op: func(int, int) -> int = add
result := op(2, 3)

func apply(xs: array[int], f: func(int) -> int) -> array[int] { ... }
```

*This is new.* The legacy AST stored a call's callee as a bare `string`, which made
function values structurally impossible to express. Closures capture by reference; see
chapter 03.

## Structs

Product types. Value semantics: assignment copies, unless the struct is linear
(then assignment *moves* — see below).

```ymr
struct Point {
    x: float,
    y: float,
}

var p := Point{x: 1.0, y: 2.0}
p.x = 3.0
```

Field initialization **MUST** be exhaustive and by name. There is no positional struct
literal and no partial initialization defaulting to zero — a struct literal names every
field. This is verbose and deliberate: adding a field to a struct should break every
construction site.

Structs may declare methods:

```ymr
func (p: Point) magnitude() -> float {
    return sqrt(p.x * p.x + p.y * p.y)
}

func (p: mut Point) scale(k: float) {
    p.x = p.x * k
    p.y = p.y * k
}
```

A receiver marked `mut` receives a mutable reference; otherwise it receives a copy.
Methods are not virtual — the receiver's type is statically known at every call site.

## Enums

Sum types. Variants **MAY** carry positional payloads.

```ymr
enum Shape {
    Circle(float),
    Rect(float, float),
    Point,
}

enum Outcome {
    Zero,
    One,
}
```

Construction names the variant; where ambiguous, qualify it:

```ymr
var s: Shape = Circle(2.0)
var t := Shape.Rect(3.0, 4.0)
```

**Ambiguous** means the bare name belongs to more than one enum declared in the
module. Writing it unqualified is then a compile error naming the candidates; it is
not resolved by the expected type. Resolution order is: an ordinary binding in scope
wins over a variant, so a local named `Circle` shadows `Shape.Circle` rather than
colliding with it. *(Previously "where ambiguous" was left undefined.)*

Enum values are inspected **only** by `match` (chapter 05). There is no field access,
no cast, and no "is this variant" predicate. `match` **MUST** be exhaustive, which is
the mechanism that makes a forgotten measurement outcome or error case a compile error.

Enums are unrestricted unless a payload is linear, in which case the enum is linear.

An enum has **no zero value** and **no `nil`**. `var s: Shape` without an initializer
is a compile error, and `s == nil` is a type error. This is what keeps `match` on an
ordinary enum free of a `nil` arm.

## Union types

A **union** is written `A | B` and denotes a value that is one of its members.

```ymr
IOError | ParseError
```

Members **MUST** all be enum types. `int | string` is not a type. Ymir has no general
union types; this restriction keeps unions implementable with the tagged-union
representation enums already need.

Unions are **sets**: `A | B` and `B | A` are the same type, `A | A` is `A`, and
`(A | B) | C` is `A | B | C`. Two unions are identical when they have the same members.
A single enum `A` is the one-member union `A`.

**Subtyping.** A union `S` is assignable to a union `T` when **S ⊆ T**:

```ymr
var e: IOError | ParseError = someIOError    # legal
var f: IOError = someUnionValue              # ERROR: not a subset
```

This subset rule is the **only** subtyping relation in the language. Everywhere else,
assignability requires identical types (§Assignability below). It exists so a
function's error set can be the union of its callees' without manual wrapping
(chapter 06).

## Nullable types

`?T` is the type of a value that is either a `T` or **`nil`**.

```ymr
var found: ?int = nil
func lookup(k: string) -> ?string
func describe(e: ?IOError, tags: array[?string]) -> ?string
```

`?` is a **general type former**, not a rule about position. It may appear anywhere a
type may: parameters, results, fields, collection elements, and variables. Nullability
is always written, never inferred from where a type sits.

*This replaced an earlier design in which the last component of a result type was
implicitly nullable and the same type elsewhere was not.* One type name meaning two
things depending on position is exactly the kind of rule that is invisible at a use
site, and there is no reason a parameter or a field should be barred from being absent.

### Rules

**N1 — `?` takes a base type or a parenthesized type.** Write `?IOError` or
`?(IOError | ParseError)`. `?A | B` is not accepted, so no precedence relation between
`?` and `|` needs to exist.

**N2 — `?` is idempotent.** `??T` is `?T`.

**N3 — `nil` belongs only to nullable types.** `nil` is assignable to any `?T` and is
its zero value. `int`, `string`, `struct`, `enum`, and bare unions have no `nil` and
**MUST NOT** be compared to it. This is what keeps `match` on an ordinary enum free of
a `nil` arm:

```ymr
match outcome {          # outcome: bit
    Zero => ...,
    One  => ...,         # complete; `bit` is never absent
}
```

**N4 — `T` is assignable to `?T`.** Not the reverse. A `?T` **MUST** be narrowed before
it is used as a `T`; `x + 1` where `x: ?int` is a type error.

**N5 — `?` requires an unrestricted type.** `?qubit` is rejected: a linear value that
may be absent cannot be consumed exactly once, and every branch would have to prove
which case it was in (rule L4).

**N6 — Narrowing.** Comparing a nullable binding against `nil` narrows it in the
corresponding branch:

```ymr
v := lookup(key)         # v: ?string
if v != nil {
    print(v + "!")       # v: string here
}
```

Narrowing applies when an `if` condition is exactly `x != nil` or `x == nil` for a
binding `x` of nullable type. Both branches are narrowed, each to what the condition
proves about it:

| Condition | `then` branch | `else` branch |
|---|---|---|
| `x != nil` | `x: T` | `x: ?T`, known `nil` |
| `x == nil` | `x: ?T`, known `nil` | `x: T` |

`x` is **not** narrowed after the `if`, in either direction.

It is deliberately minimal. The condition **MUST** be exactly that comparison on a
*binding* — not a field, not an index, not an element of a `&&` or `||` chain, and not
the result of a call. It is not general flow typing, and it does not survive
reassignment of `x` inside the branch. `match` on a narrowed `?Enum` needs no `nil` arm;
on an un-narrowed one it requires exactly one.

Nullable types make absence a property the checker tracks rather than a runtime
surprise, which is the same argument as linear types for qubits and exhaustive `match`
for enums.

## Linearity rules

These apply to any value whose type is linear. In v1 that is `qubit`, `qreg[N]`, and
aggregates containing them.

**L1 — Exactly once.** Every linear binding **MUST** be consumed exactly once on
every path from its introduction to the end of its scope. Zero uses is an error
(*unused linear value*); two uses is an error (*linear value used twice*).

**L2 — Assignment moves.** Binding a linear value to a new name invalidates the old
name. Reading a moved-from binding is a compile error.

```ymr
q2 := q1        # q1 is moved; q1 is now invalid
h(q1)           # ERROR: use of moved value 'q1'
```

This is the no-cloning theorem, enforced by the type checker.

**L3 — Passing moves.** Passing a linear value as an argument consumes it, unless the
parameter is declared `mut`, which borrows it for the call's duration.

**L4 — Branches must agree.** Every branch of an `if` or `match` **MUST** leave the
same set of linear bindings live. Consuming a qubit in one arm but not another is an
error.

**L5 — No capture.** A closure **MUST NOT** capture a linear value. A `spawn`'d call
**MUST NOT** be passed one. Both would make single-use unverifiable.

**L6 — Loops.** A `while` or `for` body **MUST NOT** consume a linear binding declared
outside it, since the body runs an unknown number of times.

The consuming operations for `qubit` are `measure`, `reset`, `discard`, returning it,
or passing it by value. See chapter 08.

## Type inference

Inference is **local**. There is no global or Hindley-Milner inference; a function's
signature is always fully annotated.

**Inferred:** the type of a `var` or `:=` binding, from its initializer.

```ymr
x := 42                   # int
y := 3.14                 # float
xs := [1, 2, 3]           # array[int]
p := Point{x: 1.0, y: 2.0}   # Point
```

**MUST be annotated:** every function parameter, every function return type, every
struct field, every enum payload, and any `var` with no initializer.

```ymr
var count: int              # no initializer, annotation required
func f(a: int) -> float     # always annotated
```

An empty collection literal has no inferable element type and **MUST** be annotated:

```ymr
var xs: array[int] = []     # required
ys := []                    # ERROR: cannot infer element type
```

## Assignability

A value of type `S` is assignable to a location of type `T` only if `S` and `T` are
**identical**, with two exceptions: unions, where `S ⊆ T` suffices (§Union types), and
nullables, where `T` is assignable to `?T` (§Nullable types). There is no other
subtyping, no coercion, and no numeric promotion. Type
identity is structural for `array`, `map`, `tuple`, `chan`, `func`, and `matrix`; it is
nominal for `struct` and `enum` — two structs with identical fields but different names
are different types.

**The two exceptions compose.** Assignability is the smallest relation satisfying all
four of these:

1. `S` is assignable to `T` when they are identical.
2. `S` is assignable to `?T` when `S` is assignable to `T`.
3. `nil` is assignable to any `?T`.
4. A union `S` is assignable to a union `T` when `S ⊆ T`. A bare enum is the one-member
   union of itself, so this covers `IOError` → `IOError | ParseError`.

Rules 2 and 4 together are what make `var e: ?(IOError | ParseError) = someIOError`
legal, and what lets `return 0, err` typecheck where `err: ?IOError` and the declared
error position is `?(IOError | ParseError)`. *(Stated because it was previously only
implied by the examples.)*

## Zero values and definite assignment

`var x: T` without an initializer binds the zero value of `T` where one exists (table
above, plus: `array` and `map` are empty, and `struct` is field-wise zero).

Types with **no** zero value: `enum` and bare unions (no privileged variant), `chan` and
`func`, and every linear type. A `var` of such a type **MUST** have an initializer. The
zero value of any `?T` is `nil`.

`chan` and `func` are on that list because of N3: `nil` belongs only to nullable types,
so a bare `chan[int]` cannot hold it. Write `?chan[int]` or `?func(int) -> int` for a
channel or function value that may be absent. *(An earlier draft gave both a zero value
of `nil`, which N3 forbids.)*

## Open questions affecting this chapter

- **Q3 (generics).** `array[T]` and `map[K, V]` are built-in generics. Whether users
  can declare generic functions or types is undecided.
- Whether `matrix[T]` stays built-in or becomes a stdlib type over `array` once
  generics exist.
