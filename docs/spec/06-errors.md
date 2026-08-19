# 06 — Errors

Decision D1: errors are ordinary values returned from functions. There is no `try`
block, `except`, `finally`, `throw`, or user-defined exception type, and no stack
unwinding for recoverable failure.

*(The `try` **expression** in this chapter is unrelated to a try/catch block. It is an
error-propagation operator. See §Propagation.)*

## The two kinds of failure

| | Recoverable | Bug |
|---|---|---|
| Mechanism | an error value in the error position | `panic` |
| Caller can handle it | yes, and **MUST** | no |
| Examples | file missing, parse failure, domain-level division by zero | index out of range, send on a closed channel, `int()` overflow |

If a caller could reasonably do something about it, return an error. If the program is
wrong, `panic`.

## Error sets

An **error set** is the type of the error position. It is either a single enum type or
a union of enum types, written with `|`:

```ymr
enum IOError {
    NotFound(string),
    PermissionDenied(string),
}

enum ParseError {
    UnexpectedChar(int, string),
    UnexpectedEOF,
}

func readFile(path: string) -> (string, IOError)
func parse(data: string) -> (Config, ParseError)
func loadConfig(path: string) -> (Config, IOError | ParseError)
```

The members of a union **MUST** all be enum types. `int | string` is not a type; Ymir
has no general union types, and this restriction is what keeps error sets implementable
with the tagged-union machinery enums already require.

### The error position

The **error position** is the final component of a function's result type, when that
component is an enum or union type. A type in the error position is an error set and is
**nullable**: `nil` is a value of it, meaning "no error".

Nullability attaches to the error position, **not** to enums generally. A `bit` or a
`Shape` used as an ordinary value has no `nil`, so `match` on one needs no `nil` arm.

*This is a wart, and it is recorded as one.* The rule is positional rather than written
into the type. The alternative — an explicit marker, `-> (Config, ?(IOError | ParseError))`
— is noisier on every signature. **Open question Q10** revisits it.

### Set algebra

Unions are **sets**, not ordered lists:

- `A | B` and `B | A` are the same type.
- `A | A` is `A`.
- `(A | B) | C` is `A | B | C`.
- A single enum `A` is the one-member set `A`.

Two error sets are identical when they contain the same members.

### Assignability

An error set `S` is assignable to an error set `T` when **S ⊆ T**. This is the only
subtyping relation in Ymir, and it exists solely for error sets.

```ymr
var e: IOError | ParseError = someIOError    # legal: {IOError} ⊆ {IOError, ParseError}
var f: IOError = someConfigError             # ERROR: {IOError, ParseError} ⊄ {IOError}
```

`nil` is assignable to every error set.

This is what makes errors compose. A function's error set is the union of the sets of
everything it calls, and returning a callee's error directly typechecks without wrapping:

```ymr
func loadConfig(path: string) -> (Config, IOError | ParseError) {
    data, err := readFile(path)          # err: IOError
    if err != nil {
        return zeroConfig, err           # legal: IOError ⊆ IOError | ParseError
    }

    cfg, err2 := parse(data)             # err2: ParseError
    if err2 != nil {
        return zeroConfig, err2          # legal
    }

    return cfg, nil
}
```

*Error set inference* — computing a function's set from its body rather than declaring
it — is **not** in v1. Sets are written explicitly. See open question Q11.

## The predeclared `error`

`error` is a predeclared enum for failures that carry nothing but a message:

```ymr
enum error {
    Msg(string),
}
```

`Error(s)` is sugar for `error.Msg(s)`. Because `error` is an ordinary enum, it
participates in unions like any other: `IOError | error` is a valid error set.

There is no privileged "any error" type. `error` is a convenience, not a supertype.

## Checking

`nil` comparison is the idiom:

```ymr
data, err := readFile(path)
if err != nil {
    print("could not read " + path)
    return
}
```

`==` and `!=` against `nil` are the **only** operations on an un-narrowed error set.
Matching one requires knowing it is non-nil.

### Nil narrowing

Inside a block guarded by `err != nil`, the checker narrows `err` to its non-nullable
form, so `match` needs no `nil` arm:

```ymr
if err != nil {
    match err {                          # narrowed: no nil arm required
        IOError.NotFound(p)         => print("missing: " + p),
        IOError.PermissionDenied(p) => print("denied: " + p),
        ParseError.UnexpectedChar(l, c) => print("bad char"),
        ParseError.UnexpectedEOF    => print("truncated"),
    }
}
```

