# 04 — Expressions

## Precedence

Highest binding first. All binary operators are **left-associative** except `**`,
which is right-associative.

| Level | Operators | Notes |
|---|---|---|
| 1 | `f(x)` `a[i]` `s.field` `t.0` | call, index, select — postfix |
| 2 | `-x` `!x` `<-ch` | unary, right-associative |
| 3 | `**` | exponent, **right**-associative |
| 4 | `*` `/` `%` `@` | `@` is matrix multiply |
| 5 | `+` `-` | |
| 6 | `<` `<=` `>` `>=` | |
| 7 | `==` `!=` | |
| 8 | `&&` | short-circuit |
| 9 | `\|\|` | short-circuit |

`2 ** 3 ** 2` is `2 ** (3 ** 2)` = 512. `-x ** 2` is `-(x ** 2)`.

There is no ternary operator and no comma operator.

## Operand typing

Both operands of a binary operator **MUST** have identical types (chapter 02 —
no implicit conversion). The result type is:

| Operators | Operand types | Result |
|---|---|---|
| `+` `-` `*` `/` `%` `**` | `int` | `int` |
| `+` `-` `*` `/` `**` | `float`, `complex` | same as operands |
| `+` | `string` | `string` (concatenation) |
| `+` `-` `*` | `matrix[T]` | `matrix[T]`, element-wise |
| `@` | `matrix[T]` | `matrix[T]` |
| `<` `<=` `>` `>=` | `int`, `float`, `string` | `bool` |
| `==` `!=` | any unrestricted type | `bool` |
| `&&` `\|\|` | `bool` | `bool` |

`%` is defined only on `int`. Its result takes the sign of the dividend (`-7 % 3` is
`-1`), matching truncating division.

`/` on `int` is truncating integer division. `7 / 2` is `3`, not `3.5`. Division by
zero — `/` or `%` with a zero `int` divisor — is a **panic**. `float` division by zero
yields IEEE infinity and does not panic.

`complex` is not ordered; `<` and friends are a type error on it.

`==` on `float` and `complex` is IEEE equality, so `nan != nan`. `==` on `array`,
`map`, `struct`, and `enum` is deep structural equality; on `chan` and `func` it is
reference identity. Linear types **MUST NOT** be compared — comparison would read them
without consuming them.

## Short-circuit evaluation

`&&` and `||` evaluate their right operand only if the result is not already
determined. This is normative, not an optimization: the right operand may have effects.

## Evaluation order

Operands of a binary operator evaluate **left to right**. Function call arguments
evaluate **left to right**, before the call. Index and selector expressions evaluate
their base before their index.

This is fully specified deliberately — unspecified evaluation order is a portability
trap between the VM and any future AOT backend.

## Literals

### Composite literals

```ymr
[1, 2, 3]                          # array[int]
[[1.0, 2.0], [3.0, 4.0]]           # matrix[float] if rectangular, else array[array[float]]
{"a": 1, "b": 2}                   # map[string, int]
(1, "one")                         # tuple[int, string]
Point{x: 1.0, y: 2.0}              # struct, all fields named
Circle(2.0)                        # enum variant with payload
```

A nested array literal is `matrix[T]` when every row has equal length and `T` is
`float` or `complex`; otherwise it is `array[array[T]]`. Where the context supplies an
expected type, that type wins. A trailing comma is permitted in every bracketed list.

### Function literals

```ymr
func(a: int, b: int) -> int { return a + b }
```

Fully annotated, like a declared function. There is no shorthand lambda syntax and no
parameter type inference from context in v1.

## Calls

```ymr
f(a, b)              # function or function-valued binding
p.magnitude()        # method, receiver is p
math.sqrt(2.0)       # module-qualified
Circle(2.0)          # enum variant construction
```

Argument count and types **MUST** match exactly. There are no default parameters, no
variadic user functions, and no keyword arguments in v1. *(`print` is variadic; it is a
builtin, and that is a wart to be removed once generics land — see Q3.)*

A multi-valued call may appear only as the entire right-hand side of a destructuring
assignment or a `return`. It **MUST NOT** be nested inside another expression:

```ymr
q, r := divmod(17, 5)          # legal
print(divmod(17, 5))           # ERROR: multi-valued call in expression position
```

## Indexing and selection

```ymr
xs[0]           # array element; panics if out of range
m["key"]        # map, single-value form; panics if absent
v, ok := m["key"]   # map, two-value form; ok is false if absent
s[3]            # string, yields the byte at index 3 as int
p.x             # struct field
t.0             # tuple element, index must be a literal
```

Assignment to an index or field is legal where the base is mutable:

```ymr
xs[0] = 99
m["k"] = 1
p.x = 3.0
```

## Channel receive

`<-ch` is a unary expression of type `T` for `ch: chan[T]`. See chapter 07.

## Constant expressions

A complex literal — a numeric literal, then `+` or `-`, then an imaginary literal — is a
single constant, not a binary operation (chapter 02 §Complex literals). `1.0 + 2.0i` is
one value; `x + 2.0i` where `x` is a binding is a type error.

An expression is constant if it is a literal, a `const`, or an operator applied to
constant operands. Constant expressions are evaluated at compile time. Division by
zero in a constant expression is a **compile error**, not a runtime panic.
