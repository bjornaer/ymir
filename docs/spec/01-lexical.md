# 01 — Lexical Structure

## Source encoding

Source files are UTF-8. The `.ymr` extension is conventional. A file **MUST** be valid
UTF-8; invalid byte sequences are a lexical error, not replaced with U+FFFD.

Identifiers and keywords are ASCII in v1. String literals and comments **MAY** contain
any Unicode scalar value.

## Line structure

Newline is `\n`. A `\r\n` sequence is normalized to `\n` before lexing. Ymir is not
whitespace-sensitive: blocks are delimited by braces, statements by newlines or `;`.

## Comments

```ymr
# Line comment, runs to end of line.
```

Only line comments exist in v1. Comments are discarded by the lexer and **MUST NOT**
appear in the token stream. *(The legacy implementation emitted them as tokens and
made every parser rule skip them; that is not carried forward.)*

## Tokenization: maximal munch over a closed operator set

Operators **MUST** be recognized by longest-match against the explicit table below —
**not** by matching a run of operator characters.

This rule exists because the legacy lexer used the character class
`[+\-*/%=<>!@]+`, which lexes `x==-3` as a single `==-` token and rejects the program.
A conforming lexer **MUST** lex `x==-3` as `x`, `==`, `-`, `3`.

### Operator table

Longest match wins. Within a length, order is irrelevant since the set is prefix-free
per length.

| Len | Operators |
|---|---|
| 3 | `**=` |
| 2 | `:=` `==` `!=` `<=` `>=` `&&` `\|\|` `->` `=>` `<-` `**` `+=` `-=` `*=` `/=` `%=` `++` `--` |
| 1 | `+` `-` `*` `/` `%` `=` `<` `>` `!` `@` `&` `\|` |

`\|` is both logical-or's second character and the union type separator (chapter 02);
they never occur in the same syntactic position.

Delimiters: `(` `)` `[` `]` `{` `}` `,` `.` `:` `;` `?`

`?` is the nullable type former (chapter 02), not an operator; no operator begins
with it.

`<-` is the channel operator and is **always** lexed as one token. Consequently
`a<-b` is a channel send, never `a < -b`. Write `a < -b` with spaces for the
comparison. This ambiguity is resolved in favor of channels deliberately; the
alternative (context-sensitive lexing) is worse.

## Keywords

Reserved; **MUST NOT** be used as identifiers.

```
break     case      const     continue  else      enum      export
false     for       func      if        import    in        match
module    mut       nil       return    select    spawn     struct
true      try       var       while
```

`try` is the error-propagation expression (chapter 06), **not** a try/catch block.

Reserved for the quantum fragment (chapter 08), unusable as identifiers even before
implementation:

```
discard   gate      measure   qubit     reset
```

**Type names are not keywords.** `int`, `float`, `bool`, `string`, `complex`, `error`,
`array`, `map`, `tuple`, `matrix`, `chan` are predeclared identifiers in the universe
scope. They can be shadowed by a local binding, which is legal but a lint warning.
*(The legacy lexer made these keywords, which made `func str(...)` unparseable.)*

## Identifiers

```
identifier = ( letter | "_" ) { letter | digit | "_" }
letter     = "A".."Z" | "a".."z"
```

Identifiers beginning with `_` are conventionally private to their module; this is
convention, not enforcement — `export` is what controls visibility (chapter 03).

The single identifier `_` is the **blank identifier**. It may appear as an assignment
target or a match binding, discards the value, and **MUST NOT** be read.

## Literals

### Integer

```ymr
42        1_000_000        0xFF        0o755        0b1010
```

Underscores are permitted between digits as separators and carry no meaning. A leading
underscore makes it an identifier, not a literal.

### Float

```ymr
3.14      1.0        1e-9        6.022e23        1_000.5
```

A float literal **MUST** have either a decimal point with at least one digit on each
side, or an exponent. `1.` and `.5` are lexical errors — requiring the digit removes
the ambiguity with the `.` selector.

### Complex

```ymr
3i        2.5i        1e3i
```

A numeric literal suffixed `i` is a `complex` with zero real part. `3 + 4i` is an
ordinary addition expression producing `complex`. Complex exists because the quantum
fragment needs amplitudes; see chapter 08.

### Boolean

`true` and `false` are keywords, of type `bool`.

### String

Double-quoted. Escape sequences are processed **by the lexer**, and the token carries
the *decoded* value with delimiters removed.

```ymr
"hello"        "line 1\nline 2"        "say \"hi\""        "tab\there"
```

| Escape | Meaning |
|---|---|
| `\n` | line feed U+000A |
| `\r` | carriage return U+000D |
| `\t` | tab U+0009 |
| `\\` | backslash |
| `\"` | double quote |
| `\0` | NUL U+0000 |
| `\u{XXXX}` | Unicode scalar, 1–6 hex digits |

Any other escape is a lexical error. An unterminated string literal is a lexical
error; string literals **MUST NOT** span lines.

*Conformance note:* the legacy lexer did none of this. It stored the literal with its
quotes attached and stripped them ad hoc in two separate places in the interpreter,
and never decoded `\n` at all. `print("a\nb")` printed a backslash. Case
`lexical/string_escapes` asserts the correct behavior.

### Nil

`nil` is the zero value of `error` and of channel and function types. It is **not** a
universal null — `int`, `float`, `bool`, `string`, `struct` and `enum` types have no
nil value and cannot be compared to it. See chapter 06.

## Semicolons

A statement is terminated by a newline or an explicit `;`. Both are accepted; `;` is
required only to place multiple statements on one line, and to separate the three
clauses of a C-style `for`.

There is **no** automatic semicolon insertion with token-lookahead rules (Go's
approach). A newline ends a statement unless the statement is syntactically incomplete
— an unclosed `(`, `[`, or `{`, or a trailing binary operator:

```ymr
total := a +
         b            # one statement; line ends on a binary operator

result := compute(
    x,
    y,
)                     # one statement; parens unclosed
```
