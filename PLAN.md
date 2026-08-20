# Ymir — Migration Plan

**Read this first if you are picking up cold.** It is the single source of truth for
where the project stands and what happens next. Update the *Status* and *Session log*
sections whenever you do meaningful work.

- **Last updated:** 2026-08-20
- **Current phase:** Phase 1 — complete. Phase 2 not started.
- **Blocking:** nothing blocks Phase 2. Q10 and Q11 should be settled during it; Q6 blocks Phase 5.

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

### Phase 1 — Frontend in Go ✅ COMPLETE (2026-08-20)

- [x] `compiler/token`, `compiler/lexer`, `compiler/ast`, `compiler/parser`,
      `compiler/diag`, `cmd/ymir`
- [x] `ymir parse [-tokens] [-q] <file>` dumps the tree or reports syntax errors
- [x] Identifiers are `*ast.Ident` nodes; a call's callee is an `ast.Expr`
- [x] Diagnostics carry file, line, column, a source excerpt, and a caret
- [x] All 23 conformance cases parse; `examples/tour.ymr` exercises the full grammar
- [x] Go tests for both packages, plus `TestConformanceCasesParse` as the exit gate
- [x] CI: gofmt, vet, test, and a parse pass over every conformance case

### Phase 2 — Type checker

- Deliverables: `compiler/types`, `compiler/check`. Scope resolution, local inference,
  assignability, exhaustiveness checking, definite assignment.
- **Error sets (R1) are the expensive part of this phase**, more so than linearity:
  union normalization, subset assignability, exhaustiveness over a union, nil narrowing,
  and `try`'s subset check. Budget accordingly.
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

### Phase 6 — Stdlib and tooling

- Stdlib written **in Ymir** where possible, in Go where it must be. Ported against the
  conformance suite, not against the legacy sources.
- `ymir run`, `ymir build`, `ymir fmt`, `ymir test`. Correct exit codes throughout —
  this is what legacy got wrong.
- **Done when:** a non-trivial program can be written using only the stdlib, and
  `ymir fmt` is idempotent over every file in the repository.

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

### Phase 9 — Editor support and distribution  ← the last phase

Deliberately last. Every item here is a wrapper around a language that must already be
finished; doing any of it earlier means redoing it when the syntax moves.

**The architectural decision that makes this cheap: do not write N editor plugins.**
Write two things and let every editor consume them.

1. **`ymir lsp`** — a Language Server Protocol server, a subcommand of the same binary.
   It reuses `compiler/parser` and `compiler/check` directly, so diagnostics in the
   editor are the *same* diagnostics the compiler emits, and can never drift from them.
   Start with diagnostics, go-to-definition, hover types, and completion.
2. **`tree-sitter-ymir`** — a grammar in its own repository, for syntax highlighting
   and structural selection.

With those two, editor support is thin glue:

| Editor | What is actually needed |
|---|---|
| Neovim | `nvim-lspconfig` entry + `nvim-treesitter` parser registration. Both upstream PRs, no plugin of our own. |
| Vim (8/legacy) | `ftdetect` + `syntax/ymir.vim`, hand-written regex highlighting. The only place a separate grammar is unavoidable. |
| VS Code | Thin extension that launches `ymir lsp`. The existing TextMate grammar in `editor-support/vscode/` is retargeted; it predates this spec and is wrong today. |
| Helix, Zed, Emacs (eglot) | Configuration only, given the LSP server and tree-sitter grammar. |

**Distribution.** Go cross-compiles from one machine, which is most of why D4 chose it.

- **GitHub Releases** — `ymir_<version>_<os>_<arch>.tar.gz` for
  darwin/{amd64,arm64}, linux/{amd64,arm64}, windows/amd64, built in CI on tag, with
  checksums. Everything below is a thin wrapper over these artifacts.
- **curl installer** — `curl -fsSL https://ymir-lang.org/install.sh | sh`: detect
  os/arch, download, verify the checksum, install to `~/.local/bin` or `/usr/local/bin`.
  Must be readable in one screen and must fail loudly rather than half-installing.
- **Homebrew** — replace the existing `bjornaer/homebrew-ymir` formula. The current one
  is a Python virtualenv formula and does not survive the rewrite; the new one is a
  binary formula, which is far simpler.
- **Windows** — **Scoop** manifest and **WinGet** package, both of which are a JSON/YAML
  file pointing at the release archive. Do **not** build an MSI; it is disproportionate
  effort for a CLI, and neither manifest requires code signing to start. Confirm the
  binary works under both PowerShell and Git Bash before publishing.
- **`go install github.com/bjornaer/ymir/cmd/ymir@latest`** works for free and should be
  documented as the zero-infrastructure path.

