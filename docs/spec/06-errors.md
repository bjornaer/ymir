# 06 — Errors

Decision D1: errors are ordinary values returned from functions. There is no `try`,
`except`, `finally`, `throw`, or user-defined exception type, and no stack unwinding
for recoverable failure.

## The two kinds of failure

| | Recoverable | Bug |
|---|---|---|
| Mechanism | `error` return value | `panic` |
| Caller can handle it | yes, and **MUST** | no |
| Examples | file missing, parse failure, division by zero *in your domain logic* | index out of range, nil channel send, `int()` overflow |

If a caller could reasonably do something about it, return an `error`. If the program
is wrong, `panic`.

## The `error` type

`error` is a predeclared struct:

```ymr
struct error {
    message: string,
    kind:    string,
}
```

`nil` is its zero value and means "no error". `error` is the only struct type
comparable to `nil`.

Constructors:

```ymr
Error("division by zero")               # kind is ""
ErrorKind("DivByZero", "b was zero")    # explicit kind tag
```

`kind` is a caller-inspectable tag, compared with `==`. It is a string rather than a
type because Ymir has no interfaces (decision D2) — see **open question Q1**, which
this design exists to provoke a decision on.

## The convention

A fallible function returns its result and an `error`, error last:

```ymr
func divide(a: int, b: int) -> (int, error) {
    if b == 0 {
        return 0, Error("division by zero")
    }
    return a / b, nil
}
```

Callers destructure and check:

```ymr
result, err := divide(10, 0)
if err != nil {
    print(err.message)
    return
}
print(result)
```

When `err != nil`, the other returned values **MUST** be the zero values of their
types. Callers **MAY** rely on this.

## Unhandled errors are a compile error

If a function's return type includes `error`, the caller **MUST** bind it. Discarding
it requires the blank identifier explicitly:

```ymr
result, err := divide(10, 2)     # legal
result := divide(10, 2)          # ERROR: multi-valued call bound to one name
divide(10, 2)                    # ERROR: unhandled error result
_, _ = divide(10, 2)             # legal — deliberate, visible, greppable
```

This is the single most valuable property of errors-as-values, and it is worth the
noise. Case `errors/unhandled_is_compile_error` asserts it.

Binding an error and never reading it is also a compile error (it is an unused
binding). `err` must be either checked or named `_`.

## Richer errors

Where a string tag is not enough, return a module-local enum instead of `error` and
`match` on it. Exhaustiveness then forces the caller to handle every failure mode:

```ymr
enum ParseError {
    UnexpectedChar(int, string),
    UnexpectedEOF,
    NumberOutOfRange(string),
}

func parseInt(s: string) -> (int, ParseError) { ... }

n, err := parseInt(input)
match err {
    UnexpectedChar(pos, c) => print("bad char at " + str(pos)),
    UnexpectedEOF          => print("truncated"),
    NumberOutOfRange(s)    => print("too big: " + s),
}
```

The cost — and it is real — is that `ParseError` and `error` are unrelated types, so
propagating across a module boundary means re-wrapping. This is exactly the tension
open question **Q1** must resolve before the type checker is built.

## Wrapping

```ymr
f, err := open(path)
if err != nil {
    return nil, Error("loading config: " + err.message)
}
```

There is no structured cause chain in v1. *(Open: whether `error` gains a
`cause: error` field. It requires either a recursive struct or a boxing rule.)*

## `panic`

`panic` aborts the program. It is **not** catchable; there is no `recover`.

```ymr
panic("unreachable: parser reached state " + str(s))
```

The runtime panics on: array index out of range, single-value map access on an absent
key, integer division or modulo by zero, `int()` of a NaN/infinite/out-of-range float,
send on a closed channel, and receive from a closed empty channel.

A panic **MUST** write the message and a stack trace to stderr and exit with a
**non-zero** status.

*Normative note against legacy:* `ymir run` in the legacy implementation caught every
exception, printed it, and exited 0 — five bare `except Exception` handlers in
`cli/ymir_cli.py`. This made its CI "examples" job structurally incapable of failing,
which is why a broken `concurrency_demo.ymr` sits in the repository today. The exit
code is normative. Case `errors/panic_exit_code` asserts it is non-zero.

## No `recover`, deliberately

A catchable panic becomes an exception mechanism by another name, and reintroduces
every problem D1 was chosen to avoid — including unwinding past a live qubit. If a
long-running service needs to survive a failing task, that isolation belongs at the
task boundary (chapter 07) and is an open design question, not a `recover` builtin.