Narrowing is deliberately minimal. It applies when the condition of an `if` is exactly
`x != nil` or `x == nil` for a binding `x` of error-set type, and only within the
corresponding branch. It is not general flow typing, and it does not survive
reassignment of `x`.

An un-narrowed `match` **MUST** include a `nil` arm:

```ymr
match err {
    nil                      => print("ok"),
    IOError.NotFound(p)      => ...,
    ...
}
```

### Qualified patterns

Patterns over a union qualify the variant with its enum: `IOError.NotFound(p)`. Within
a `match` on a single enum, the qualifier **MAY** be omitted, as elsewhere in the
language:

```ymr
match parseErr {                 # parseErr: ParseError
    UnexpectedEOF        => ...,
    UnexpectedChar(l, c) => ...,
}
```

Exhaustiveness is computed over the **whole union**: every variant of every member.
Adding a variant to `IOError` breaks every `match` on every set containing it. That is
the intent.

## Propagation: the `try` expression

`try e` evaluates `e`, which **MUST** be a call whose result type has an error position.
If the error is `nil`, `try` yields the remaining result values. Otherwise it returns
immediately from the enclosing function, with that error in the error position and the
**zero value** of every other result.

```ymr
func loadConfig(path: string) -> (Config, IOError | ParseError) {
    data := try readFile(path)
    cfg  := try parse(data)
    return cfg, nil
}
```

which is exactly equivalent to the explicit form written above.

### Rules

- The enclosing function **MUST** have an error position, and the callee's error set
  **MUST** be a subset of the enclosing function's. This is checked statically; `try`
  never widens a set implicitly beyond what is declared.
- Every non-error result of the enclosing function **MUST** have a zero value. `try` in
  a function returning an enum or a linear type is a compile error, since there is
  nothing to return on the error path.
- `try` on a call with no error position is a compile error.
- `try` is an expression and composes: `cfg := try parse(try readFile(path))`.
- `try` **MUST NOT** appear in a `gate` body (chapter 08 — gates cannot fail) or where
  a linear binding is live and unconsumed, since the early return would abandon it.

### When not to use it

`try` propagates unchanged. Use the explicit form when you want to add context, handle
some variants and propagate others, or clean up first:

```ymr
data, err := readFile(path)
if err != nil {
    return zeroConfig, Error("loading " + path + ": " + str(err))
}
```

## Unhandled errors are a compile error

If a call's result type has an error position, the caller **MUST** bind it. Discarding
requires the blank identifier explicitly:

```ymr
result, err := divide(10, 2)     # legal
result := divide(10, 2)          # ERROR: multi-valued call bound to one name
divide(10, 2)                    # ERROR: unhandled error result
_, _ = divide(10, 2)             # legal — deliberate, visible, greppable
data := try readFile(path)       # legal — propagates
```

Binding an error and never reading it is also a compile error (it is an unused
binding). An error must be checked, propagated, or explicitly discarded.

## Wrapping

There is no structured cause chain. To add context, construct a new error:

```ymr
return zeroConfig, Error("loading config: " + str(err))
```

Every enum has an auto-derived `str()`. Note that wrapping into `error` **loses the
set**: the caller sees `error`, not `IOError | ParseError`. Prefer propagating the set
where the caller might act on the variants, and wrap only at the boundary where nobody
will.

## `panic`

`panic` aborts the program. It is **not** catchable; there is no `recover`.

```ymr
panic("unreachable: parser reached state " + str(s))
```

The runtime panics on: array index out of range, single-value map access on an absent
key, integer division or modulo by zero, `int()` of a NaN/infinite/out-of-range float,
send on a closed channel, and close of a closed or `nil` channel.

A panic **MUST** write the message and a stack trace to stderr and exit with a
**non-zero** status.

*Normative note against legacy:* `ymir run` in the legacy implementation caught every
exception, printed it, and exited 0 — five bare `except Exception` handlers in
`cli/ymir_cli.py`. Its CI "examples" job was therefore structurally incapable of
failing, which is why a broken `concurrency_demo.ymr` is in the repository. The exit
code is normative. Case `errors/panic_exit_code` asserts it is non-zero.

## No `recover`, deliberately

A catchable panic becomes an exception mechanism by another name, and reintroduces
everything D1 was chosen to avoid — including unwinding past a live qubit. If a
long-running service needs to survive a failing task, that isolation belongs at the
task boundary (chapter 07) and is an open design question, not a `recover` builtin.
