# 05 — Statements and Control Flow

## Blocks

`{ ... }` introduces a block and a scope. Braces are **required** on every control-flow
construct; there is no single-statement form.

Parentheses around a condition are **not** required and **SHOULD** be omitted:

```ymr
if x > 0 { ... }        # preferred
if (x > 0) { ... }      # legal, discouraged
```

## Assignment

```ymr
x = 1                   # simple
xs[0] = 1               # indexed
p.x = 1.0               # field
a, b = b, a             # tuple assignment; RHS fully evaluated before any store
q, r := divmod(17, 5)   # destructuring declaration
x += 1                  # compound: += -= *= /= %= **=
x++                     # statement, not an expression; equivalent to x += 1
```

Compound assignment `x op= e` is defined as `x = x op e`, with `x` evaluated once.
`++` and `--` are statements and produce no value, so `y = x++` is a syntax error.

## `if`

```ymr
if cond {
    ...
} else if other {
    ...
} else {
    ...
}
```

The condition **MUST** be `bool`. There is no truthiness: `if x` where `x: int` is a
type error.

## `while`

```ymr
while cond {
    ...
}
```

## `for`

Two forms.

**Range form**, over `array`, `map`, `string`, or an integer range:

```ymr
for x in xs { ... }                # array[T]; x is T
for i, x in enumerate(xs) { ... }  # index and element
for k, v in m { ... }              # map; order unspecified
for i in range(0, 10) { ... }      # 0..9
for i in range(0, 10, 2) { ... }   # step
```

Iterating an `array` while mutating its length is **unspecified**. Do not.

**C-style form:**

```ymr
for i := 0; i < 10; i = i + 1 {
    ...
}
```

The init clause's bindings are scoped to the loop. Any clause may be empty.

*Normative note:* the range form **MUST** work over arrays whose contents are not known
until runtime. Legacy's LLVM backend supported it only over compile-time array
literals, because arrays were lowered to bare pointers with no length. Case
`control/for_in_runtime_array` asserts the general case.

## `break` and `continue`

Legal only inside a loop body, applying to the innermost enclosing loop. There are no
labels in v1, and no `break` out of a `match`.

## `match`

Destructures an enum. **MUST** be exhaustive over the enum's variants.

```ymr
match shape {
    Circle(r)   => return 3.14159 * r * r,
    Rect(w, h)  => return w * h,
    Point       => return 0.0,
}
```

Each arm is `pattern => statement-or-block`, comma-separated; a trailing comma is
permitted. A block arm needs no comma:

```ymr
match outcome {
    Zero => {
        count = count + 1
        print("zero")
    }
    One => print("one"),
}
```

### Arms

A single-statement arm **MUST NOT** return multiple values. The comma that
terminates the arm would be indistinguishable from the comma separating return
values — `A => return x, B => ...` and `A => return x, y` have the same shape, and
telling them apart requires knowing the enum, which the parser does not. Use a
block arm:

```ymr
match e {
    A => { return 1, 2 },        # multiple values need a block
    B => return 3,               # single value is fine
}
```

### Patterns

| Pattern | Matches |
|---|---|
| `Variant` | a payload-free variant |
| `Variant(a, b)` | a variant with payload, binding each position |
| `Variant(_, b)` | as above, discarding a position |
| `Enum.Variant(a)` | a variant qualified by its enum; required when matching a union |
| `nil` | the absent value of an un-narrowed `?T` |
| `_` | anything — the catch-all arm |

Bindings introduced by a pattern are scoped to that arm. Patterns do not nest in v1:
`Circle(Rect(w, h))` is not expressible. There are no literal patterns, no guards, and
no or-patterns. All three are candidates for v2.

### Matching a union

Matching a union (chapter 02) covers every variant of every member. Patterns qualify
the variant with its enum, since two members may share a variant name:

```ymr
match err {
    IOError.NotFound(p)             => print("missing: " + p),
    IOError.PermissionDenied(p)     => print("denied: " + p),
    ParseError.UnexpectedChar(l, c) => print("bad char"),
    ParseError.UnexpectedEOF        => print("truncated"),
}
```

Matching an un-narrowed nullable (`?T`, chapter 02 §Nullable types) requires exactly
one `nil` arm. Inside a block guarded by `x != nil` the checker narrows it, and the
`nil` arm is then neither required nor permitted.

### Exhaustiveness

A `match` that omits a variant and has no `_` arm is a **compile error** naming the
missing variants. This is the enforcement mechanism referenced throughout this spec:
adding a variant to an enum breaks every `match` on it, which is the intent.

A `_` arm satisfies exhaustiveness but **SHOULD** be avoided on enums you own,
precisely because it defeats that.

Every arm **MUST** produce the same set of live linear bindings (rule L4, chapter 02).

## `return`

```ymr
return                 # from a function with no return type
return x               # single value
return q, r            # multiple values
return 0, Error("bad") # the fallible idiom
```

A function with a declared return type **MUST** return on every path. Falling off the
end is a compile error.

### Returning on every path

A function body satisfies that rule when its block **terminates**. A statement
terminates if it is one of:

- a `return`;
- a call to `panic(...)`;
- a block whose last statement terminates;
- an `if` that has an `else`, where both the `then` block and the `else` branch
  terminate — an `if` with no `else` never terminates, however its branch ends;
- a `match` in which every arm's body terminates. Exhaustiveness (below) already
  guarantees the arms cover the scrutinee, so no fall-through case remains;
- a `while true { ... }` whose body contains no `break` that leaves it.

Nothing else terminates. In particular a `for`, a `while` with any other condition, and
a loop that can `break` do not, because the checker does not prove they run at all.

```ymr
func classify(n: int) -> string {
    if n > 0 {
        return "positive"
    } else {
        return "non-positive"
    }
}                                  # terminates: if/else, both branches return

func broken(n: int) -> string {
    if n > 0 {
        return "positive"
    }
}                                  # ERROR: missing return at end of function
```

*(Legacy returned "the last evaluated value" from a function that fell off the end,
which made a function's result depend on the shape of its final statement.)*

## Statement-level expressions

Only calls and channel operations may stand alone as statements. `x + 1` as a
statement is a compile error — it computes a value and discards it, which is always
a mistake or a typo.

A call returning values used by nobody is legal — that is how void-in-effect functions
are written — but a *fallible* call whose `error` result is discarded requires the
blank identifier, making the omission visible:

```ymr
writeFile(path, data)          # ERROR: unhandled error result
_, _ = writeFile(path, data)   # explicit, legal, greppable
```

See chapter 06.
