# Ymir — Migration Plan

**Read this first if you are picking up cold.** It is the single source of truth for
where the project stands and what happens next. Update the *Status* and *Session log*
sections whenever you do meaningful work.

- **Last updated:** 2026-08-20
- **Current phase:** Phase 0 — complete. Phase 1 not started.
- **Blocking:** open question Q1 must be answered before Phase 2.

---

## 1. What Ymir is becoming

A statically typed, compiled language with algebraic data types, Go-style concurrency,
and a linearly typed quantum fragment, executed by a bytecode VM shipped as one static
Go binary.

The differentiator is the quantum fragment: no-cloning, use-after-measurement, and
dropped-qubit errors are **compile errors**, which a library in a host language cannot
do. Everything else in the language exists to make that fragment usable.

Full rationale, the four locked decisions, and all open questions:
[`docs/spec/00-overview.md`](docs/spec/00-overview.md).

## 2. Why we are rewriting rather than refactoring

The Python implementation was assessed in August 2026. Its test suite reports
`278 passed, 5 skipped`, and that number is not measuring language behavior. Verified
by direct execution:

- `func main()` runs under LLVM/auto mode and is a **silent no-op** under `-i`. Every
  quickstart in the README is a no-op under one of the two engines.
- Module-level `var` is invisible inside functions — `Undefined variable: total`.
- The type checker types the literal `2.0` as `None`; `x / 2.0` fails to typecheck.
- The lexer merges operators: `x==-3` lexes as one `==-` token.
- `ymir run` **always exits 0** (five bare `except Exception` in `cli/ymir_cli.py`),
  which makes the CI `examples` job structurally incapable of failing. A broken
  `concurrency_demo.ymr` is in the repository because of this.
- LLVM codegen lowers **every** function parameter to `i32` (`tools/codegen.py:216`
  indexes a `List[Type]` as a dict), and memoizes a side-effecting IR emitter with
  `@functools.lru_cache`.

The two blockers are AST-level: a call's callee is a bare `string` (so function values
are inexpressible), and identifiers are bare strings that fall back to string literals
(so a typo becomes a value). Fixing them means replacing the AST and both backends —
about 4,000 of 5,600 lines. That is a rewrite regardless of what it is called, so it
is being done deliberately, in a language that hosts the concurrency model natively.

The Python implementation is frozen at [`/ymir-legacy-py/`](ymir-legacy-py/) as an
executable reference. Its defect catalogue is in its README.

## 3. Repository layout

```
docs/spec/          NORMATIVE language definition. Chapters 00-09.
conformance/        Executable form of the spec. run.py + cases/.
ymir-legacy-py/     Frozen Python implementation. Reference only. Delete at Phase 8.
compiler/           (Phase 1) Go: lexer, parser, checker, bytecode compiler.
vm/                 (Phase 3) Go: the bytecode virtual machine.
cmd/ymir/           (Phase 1) Go: the CLI.
editor-support/     VSCode extension. Needs updating at Phase 6.
docs/               Older prose docs. Superseded by docs/spec/ where they conflict.
```

`docs/context.md`, `docs/syntax_guidelines.md`, `docs/concurrency.md`, and
`docs/stdlib_reference.md` describe the **legacy** language and contain claims we have
disproved. They are kept for history. **`docs/spec/` wins on every conflict.**

## 4. The conformance suite is the contract

```bash
python3 conformance/run.py --ymir "./bin/ymir run"                        # Go
python3 conformance/run.py --ymir "poetry run ymir run" --cwd ymir-legacy-py  # legacy
```

Baseline against the frozen Python implementation, 2026-08-20:
**2 passed, 15 failed.** That is the starting line. Phase exit criteria below are
stated as conformance categories going green.

**The rule that matters:** never weaken a case to make an implementation pass. Fix the
implementation, or change the spec and say so in the commit message.

## 5. Phases

Each phase has a **definition of done** that is mechanically checkable. Do not start a
phase before its predecessor's criteria are met.

### Phase 0 — Spec and conformance foundation ✅ COMPLETE (2026-08-20)

- [x] Move Python implementation to `ymir-legacy-py/`, CI updated, suite still green
- [x] `docs/spec/` chapters 00–09 drafted
- [x] `conformance/run.py` + 17 initial cases
- [x] Baseline recorded against legacy
- [x] `CLAUDE.md` and the `ymir-compiler` agent

### Phase 1 — Frontend in Go

Go module, lexer, parser, AST. No types, no execution.

- Deliverables: `compiler/lexer`, `compiler/ast`, `compiler/parser`, `cmd/ymir` with
  a `ymir parse <file>` subcommand that dumps the AST or a syntax error.
- Identifiers are **AST nodes**, never strings. A call's callee is an **expression**,
  never a string. These two are non-negotiable; they are the legacy's fatal flaws.
- Error messages carry file, line, column, and a source excerpt from day one.
- **Done when:** every `.ymr` file in `conformance/cases/` parses or reports a syntax
  error with an accurate position, and chapter 09's grammar is implemented in full.

### Phase 2 — Type checker  🚧 BLOCKED on Q1

- Deliverables: `compiler/types`, `compiler/check`. Scope resolution, local inference,
  assignability, exhaustiveness checking, definite assignment.
