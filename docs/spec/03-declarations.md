# 03 — Declarations, Modules, and Functions

## Program structure

A program is a set of modules. Exactly one module **MUST** declare
`func main()`, which is the entry point.

## Module declaration

Every source file **MUST** begin with a module declaration, before any other
declaration (comments and blank lines excepted).

```ymr
module stdlib.math
```

Module names are dot-separated identifiers. A file's module name **MUST** match its
path relative to the module root, with `/` replaced by `.` and `.ymr` removed. This
is enforced by the compiler.

## Imports

```ymr
import stdlib.math
import stdlib.math as m
```

Import binds the module's name (or alias) in the importing file's scope. Members are
reached with `.`:

```ymr
import stdlib.math
r := math.sqrt(2.0)
```

There is **no** wildcard import and no way to bring a member into the local scope
unqualified. Every non-local name in a file is traceable to an import by reading the
top of the file.

Import cycles are a compile error.

## Exports

A declaration is module-private unless marked `export`.

```ymr
export func sqrt(x: float) -> float { ... }
export const PI: float = 3.141592653589793

func helper() -> int { ... }        # private to this module
```

`export` applies to `func`, `struct`, `enum`, and `const`. **`var` cannot be
exported** — there are no mutable globals across module boundaries.

## Constants

```ymr
const PI: float = 3.141592653589793
const MAX_QUBITS: int = 30
```

A `const` initializer **MUST** be a compile-time constant expression: literals and
operators over literals and other constants. Constants are typed; there are no untyped
constants and no automatic conversion.

## Variables

```ymr
var x: int = 0        # annotated, initialized
var y := 0            # inferred
z := 0                # short form, equivalent to `var z := 0`
var w: int            # zero-initialized
```

`:=` **declares**. `=` **assigns** to an existing binding. Assigning to an undeclared
name is a compile error; declaring a name already bound in the same scope is a compile
error (shadowing in a *nested* scope is legal).

*This is the fix for the legacy implementation's worst class of bug.* There, an
unknown identifier silently evaluated to a string equal to its own name, so a typo
became a value instead of an error. Here, every name resolves at compile time or the
program does not build. Case `decl/undefined_variable` asserts this.

### Mutability

Bindings are mutable by default. `const` is the immutable form for compile-time
values. There is no `let`/`mut` distinction on locals in v1; `mut` marks a parameter or
a method receiver and nothing else. *(Resolved question R6. Immutability-by-default is
the better default, but adding `let` later is additive and doing it now would rewrite
every example in this spec.)*

## Scope

Ymir is **lexically scoped**, with these levels, innermost first:

1. Block scope — any `{ ... }`, including function bodies and loop bodies.
2. Function scope — parameters.
3. File scope — imports.
4. Module scope — that module's `func`, `struct`, `enum`, `const`, `var`.
5. Universe scope — predeclared type names and builtins.

**Module-scope declarations are visible regardless of textual order.** A `func` may call
one declared below it, and a `struct` field may name a type declared later in the file.
File scope holds only imports, so resolution inside a function body proceeds block chain
→ parameters → this file's imports → the whole module → universe. *(This is why a
checker collects module-scope names in a pre-pass before checking any body. Local
bindings are the opposite: they are visible only after their declaration, see §Variables
below.)*

A module-level `var` is visible and assignable inside every function in that module.

```ymr
module counter

var total: int = 0

func bump() {
    total = total + 10      # legal, mutates the module-level binding
}

func main() {
    bump()
    print(total)            # prints 10
}
```

*This is a normative statement against the legacy implementation*, where the same
program failed with `Undefined variable: total` because the interpreter kept two flat
dictionaries and swapped them at each call. Case `scope/module_var_mutation` asserts
it prints `10`.

Blocks nest properly, and a binding declared in a block is not visible after it:

```ymr
if cond {
    inner := 1
}
print(inner)      # ERROR: undefined
```

## Functions

```ymr
func add(a: int, b: int) -> int {
    return a + b
}

func greet(name: string) {           # no return type = returns nothing
    print("hello, " + name)
}
```

Parameters and return type **MUST** be annotated (chapter 02). A function with a
declared return type **MUST** return on every path; falling off the end is a compile
error. *(Legacy returned "the last evaluated value" from a function with no `return`,
which meant a function's result depended on the shape of its final statement.)*

### Multiple return values

```ymr
func divmod(a: int, b: int) -> (int, int) {
    return a / b, a % b
}

q, r := divmod(17, 5)
q, _ := divmod(17, 5)        # discard the second
```

Multiple returns are the normative mechanism for fallible operations (chapter 06).
A multi-valued call **MUST** be destructured; binding it to a single name is a
compile error.

### Parameter passing

Primitives, `struct`, and `tuple` pass **by value**. `array`, `map`, `chan`, and
`string` pass **by reference** (`string` immutably, so the distinction is
unobservable). A parameter declared `mut` receives a mutable reference to the
caller's binding:

```ymr
func scale(p: mut Point, k: float) {
    p.x = p.x * k
}
```

Linear parameters follow rules L3 and L4 of chapter 02.

### Functions as values, and closures

Functions are values of `func` type (chapter 02). A function literal may be written
inline and **captures its enclosing scope by reference**:

```ymr
func counter() -> func() -> int {
    count := 0
    return func() -> int {
        count = count + 1
        return count
    }
}

c := counter()
print(c())      # 1
print(c())      # 2
```

A closure **MUST NOT** capture a linear binding (rule L5).

### `main`

```ymr
func main() { ... }
```

`main` takes no parameters. Exactly one module in a program declares it. **`main` is
invoked automatically**; it **MUST NOT** be called explicitly.

Top-level executable statements are **not permitted**. A module body contains only
declarations. This forecloses the legacy implementation's entry-point divergence,
where `func main()` ran under one engine and was a silent no-op under the other
because the two disagreed about whether top-level statements or `main` was the entry
point. Case `decl/main_entry_point` asserts `main` runs.

Process exit code is 0 on normal return from `main`, and non-zero on panic. *(Open
question Q4: whether `main` should return `int` or `error`.)*