**Done when:** on a clean macOS, Linux, and Windows machine, a user can install Ymir by
a single command, run `ymir version`, open a `.ymr` file in Neovim and VS Code, and see
type errors inline from `ymir lsp`.

## 6. Open questions

Blocking work. Answer in `docs/spec/00-overview.md`, then update here.

| # | Question | Blocks | Status |
|---|---|---|---|
| R1 | How do user types occupy the `error` position? | — | **resolved: error sets** |
| R2 | Error propagation operator | — | **resolved: `try`** |
| Q2 | Is `Result[T,E]` in the stdlib alongside `(T, error)`? | Phase 6 | open, largely mooted by R1 |
| Q3 | User-facing generics in v1? | Phase 2 | open |
| Q4 | Does `main` return `int` or `error`? | Phase 3 | open |
| Q5 | Integer overflow: wrap, trap, or saturate? | Phase 3 | open |
| Q6 | Data races on shared `array`/`map` between tasks | **Phase 5** | open |
| Q7 | Structured concurrency instead of Go's detached `spawn`? | Phase 5 | open |
| Q8 | Immutability by default for locals (`let`/`mut`)? | Phase 2 | open |
| Q10 | Should error-position nullability be written into the type? | Phase 2 | open |
| Q11 | Should error sets be inferred? | Phase 2 | open, leaning explicit-first |
| Q12 | Are `as` and `default` reserved words or contextual identifiers? | Phase 6 | open, found in Phase 1 |

R1 and R2 are recorded in `docs/spec/00-overview.md` under *Resolved questions*, with
the reasoning and the rejected alternatives. Do not reopen them without reading that.

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
- Committed as four commits on `rewrite/phase-0-spec-and-conformance`.

### 2026-08-20 — Q1 resolved: error sets and `try`

- The first draft's error design did not work. `error` as a concrete `{message, kind}`
  struct left no type to name when a function calls two fallible things from different
  modules, and chapter 06's own example was incoherent — `ParseError` had no success
  variant, so a successful `parseInt` had nothing to return.
- Resolved as **error sets** (R1): the error position holds an enum or a union of enums,
  assignable by subset, so a function's set is the union of its callees'. Rejected
  interfaces because recovering the concrete type needs RTTI, which Ymir does not have.
  Prior art is Zig.
- Adopted **`try`** (R2) alongside it. Go's verbosity reputation is about lacking this
  operator, not about its error interface.
- Rewrote chapter 06; updated 01 (`try` keyword), 02 (union types, subset assignability,
  enums have no `nil`), 05 (matching a union, `nil` arm), 09 (grammar). Added Q10
  (positional nullability is a wart) and Q11 (set inference).
- Conformance: 23 cases, up from 17. Six new for error sets and `try`; the old
  `error_value_roundtrip` was rewritten since it predated the design.
- **Next:** Phase 1, the Go frontend. Nothing blocks it.

### 2026-08-20 — Phase 1: the Go frontend

- Go module `github.com/bjornaer/ymir`, Go 1.26. Packages: `compiler/token`,
  `compiler/lexer`, `compiler/ast`, `compiler/parser`, `compiler/diag`, `cmd/ymir`.
- `ymir parse` prints the syntax tree, or diagnostics with a source excerpt and a
  caret, exiting non-zero. All 23 conformance cases parse.
- Three legacy defects are foreclosed structurally rather than fixed: operators are
  matched by longest prefix over a closed set (`x==-3` lexes correctly), string
  escapes are decoded in the lexer, and comments never reach the parser.
- Two spec deviations found by implementing:
  - **Unary vs `**` precedence.** Spec 04 says `-x ** 2` is `-(x ** 2)`, so `**` binds
    tighter than unary minus. The obvious recursive-descent shape gets this wrong;
    a unary operand is parsed at the exponent level. Test `TestPrecedence` pins it.
  - **Match arms and multi-value return.** `A => return x, B => ...` and
    `A => return x, y` are the same shape and cannot be told apart without knowing
    the enum. A single-statement arm now cannot return multiple values; use a block.
    Spec 05 gained an §Arms section saying so.
- Spec gap noted, not yet resolved: `as` (import alias) and `default` (select) are
  parsed as contextual identifiers rather than keywords, which chapter 01's keyword
  list does not mention. Either reserve them or document them as contextual.
- **Next:** Phase 2, the type checker. Settle Q10 and Q11 early — both change the
  type representation.
- Added Phase 9 (editor support and distribution) as the deliberate last phase, and
  moved distribution out of Phase 6. The load-bearing decision recorded there: ship
  one LSP server and one tree-sitter grammar rather than per-editor plugins, so
  editor diagnostics are the compiler's own and cannot drift. Q12 filed from Phase 1.
