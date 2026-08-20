# The Ymir Language Specification

This directory is the **normative definition** of Ymir. Where this spec and any
implementation disagree, the spec is right and the implementation is a bug.

Version: **0.1.0-draft** · Status: **in design, nothing frozen**

## Chapters

| # | Chapter | Status | Covers |
|---|---|---|---|
| 00 | [Overview](00-overview.md) | draft | Goals, non-goals, the four locked decisions, open questions |
| 01 | [Lexical structure](01-lexical.md) | draft | Encoding, tokens, literals, operators, comments |
| 02 | [Type system](02-types.md) | draft | Primitives, composites, structs, enums, linearity, inference |
| 03 | [Declarations & modules](03-declarations.md) | draft | `module`, `import`, `export`, `func`, `struct`, `enum`, `var` |
| 04 | [Expressions](04-expressions.md) | draft | Operators, precedence, calls, literals |
| 05 | [Statements & control flow](05-statements.md) | draft | `if`, `while`, `for`, `match`, `return` |
| 06 | [Errors](06-errors.md) | draft | Errors as values, `panic`, the `error` type |
| 07 | [Concurrency](07-concurrency.md) | draft | `spawn`, channels, `select` |
| 08 | [Quantum](08-quantum.md) | draft, unimplemented | `qubit`, linear typing, gates, measurement |
| 09 | [Grammar](09-grammar.md) | draft | Consolidated EBNF |

## How to change this spec

1. Open the change as a discussion in `PLAN.md` under *Open questions*, or as an issue.
2. Amend the chapter **and** add or update conformance cases in `/conformance/cases/`.
   A spec change with no conformance case is not a spec change.
3. If the change invalidates existing conformance cases, say so explicitly in the
   commit message. Silent behavior changes are the failure mode this whole
   structure exists to prevent.

## Normative language

- **MUST** / **MUST NOT** — required; a conforming implementation is wrong otherwise.
- **SHOULD** — strongly recommended; deviation needs a stated reason.
- **MAY** — genuinely optional.
- *Unspecified* — implementations may differ; programs relying on it are not portable.
- *Undefined* — programs doing this are invalid; implementations may do anything.
  Ymir aims to have **no undefined behavior** in safe code. Every occurrence in this
  spec is a defect to be designed away.