- **Build the linearity machinery now** (chapter 02, rules L1–L6) even though no linear
  type exists until Phase 7. Decision D3 exists for this reason. The move/consume
  bookkeeping in the checker is the expensive part; adding `qubit` later is then small.
- **Done when:** every `compile-error` case in the suite reports the right error, and
  the `types/`, `scope/`, `decl/`, and `match/` categories pass their compile-time
  assertions.

### Phase 3 — Bytecode and VM, minimal slice

- Deliverables: `compiler/bytecode`, `vm/`. Enough for: `main`, `print`, `int` and
  `float` arithmetic, `if`/`while`, function calls, module-level `var`.
- One engine. No fallback path, ever. If the VM cannot do something, that is a
  compile error, not a silent second implementation.
- **Done when:** `decl/`, `scope/`, `lexical/`, `types/`, `expr/`, `control/` pass.

### Phase 4 — Full classical language

Structs, enums, `match`, arrays, maps, strings, tuples, closures, methods, errors,
`panic` with a stack trace and a non-zero exit code.

- **Done when:** every non-`concurrency`, non-`quantum` case passes, and the suite has
  been grown to at least ~150 cases covering every normative **MUST** in chapters 01–06.

### Phase 5 — Concurrency  🚧 BLOCKED on the data-race question (chapter 07)

`spawn`, `chan[T]`, `select`, `close`, ranging over a channel.

- Resolve first: shared `array`/`map` across tasks is currently *unspecified* behavior,
  the one hole in "no undefined behavior in safe code." Decide between a VM race
  detector and making those types non-sendable.
- **Done when:** the `concurrency/` category passes, plus a stress case run under
  repetition without flaking.

### Phase 6 — Stdlib, tooling, distribution

- Stdlib written **in Ymir** where possible, in Go where it must be. Ported against the
  conformance suite, not against the legacy sources.
- `ymir run`, `ymir build`, `ymir fmt`, `ymir test`. Correct exit codes throughout —
  this is what legacy got wrong.
- Cross-compiled release binaries, updated Homebrew tap, VSCode extension pointed at
  the new grammar.
- **Done when:** `brew install ymir` yields a working binary on macOS and Linux, and
  the extension highlights the current syntax.

### Phase 7 — Quantum fragment

`qubit`, `qreg[N]`, `bit`, gates, `gate` declarations with `adjoint`/`controlled`,
`measure`/`reset`/`discard`, and the state-vector simulator.

- The linearity checker from Phase 2 should need extension, not redesign. If it needs
  redesign, Phase 2 was done wrong.
- **Done when:** the `quantum/` category passes with `skip` removed, and teleportation
  (chapter 08's worked example) runs and produces correct statistics over many shots.

### Phase 8 — Retire the legacy implementation

- Delete `ymir-legacy-py/` in one commit once the Go implementation passes the full
  suite.
- Optional and explicitly **not** a prerequisite: a native AOT backend, gated on
  passing the identical conformance suite.

## 6. Open questions

Blocking work. Answer in `docs/spec/00-overview.md`, then update here.

| # | Question | Blocks | Status |
|---|---|---|---|
| Q1 | How do user types satisfy `error`? Interfaces (a), open enum (b), or closed as spec'd (c)? | **Phase 2** | open |
| Q2 | Is `Result[T,E]` in the stdlib alongside `(T, error)`? | Phase 6 | open, leaning no |
| Q3 | User-facing generics in v1? | Phase 2 | open |
| Q4 | Does `main` return `int` or `error`? | Phase 3 | open |
| Q5 | Integer overflow: wrap, trap, or saturate? | Phase 3 | open |
| Q6 | Data races on shared `array`/`map` between tasks | **Phase 5** | open |
| Q7 | Structured concurrency instead of Go's detached `spawn`? | Phase 5 | open |
| Q8 | Immutability by default for locals (`let`/`mut`)? | Phase 2 | open |

## 7. Standing rules

1. **The spec is normative.** Implementation disagrees with spec ⇒ implementation is
   the bug. Change the spec deliberately, in its own commit, saying what it invalidates.
2. **No feature without a conformance case.** A rule with no case is not a rule.
3. **One execution engine.** The dual-backend split is the root cause of the legacy's
   worst bug. Do not reintroduce it, including "just a fast path."
4. **No silent failure.** Every error path exits non-zero. No bare `except`/`recover`
   that swallows. This is what made legacy's CI meaningless.
5. **Do not fix `ymir-legacy-py/`.** It is frozen. Its bugs are documentation.

## 8. Session log

Append an entry per working session. Keep it short: what changed, what to do next.

### 2026-08-20 — Assessment and Phase 0

- Assessed the Python implementation. Installed Python 3.13 + deps (fails on 3.14;
  llvmlite 0.43 has no wheel) and ran the suite: 278 passed. Then verified by direct
  execution that the green is not measuring language behavior — see §2.
- Decided: rewrite in Go, bytecode VM, errors-as-values, structs + ADTs, quantum
  normative now.
- Moved the Python implementation to `ymir-legacy-py/`; CI workflow renamed to
  `legacy-py-tests.yml` with `working-directory` set; suite re-verified green at the
  new path (278 passed).
- Wrote `docs/spec/` chapters 00–09 (~1,900 lines) and `conformance/` with 17 cases.
- Recorded the legacy baseline: 2 passed, 15 failed.
- **Next:** answer Q1, then start Phase 1 (Go frontend). Nothing is committed yet.
