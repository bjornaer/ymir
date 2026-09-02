# Ymir — Migration Plan

**Read this first if you are picking up cold.** It is the single source of truth for
where the project stands and what happens next. Update the *Status* and *Session log*
sections whenever you do meaningful work.

- **Last updated:** 2026-09-02
- **Current phase:** Phase 3 — bytecode and VM. In progress on `phase-3-bytecode-vm`.
- **Blocking:** nothing. R1–R10 are resolved. Q6 blocks Phase 5; Q14 blocks the
  `quantum/` cases and Phase 7.

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
docs/spec/            NORMATIVE language definition. Chapters 00-09.
conformance/          Executable form of the spec. run.py + 88 cases.
examples/tour.ymr     Exercises the full grammar. Keep it parsing.
ymir-legacy-py/       Frozen Python implementation. Reference only. Delete at Phase 8.

compiler/token/       EXISTS. Token kinds, closed operator set, positions.
compiler/lexer/       EXISTS. Maximal munch, escape decoding. Has tests.
compiler/ast/         EXISTS. Syntax tree, tree printer, Walk/Inspect.
compiler/parser/      EXISTS. Recursive descent over chapter 09. Has tests.
compiler/diag/        EXISTS. Errors with position, source excerpt, caret.
cmd/ymir/             EXISTS. CLI; `parse`, `check`, `build -S`, `run`.

compiler/types/       EXISTS. Semantic types, identity, assignability, universe.
compiler/check/       EXISTS. The whole Phase 2 checker. `ymir check` is the gate.
compiler/bytecode/    EXISTS. Instruction set, chunk, line table, disassembler.
vm/                   EXISTS. Tagged Value, stack machine, panics.

editor-support/       VSCode extension, outdated. Retargeted at Phase 9.
docs/                 Older prose docs. Superseded by docs/spec/ where they conflict.
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

### Phase 2 — Type checker  ✅ COMPLETE (2026-09-02)

**What Phase 1 left you.** A parsed `*ast.File` with positions on every node, and
`compiler/diag` for reporting. `ast.Type` is *syntax only* — what was written, not what
it means. Phase 2 introduces `compiler/types` for semantic types and resolves one to the
other. Nothing in the AST carries semantic information yet, and it should not; keep
resolved types in a side table keyed by node, so the AST stays a faithful record of the
source (this is what lets `ymir fmt` and the LSP reuse it later).

**Deliverables:** `compiler/types`, `compiler/check`, and a `ymir check <file>`
subcommand alongside `parse`.

**Scope of the work,** roughly in dependency order:

1. **Semantic types** — primitives, `array`/`map`/`tuple`/`matrix`/`chan`/`func`,
   named struct and enum types, unions, nullables. Identity is structural for the
   built-ins and nominal for struct and enum (chapter 02 §Assignability).
2. **Scope resolution** — the five scope levels of chapter 03. A real scope chain, not
   two flat maps. Module-level `var` must be visible inside every function in the
   module; case `scope/module_var_mutation` exists because legacy got this wrong.
3. **Local inference** — `:=` and `var x := e` only. Signatures are always annotated,
   so there is no global inference and no unification.
4. **Assignability** — identity, plus the two exceptions: union subset (`S ⊆ T`) and
   `T` → `?T`.
5. **Exhaustiveness** — over a single enum and over a union. Must name the missing
   variants in the error.
6. **Nullable handling (R3)** — rules N1–N6 of chapter 02: `?` is idempotent, `nil`
   belongs only to `?T`, `?T` must be narrowed before use as `T`, `?` rejects linear
   types, and narrowing on `if x != nil`.
7. **Definite assignment** — a function with a declared result must return on every
   path. Legacy returned "the last evaluated value", so a function's result depended on
   the shape of its final statement.
8. **Linearity (L1–L6)** — build it now, per decision D3, even though `qubit` does not
   arrive until Phase 7. The move/consume bookkeeping is the expensive part; adding the
   type to a checker already built around it is small. Retrofitting it is not.

**Two things that will cost more than expected:**

- **Error sets and unions (R1).** Union normalization, subset assignability,
  exhaustiveness across members, and `try`'s subset check. Harder than linearity.
- **Narrowing (R3/N6).** Deliberately minimal — exactly `x != nil` / `x == nil` on a
  binding, that branch only, not surviving reassignment. Resist generalizing it into
  flow typing; that is a much larger commitment and is not specified.

**Explicitly NOT in this phase:** error set inference (R4 — sets are written out, which
keeps this a single pass rather than a fixed-point over the call graph), user-facing
generics (Q3, undecided), and any execution.

**Decide early, both affect the type representation:** Q3 (generics) and Q5 (integer
overflow). Q12 (`as` and `default` as contextual identifiers) can wait for Phase 6.

**Done when:** every `compile-error` case reports the right error at the right position.
The suite has 13 such cases of 26; two are `quantum/` and stay skipped until Phase 7, so
**11 are in scope for this phase**:

```
decl/undefined_variable          scope/block_scope
types/no_implicit_conversion     types/nil_not_on_plain_type
types/nullable_needs_narrowing   match/exhaustiveness
errors/match_union_exhaustive    errors/match_unnarrowed_needs_nil
errors/error_set_not_superset    errors/try_requires_superset
errors/unhandled_is_compile_error
```

Add cases as you go — the suite is thin on the type system and should roughly double
during this phase.

**Milestones.** One self-contained commit each: builds, `go test ./... -count=1` green,
`gofmt` and `go vet` clean, and this file updated in the same commit.

- [x] **M0** — spec corrections + the illegal conformance case (2026-09-01)
- [x] **M1** — `compiler/types`: type representation, union normalization, identity,
      assignability, linearity predicate, universe scope (2026-09-01)
- [x] **M2** — `ast.Walk`, `compiler/check` skeleton, `ymir check`, and the
      `TestConformanceCasesCheck` gate with its expected-position table (2026-09-01)
- [x] **M3** — scope resolution (five levels, module pre-pass, imports, shadowing) (2026-09-01)
- [x] **M4** — literals, operators, local inference, assignability, constant
      folding (2026-09-01)
- [x] **M5** — calls, method sets, selection, return values (2026-09-01)
- [x] **M6** — composite literals and indexing (2026-09-01)
- [x] **M7** — nullables and narrowing (N1–N6) (2026-09-01)
- [x] **M8** — `match` exhaustiveness over enums and unions (2026-09-01)
- [x] **M9** — error sets, `try`, unhandled errors (2026-09-02)
- [x] **M10** — returns on every path, `main`'s signature (2026-09-02)
- [x] **M11** — linearity L1–L6, CI `ymir check -q` gate, phase close (2026-09-02)

**Position accuracy is enforced Go-side, not by `run.py`.** The runner checks only that
each `compile-error` substring appears somewhere in stdout or stderr, and never checks
line or column — a runtime failure printing the right word would pass it. The
`compiler/check` conformance test carries the expected `line:column` per case.

### Phase 3 — Bytecode and VM, minimal slice  ← START HERE

**What Phase 2 left you.** `compiler/types` answers every question about a type;
`compiler/check` resolves a parsed file against it and returns an `Info` side table —
`Types` keyed by `ast.Expr`, `Defs` and `Uses` keyed by `*ast.Ident`. Nothing is written
back onto the AST, so the bytecode compiler reads types out of `Info` rather than
re-deriving them. `ymir check <file>` exits 0 or reports with position and excerpt.

**Decide first, both block code generation:**

- **Q4 — does `main` return anything?** The checker currently requires `func main()` with
  no results. Changing it to `-> int` or `-> ?error` is a checker change *and* a runtime
  change, so decide before writing the entry sequence.
- **Q5 is already answered (R5): `int` overflow traps.** Every arithmetic opcode needs the
  check. Constant expressions already fail at compile time.

**Watch out for:** `?int` cannot be a bare int64 at runtime. Nullable primitives need a
tagged representation or boxing — flagged since R3 and still undecided. It is a VM
representation choice, not a semantic one; chapter 02 is normative on meaning only.

- Deliverables: `compiler/bytecode`, `vm/`, and `ymir run`. Enough for: `main`,
  `print`, `int` and `float` arithmetic, `if`/`while`, function calls, strings,
  `panic`, and module-level `var`.
- One engine. No fallback path, ever. If the VM cannot do something, that is a
  compile error, not a silent second implementation. `ymir run` type-checks before
  it executes, so nothing the checker rejects can ever run.

**The exit criterion was corrected on 2026-09-02.** It used to read "`decl/`,
`scope/`, `lexical/`, `types/`, `expr/`, `control/` pass", which was written against
a 26-case suite. The suite is now 85, and those six categories contain 15 run-cases
needing structs, methods, enums, `match`, arrays, maps, string concatenation, `str()`,
complex arithmetic, numeric conversions and runtime nullables — which is **Phase 4's
feature list**. The phase boundary moved, not the cases: nothing was weakened, no
assertion relaxed, and the eight run-cases that moved are covered by Phase 4's
criterion, which already requires every non-`concurrency`, non-`quantum` case to pass.

- **Done when**, under `python3 conformance/run.py --ymir "./bin/ymir run"`:
  - every `compile-error` case in the suite exits non-zero with its asserted message,
    which follows from `ymir run` type-checking first; and
  - these seven run-cases produce their asserted stdout at exit 0:
    `decl/main_entry_point`, `decl/main_returns_error`, `scope/forward_reference`,
    `scope/module_var_mutation`, `scope/shadowing`, `lexical/operator_munch`,
    `lexical/string_escapes`, `types/float_literal_arithmetic`.

**Milestones.** One self-contained commit each.

- [x] **M1** — record R9 and R10, correct the phase boundary, accept `main() -> ?error` (2026-09-02)
- [x] **M2** — `compiler/bytecode`: ops, chunk, line table, disassembler (2026-09-02)
- [x] **M3** — compiler and VM spine: `main` printing a literal, end to end (2026-09-02)
- [x] **M4** — arithmetic, comparison, and local variables (2026-09-02)
- [x] **M5** — control flow: `if`/`else`, `while`, `for`, short-circuit, `break` (2026-09-02)
- [x] **M6** — functions, frames, calls, module-level `var` as globals (2026-09-02)
- [ ] **M7** — strings, `panic` with a stack trace, exit codes, `main`'s error form
- [ ] **M8** — CI runs the suite; phase close and the Phase 4 brief

### Phase 4 — Full classical language

Structs, enums, `match`, arrays, maps, tuples, closures, methods, errors, complex
arithmetic and the numeric conversions.

Inherits the eight run-cases Phase 3's corrected criterion left behind:
`types/complex_literal`, `types/nullable_narrowing`, `types/narrowing_else_branch`,
`expr/method_call`, `expr/map_two_value_form`, `expr/array_bounds_panic`,
`control/for_in_runtime_array`, `control/terminating_statements`.

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
| R9 | Does `main` return `int` or `error`? | — | **resolved: `main()` or `main() -> ?error`** |
| R10 | How does the VM represent a value? `?int` is not a bare int64 | — | **resolved: one uniform tagged `Value`** |
| R5 | Integer overflow: wrap, trap, or saturate? | — | **resolved: traps** |
| Q6 | Data races on shared `array`/`map` between tasks | **Phase 5** | open |
| Q7 | Structured concurrency instead of Go's detached `spawn`? | Phase 5 | open |
| R6 | Immutability by default for locals (`let`/`mut`)? | — | **resolved: not in v1** |
| R3 | Should error-position nullability be written into the type? | — | **resolved: `?T`, general** |
| R4 | Should error sets be inferred? | — | **resolved: explicit for now** |
| Q12 | Are `as` and `default` reserved words or contextual identifiers? | Phase 6 | open, found in Phase 1 |
| Q14 | Where do the built-in quantum gates live? Not universe scope | Phase 7 | open, found in Phase 2 |
| Q15 | Order of module-level `var` initializers | — | open, found in Phase 3 |
| R7 | How is a `complex` value written? | — | **resolved: the parser folds `a ± bi`** |
| R8 | Is a container of a linear type linear, or ill-formed? | — | **resolved: ill-formed** |

R1–R10 are recorded in `docs/spec/00-overview.md` under *Resolved questions*, with the
reasoning and the rejected alternatives. Do not reopen them without reading that.

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
- **Next:** Phase 2, the type checker.
- Added Phase 9 (editor support and distribution) as the deliberate last phase, and
  moved distribution out of Phase 6. The load-bearing decision recorded there: ship
  one LSP server and one tree-sitter grammar rather than per-editor plugins, so
  editor diagnostics are the compiler's own and cannot drift. Q12 filed from Phase 1.

### 2026-08-20 — Q10 and Q11 resolved (R3, R4)

- **R3: `?T` is a general nullable type former**, not a positional rule. The earlier
  design made only the error position nullable, so one type name meant two things
  depending on where it sat, and parameters and fields could never be absent. Now
  `?int`, `array[?string]`, `func f(e: ?IOError)` all work, and the error position is
  just `?E`. `nil` belongs only to nullable types, so `match` on an ordinary enum still
  needs no `nil` arm. Narrowing is general. `?qubit` is rejected (rule N5).
- **R4: error sets stay explicit.** Inference is additive later and the reverse is not,
  so explicit-first is the reversible choice. It also keeps Phase 2's checker a single
  pass rather than a fixed-point computation over the call graph.
- Implemented `?` end to end: token, lexer, `ast.NullableType`, parser, printer. Spec
  chapters 00, 01, 02, 05, 06, 09 updated. All conformance cases and `examples/tour.ymr`
  moved to `?` notation; three cases added for narrowing, use-before-narrowing, and
  `nil` on a non-nullable type. 26 cases total.
- **Flagged for Phase 3, not yet decided:** `?int` cannot be a bare int64 at runtime.
  Nullable primitives need a tagged representation or boxing. That is a VM
  representation decision; chapter 02 is normative on semantics only.

### 2026-08-20 — Merged, and handoff audit

- PR #1 merged to `main`. Feature branch deleted; `main` is the working branch again.
- Verified from a clean clone: `go build`, `go test ./...`, and all 26 conformance cases
  parsing. 173 tracked files, `.claude/agents/` included.
- Handoff gaps found and closed: `CLAUDE.md` had no Go commands at all (a fresh session
  could not build); `PLAN.md` §3 described `compiler/` as planned rather than existing;
  the Phase 2 brief predated Phase 1 and mentioned neither R3's nullable work nor what
  the parser hands over.
- Phase 2 is now marked **START HERE** with a full brief: what Phase 1 left, the eight
  work items in dependency order, the two that will cost more than expected (unions and
  narrowing), what is explicitly out of scope, and the 11 conformance cases that define
  done.
- **Next session: read `PLAN.md`, then start Phase 2.** Nothing blocks it.

### 2026-09-01 — Phase 2 M0: spec corrections before any checker code

- Planned Phase 2 as eleven atomic milestones (M0–M10), listed above.
- **R5 — integer overflow traps.** Overflow on `int` is a runtime panic; overflow in a
  constant expression is a compile error, matching the existing const-division-by-zero
  rule. Rejected wrapping and saturating: both are silently wrong answers, the defect
  class the rewrite exists to remove. Costs a branch per arithmetic opcode in Phase 3.
- **R6 — no `let`/`mut` on locals in v1.** Immutability-by-default is the better default
  but adding `let` later is additive, whereas doing it now rewrites every example in the
  spec before a line of the checker exists. Same reversibility argument as R4.
- Six spec defects found while planning and fixed here, each one otherwise a place the
  checker would have invented semantics:
  - `errors/error_set_subset` matched an un-narrowed `?E` with no `nil` arm, which 05
    and 06 both make a compile error. **The case was wrong, not the rule** — a `nil` arm
    was added; `report` is never called with `nil`, so the asserted stdout is unchanged.
  - `error` was listed as a primitive with zero value `nil`, contradicting 06 (it is a
    predeclared enum) and 02 §Enums (enums have no `nil`). Row removed.
  - `any` was still in 01's predeclared identifiers though 02 says there is no `any`.
  - Assignability's two exceptions were never stated to **compose**, though the spec's
    own examples require it. Now written as four rules.
  - `chan` and `func` had zero value `nil`, which N3 forbids. They now have **no** zero
    value; `?chan[T]` is the form that may be absent.
  - "Returns on every path" had no definition. 05 now enumerates the terminating
    statements; an `if` with no `else` never terminates.
  - N6 did not say whether the `else` branch narrows. It does, and 02 has the table.
  - The type of a multi-valued `try` was unstated. 06 now says it inherits ch04's
    restriction on multi-valued calls.
- Conformance: 29 cases, up from 26. Added `types/const_overflow_is_error`,
  `types/chan_has_no_zero_value`, `decl/no_zero_value_needs_init` — the three new rules
  above that no existing case covered.
- **Next:** M1, `compiler/types`. Nothing blocks it.

### 2026-09-01 — Phase 2 M1: `compiler/types`

- `compiler/types` exists: `Basic`, `Named` (struct and enum, nominal identity by
  pointer), `Array`, `Map`, `Tuple`, `Matrix`, `Chan`, `Func`, `Union`, `Nullable`,
  `Qubit`, `QReg`, plus `Invalid` for recovery and `Nil` for the literal. No dependency
  on `ast`, `token` or `diag` — it answers questions and never reports.
- `NewUnion` normalizes on construction, so `A | B` and `B | A` are the same value and
  a one-member union *is* the bare enum. `Identical` can then compare members
  element-wise.
- `Assignable` implements the four composed rules M0 wrote into chapter 02. The cases
  that matter are covered by tests: `IOError` → `?(IOError | ParseError)` (rules 2 and 4
  together) and `?IOError` → `?(IOError | ParseError)`, which is what makes
  `errors/error_set_subset` typecheck.
- `Invalid` is assignable in both directions, so one bad expression will not produce a
  cascade of follow-on diagnostics.
- **Deliberate conservative reading, flagged for chapter 02.** The spec says linear
  means `qubit`, `qreg`, a struct transitively containing one, and an enum with a linear
  payload. It says nothing about `array[qubit]`. `IsLinear` treats a container of a
  linear type as linear, because the alternative lets a program duplicate a qubit by
  copying an array reference. The spec should say so before Phase 7.
- `HasZeroValue` encodes the M0 change: `chan` and `func` have none.
- 44 assertions across 10 table-driven tests. **Next:** M2, the walker, the `check`
  skeleton, `ymir check`, and the conformance gate.

### 2026-09-01 — Phase 2 M2: walker, checker skeleton, and the gate

- `ast.Walk` / `ast.Inspect`. There was no traversal in the repository; the
  printer's type switch was the only thing that knew which node has which
  children, and a second drifting copy inside `check` is how a checker starts
  silently skipping a construct. `TestWalkHandlesEveryNodeKind` greps `ast.go`
  for `^type X struct` and fails if any of the 55 node types is missing from the
  table, so adding a node without wiring the walk is a test failure rather than
  a rule that quietly stops being enforced.
- `compiler/check` skeleton: `Info` (the side table — `Types` keyed by
  `ast.Expr`, `Defs` and `Uses` keyed by `*ast.Ident`), `Object`, `ObjKind`, and
  `Check(file, name, src) (*Info, *diag.List)`. It checks nothing yet; M3
  onward hang off `checkFile`.
- `ymir check [-q] <file>`, sharing `finish` and a new `readSource` with
  `parse`. It refuses to check a tree the parser recovered in, because the
  synthetic `_`-named nodes would produce confident nonsense.
- **`TestConformanceCasesCheck` is the real Phase 2 gate.** `run.py` checks only
  that a `compile-error` substring appears somewhere in the output — no line, no
  column, and no way to tell a compile error from a runtime failure that printed
  the right word. This test carries the expected `line:column` per case, and
  asserts the other half too: every case *without* a `compile-error` header must
  check clean, so a false positive fails as loudly as a missed error.
- A compile-error case absent from the expectation table reports as *pending*
  rather than failing, so `go test ./compiler/check -v` is the Phase 2 progress
  report. Today: 16 pending, 13 checking clean.
- **Next:** M3, scope resolution. `decl/undefined_variable` and
  `scope/block_scope` are the two cases it turns green.

### 2026-09-01 — Parser fix: `qreg[N]` did not parse

- Found while writing M3's type resolution. Grammar 09 §Types specifies
  `"qreg" "[" IntLit "]"`, but `parseBaseType` only ever accepted *types* as
  arguments, so `var r: qreg[4]` produced three cascading syntax errors.
- Nothing caught it because **no conformance case used `qreg`** — the Phase 1
  gate only asserts that existing cases parse, and standing rule 2 is exactly
  about this: a rule with no case is not a rule.
- `ast.GenericType` gained `Width *BasicLit`, set only for `qreg`. It is not a
  type argument and does not belong in `Args`. Printer, walker and parser
  updated together.
- Added `quantum/qreg_register.ymr`, skipped like the other quantum cases but
  still subject to the parse gate, which is what would have caught this. 30
  cases.

### 2026-09-01 — Phase 2 M3: scope resolution and type resolution

- The five scope levels of chapter 03, as a real chain: block → parameters →
  file (imports only) → module → universe. File scope sits *inside* module
  scope, because that is the order resolution runs in.
- Module-scope symbols are collected in four passes before any body is checked:
  imports, then type *names*, then type *bodies*, then values. That is what makes
  declarations order-independent (the statement M0 added to chapter 03) and what
  lets two structs name each other.
- `ast.Type` → `types.Type` resolution, with the chapter 02 formation rules:
  map keys must be hashable, matrix elements float or complex, union members
  enums, and `?` rejects a linear type (N5). Every failure yields `Invalid`, so
  one bad annotation does not cascade.
- Resolution is a hand-written traversal, not `ast.Walk`. An `*ast.Ident` means
  five different things depending on where it sits — a reference, a declaration,
  a field name, a variant, a selector — and a uniform walk cannot tell them
  apart.
- **11 conformance cases green**, 12 pending. `decl/undefined_variable` at
  10:11 and `scope/block_scope` at 13:11 are the two PLAN.md named for this
  milestone; the other nine are new.
- **Spec addition:** chapter 02 §Enums said "where ambiguous, qualify it" without
  defining ambiguous. It now does — the bare name belongs to two enums in the
  module, it is not resolved by expected type, and an ordinary binding shadows a
  variant. Found by implementing it. Case `decl/ambiguous_variant`.
- Two bugs caught by writing the tests rather than the code: `:=` was applying
  Go's "at least one name is new" rule where chapter 03 is stricter, and
  parameter annotations were resolved twice, so every bad one was reported twice.
- 12 new conformance cases, 42 total, up from 30. Roughly half the doubling the
  Phase 2 brief asks for.
- **Next:** M4, local inference and assignability at every site.

### 2026-09-01 — Phase 2 M4: operators, inference, assignability, constant folding

- Milestones M4 and M5 swapped from the original plan. Inference cannot come
  before expression typing — `x := 1` needs the type of `1` — so M4 is now
  literals, operators, inference and assignability, and M5 is calls, composite
  literals, indexing and selection.
- The operand table of chapter 04, in full: identical operands with no promotion,
  `%` on `int` only, `complex` unordered, `==` on any unrestricted type, and
  linear values not comparable at all.
- Local inference for `:=` and `var x := e`, the only two things chapter 02
  infers. `v := nil` is an error, because nil belongs to every `?T` and so
  determines none of them.
- Assignability applied at annotated declarations, at `=`, and at `const`.
- **Constant folding**, memoized per node because it reports: R5's overflow and
  chapter 04's constant division by zero are compile errors, and running the fold
  twice reported them twice. `const A: int = 2` then `const B: int = A * 3`
  folds through the named constant.
- `if`/`while`/`for` conditions must be `bool` — no truthiness.
- **16 conformance cases green**, 7 pending. `examples/tour.ymr` is now held to
  the same bar as a clean case, and caught the one false positive this milestone
  produced: `v, ok := m["a"]` is the two-value map form, not an arity mismatch.
- **New open question Q13.** Chapter 02 gives `complex` the zero value
  `0.0 + 0.0i` and chapter 04 requires both operands of `+` to have identical
  types, so that expression is `float + complex` and does not typecheck. Complex
  values are currently unwritable except as a bare imaginary literal, and
  `complex` has no writable zero value at all. Filed rather than resolved: the
  fix is a language decision (a two-argument `complex(re, im)`, a single lexical
  form for `1.0+2.0i`, or the language's first implicit conversion).
- 5 new cases, 47 total, up from 42.
- **Next:** M5, calls and composite literals. That is what unblocks the two-value
  map form, multi-valued call arity, and most of what remains.

### 2026-09-01 — Phase 2 M5: calls, method sets, selection, returns

- `c.call` sorts out what a callee actually is — a builtin, a numeric
  conversion, an enum variant (bare or qualified), a module member, a method, or
  an ordinary function value — then checks exact arity and assignability.
  Chapter 04 allows no default parameters, no variadic user functions and no
  keyword arguments, so this is deliberately rigid.
- Method sets: one flat table per named type. Methods are not virtual, so that
  is the entire mechanism. A `mut` receiver requires a mutable base.
- Selection now distinguishes a struct field, a method value, a qualified
  variant, and a module member. An enum has no field access at all — it "is
  inspected only by match" — and the diagnostic says so.
- Return values are checked against the declared results, including the
  multi-valued-call-as-whole-return form. That is what turns
  `errors/error_set_not_superset` green, and it exercises the rule the whole
  error design rests on: a narrower set flows out through a wider declared one
  and not the reverse.
- `try` gets its *shape* here — the callee's results minus the error position —
  because without it every `data := try readFile(path)` in the suite reads as a
  multi-valued call in expression position. Its rules stay in M9.
- Quantum builtins report "not implemented yet" rather than typing. Allowing
  `qubit()` would let a program construct a linear value the linearity checker
  cannot yet track, which is worse than refusing.
- **21 conformance cases green**, 6 pending. 5 new cases, 52 total.
- Milestone list re-numbered: composite literals and indexing became their own
  milestone (M6), since calls alone was already a large change.
- **Next:** M6, composite literals and indexing. That unblocks the two-value map
  form and lets the M5 tests stop annotating what they should be inferring.

### 2026-09-01 — Phase 2 M6: composite literals and indexing

- Composite literals are the one place Ymir types **bidirectionally**, because
  chapter 04 says so: "Where the context supplies an expected type, that type
  wins." `exprWant` threads an expected type from an annotated declaration, an
  assignment, a call argument, a return, and a struct field. Nothing else
  consults it — every other expression has a type of its own.
- `[[1.0, 2.0], [3.0, 4.0]]` is a `matrix[float]` and `[[1, 2]]` is an
  `array[array[int]]`, per the rectangular-and-float-or-complex rule.
- Struct literals are exhaustive and by name, and the diagnostic lists the
  missing fields.
- Indexing: array by int, map by key (yielding two values in the destructuring
  form, which is the safe accessor), string by int yielding a byte, `qreg` by
  int yielding a qubit. Tuples use `t.0`, not brackets.
- **Refused rather than guessed:** chapter 02 specifies matrix *arithmetic* and
  never specifies indexing a matrix. `a[0]` on one reports that it is not
  defined in v1 rather than inventing a shape. Recorded here as a spec gap to
  close before a stdlib needs it.
- Assignment to a struct field requires a mutable base, since a struct has value
  semantics and a non-`mut` parameter is a copy. Indexing an array or map does
  not, because those are references.
- Bare payload-free enum variants are now values with the enum's type, which
  M5 had left as unknown. Found by a map literal keyed on one.
- **27 conformance cases green**, 6 pending — all six are `match`, `try`, and
  unhandled errors. 7 new cases, 59 total.
- **Next:** M7, nullables and narrowing. `types/nullable_needs_narrowing`
  already reports at the right place; it needs N4's message rather than the
  generic mismatched-types one.

### 2026-09-01 — Phase 2 M7: nullables and narrowing

- **Narrowing is a scope, not a side table.** The narrowed branch is checked in a
  scope holding a shadow binding of type `T`. Lexical scoping then gives N6's
  "that branch only" for free, and removing the shadow is what gives "does not
  survive reassignment of x".
- Both branches narrow, per the table M0 added to chapter 02: `if x != nil`
  narrows the `then`, `if x == nil` narrows the `else`. Neither narrows the
  other side.
- Deliberately syntactic and exact: `x != nil && true` does not narrow, and
  neither does `b.v != nil` on a field. Resisting the pull toward general flow
  typing is the point — the spec does not specify it, and it is a much larger
  commitment.
- Reassigning a narrowed binding restores the declared `?T`, so `v = nil` inside
  `if v != nil { ... }` is legal and the *next* use needs narrowing again. That
  came out of a hand-run rather than a test, and it caught a duplicated
  assignability check that was reporting the assignment against the narrowed
  type.
- N4 now has its own message — "?int must be narrowed before it is used as int"
  — instead of falling through to the generic mismatched-types one.
- **30 conformance cases green**, 5 pending. All five are `match`, `try`, and
  unhandled errors. 3 new cases, 62 total.
- **Next:** M8, `match` exhaustiveness over enums and unions.

### 2026-09-01 — Phase 2 M8: `match` exhaustiveness

- Exhaustiveness over a single enum and over a union, computed as every variant
  of every member plus the `nil` case when the scrutinee is an un-narrowed `?T`.
  **The error names the missing variants**, which is normative and is the whole
  mechanism: adding a variant breaks every `match` on it.
- Qualification required on a union, optional on a single enum. The qualifier
  must be a *member of the scrutinee*, not merely an enum in scope.
- Pattern bindings carry the payload's real type, so `Circle(r) => print(r + 1)`
  on `Circle(float)` reports a `float`/`int` mismatch rather than staying silent.
- A `nil` arm is required on an un-narrowed `?E` and forbidden on a narrowed one,
  which is what makes `if err != nil { match err { ... } }` read naturally.
- `errors/match_union_exhaustive` trips two rules at once — a missing variant and
  a missing `nil` arm — and both are reported. A nil-only diagnostic would fail
  the case, which asserts `UnexpectedEOF`.
- **Cascade suppressed:** when a pattern fails to resolve, coverage cannot be
  computed, so the exhaustiveness check is skipped rather than adding a second
  misleading error on top of the first.
- **Spec addition:** chapter 05 §Exhaustiveness now says arms are a set — two
  arms for one variant, two `_` arms, or two `nil` arms are each an error. It was
  unstated, and the second arm is unreachable.
- **35 conformance cases green, 2 pending.** 5 new cases, 67 total.
- **Next:** M9, error sets and `try`. `errors/try_requires_superset` and
  `errors/unhandled_is_compile_error` are the last two.

### 2026-09-01 — R7 and R8, recorded before the standby

- **R7 — a complex literal is `a ± bi`, folded by the parser.** `0.0 + 0.0i` was
  `float + complex` and did not typecheck, so `complex` had no writable zero value
  and the only expressible complex was a bare imaginary literal. Folding happens in
  the parser rather than the lexer deliberately: lexing `1.0+2.0i` as one token
  needs whitespace to decide where the literal ends, which is the maximal-munch
  ambiguity that made legacy lex `x==-3` as `x` `==-` `3`. Same surface language,
  no trap, no lexer change. **Not yet implemented** — chapters 02 and 04 are
  updated; the parser fold and its cases are still to do.
- **R8 — a container of a linear type is ill-formed.** `array[qubit]`,
  `map[K, qubit]`, `chan[qubit]` and `tuple[qubit, …]` are rejected where the type
  is written. Rule L1 needs each linear value proved consumed exactly once and a
  container's length is a runtime value, so treating the container as linear would
  promise a guarantee the checker cannot verify per element. `qreg[N]` is the
  collection-of-qubits type and its width is a compile-time constant. A struct may
  still hold a linear field, because its shape is static. Implemented, with case
  `types/container_of_linear_rejected`. This shapes the M11 lattice.
- `types.IsLinear` still answers honestly for containers, as a backstop rather
  than an assumption that the formation check is exhaustive.
- Session paused here at 22:40 CEST against a credit limit, with a wake-up armed
  for 01:55. 36 cases green, 2 pending, 68 total.
- **Also noted, additive, not now:** matrix indexing stays undefined (M6), but a
  slicing or index notation will be wanted before anyone writes real matrix code.
  Deliberately deferred rather than guessed.

### 2026-09-02 — Phase 2 M9: error sets, `try`, unhandled errors

- **All 11 conformance cases the Phase 2 brief named are green**, and so is every
  compile-error case added since. 70 of 73 cases pass the checker gate; the three
  that do not are the `quantum/` skips.
- An error position is the last result being `?E` for an error set `E` — so
  `-> ?IOError` has one and `-> ?int` does not. `ast.FuncDecl.HasErrorPosition`
  was only ever a `len(Results) > 1` heuristic; this is the real predicate.
- `try` now enforces all four static rules: the callee must be fallible, the
  enclosing function must have an error position, the callee's set must be a
  subset of the enclosing one, and every other result of the enclosing function
  must have a zero value. The subset hint names the widened set, which is the fix.
- Unhandled errors: a fallible call standing alone as a statement is an error
  naming the callee. `_, _ = f()`, binding and checking, and `try` are the three
  legal forms.
- **Binding an error and never reading it** is an error. Implemented with a read
  set, where an assignment target is explicitly *not* a read — `err = nil` does
  not count as handling it.
- Scoped deliberately to error bindings. Chapter 06 words the rule as though a
  general unused-binding rule existed, but no chapter states one, and inventing it
  would reject programs the spec permits. Recorded rather than guessed.
- 5 new cases, 73 total.
- **Next:** the R7 parser fold for complex literals, then M10 (returns on every
  path, `main`) and M11 (linearity, CI gate, phase close).

### 2026-09-02 — R7 implemented: complex literals fold in the parser

- `0.0 + 0.0i`, `1.0 - 2.0i` and `-1.0 + 2.0i` are each one literal of type
  `complex`. Folded in `parseBinaryExpr`, so `1.0+2.0i` and `1.0 + 2.0i` are the
  same program — a lexer-level fold would have made them differ, which is the
  whitespace-sensitivity R7 was chosen to avoid.
- Both operands must be literals. `x + 2.0i` for a `float` binding stays a
  `BinaryExpr` and the checker still rejects it, which is the point: no implicit
  conversion sneaks in through the back door.
- The folded literal reuses `ast.BasicLit` with kind `IMAG` and the whole text as
  its value, so no AST node, walker case, or printer case was added.
- `complex` gained a constant representation, so `const ZERO: complex = 0.0 + 0.0i`
  folds. Addition, subtraction and multiplication of complex constants work;
  division does not, and nothing needs it before Phase 3.
- 2 new cases, 75 total.

### 2026-09-02 — Phase 2 M10: returns on every path, and `main`

- The terminating-statement rules M0 wrote into chapter 05, implemented: `return`,
  `panic(...)`, a block whose last statement terminates, an `if` **with an else**
  where both branches do, a `match` where every arm does, and `while true` with no
  escaping `break`. Nothing else.
- The analysis is syntactic on purpose. It proves control always transfers; it
  never proves a condition is true. `for` and `while cond` do not terminate,
  because the checker does not prove they run at all.
- A `break` inside a *nested* loop belongs to that loop, so it does not make the
  outer `while true` exitable.
- Function literals are held to the same rule.
- `main` takes no parameters, declares no results, cannot be exported, and must
  not be called explicitly. A *method* named `main` is unaffected.
- "Exactly one module declares `main`" needs a whole-program view and waits for
  the module loader in Phase 6.
- 4 new cases, 79 total.
- **Next:** M11, linearity L1–L6, the CI gate, and the phase close.

### 2026-09-02 — Phase 2 M11: linearity, and the phase closes

- **Rules L1 through L6 are implemented and exercised from conformance cases**, not
  only from Go tests. That was not the plan: the brief assumed no linear value
  could exist before Phase 7. It can — a parameter may be declared `qubit` — and
  once allocation and disposal were allowed to *typecheck*, every rule became
  reachable from source.
- The state is one bit per binding, in a map that branches snapshot and restore.
  There is no dataflow lattice, because Ymir has no `goto` and no fallthrough, so
  control flow is the statement tree.
- **`mut` is now part of a function's type.** `func(mut qubit)` and `func(qubit)`
  are different types, because L3 turns on the difference: passing consumes,
  borrowing does not.
- **Chapter 08's allocation and disposal now typecheck** — `qubit()`, `qreg[N]()`,
  `measure`, `reset`, `discard`, `measure_all`, and the `bit` enum. That is
  decision D3 working as designed: the type rules are Phase 2's, the simulator is
  Phase 7's. `quantum/linear_unconsumed` is no longer skipped.
- **New open question Q14: where do the built-in gates live?** Adding `h`, `x`,
  `y`, `z`, `s`, `t` to universe scope was tried and reverted within the minute —
  `TestLoopHeaderBindingsAreScopedToTheLoop` failed because `print(x)` after the
  loop resolved to the Pauli-X gate instead of reporting `undefined: x`. Chapter 08
  never says what scope they are in. A `stdlib.quantum` module reached as
  `quantum.h(q)` is the likely answer. `quantum/no_cloning` and
  `quantum/qreg_register` stay skipped until it is settled.
- **Bug the gate caught:** indexing a `qreg` consumed the whole register. Chapter 08
  §Registers says indexing is a *borrow* and the register retains the obligation.
- **Bug the tests caught:** `restoreLinear` aliased the snapshot instead of copying
  it, so each branch mutated the baseline the join was about to compare against and
  L4 silently passed everything. Fixed, and the reason is in the comment.
- The Go gate no longer honours `run.py`'s `skip`. "Do not execute" and "do not
  typecheck" are different questions, and conflating them was quietly dropping the
  quantum cases from the gate. `checkerSkips` names the two that genuinely cannot
  be checked, with the reason.
- CI now type-checks every case that is meant to compile, plus the tour.
- 6 new cases, 85 total. **83 of 85 pass the checker gate.**

---

## Phase 2 is complete

Definition of done, from the Phase 2 brief: *every `compile-error` case reports the
right error at the right position.* All 11 cases the brief named do, and so do the
36 added since — position asserted in Go, because `run.py` checks neither line nor
column.

The other half holds too: every case without a `compile-error` header type-checks
clean, as does `examples/tour.ymr`.

**Suite: 26 cases at the start of Phase 2, 85 now.** The brief asked for roughly
double; it more than tripled.

**Resolved during the phase:** Q5 → R5 (overflow traps), Q8 → R6 (no `let`/`mut`),
Q13 → R7 (complex literals fold in the parser), and R8 (a container of a linear type
is ill-formed).

**Found and filed rather than guessed:** Q13 and Q14, matrix indexing left undefined,
`qreg[N]` not parsing at all, and eight spec defects corrected in M0.

**Next:** Phase 3. Answer Q4 first.

### 2026-09-02 — Remove the legacy Python CI

- `legacy-py-tests.yml` and `release.yml` deleted. Both ran against
  `ymir-legacy-py/`, both failed on every push, and both were pure noise: standing
  rule 6 says the Python implementation is frozen and not to be fixed, and Phase 8
  deletes it outright. CI that fails on code we have decided not to repair trains
  people to ignore CI.
- `release.yml` was failing in 0 seconds with no log at all — GitHub could not load
  the workflow. It built PyPI wheels for the legacy tree, which the Go
  implementation will never need; Phase 9 ships one cross-compiled static binary
  through GitHub Releases instead.
- `docs/releasing.md` marked superseded rather than deleted, like the other legacy
  prose docs.
- **Kept `conformance.yml`.** Its `validate-cases` job is Python, but it passes in
  13 seconds and earns its place: the Go gate's `#@` header parser is a deliberate
  reimplementation of `run.py`'s, and running both is how a divergence between them
  gets noticed. Its `run-suite` job stays `if: false` until Phase 3.
- CI on `main` is now `Go` and `Conformance`, both green.

### 2026-09-02 — Phase 3 M1: R9, R10, and a corrected phase boundary

- **R9 — `main` is `func main()` or `func main() -> ?error`, and nothing else.** The
  error form exists so `try` works in the entry point, which is the one function
  that calls everything else; without it, `main` is the single place R2's operator
  cannot be used. A non-nil result writes `str(err)` to stderr and exits 1.
  Rejected `-> int`: it competes with panic for the exit code's meaning and does
  nothing for `try`.
- **R10 — the VM uses one uniform tagged `Value`.** This dissolves the `?int`
  representation question R3 flagged rather than answering it: if no `int` is a bare
  machine word, `?int` needs no special case anywhere. Rejected boxing only
  nullables — one source type with two runtime representations that must be kept in
  agreement is the shape of legacy's dual-backend bug.
- **Corrected Phase 3's exit criterion**, which contradicted its own scope. It said
  six whole categories must pass; those categories now hold 15 run-cases needing
  structs, methods, enums, `match`, arrays, maps, `str()` and complex arithmetic —
  Phase 4's feature list, not Phase 3's. The criterion was written against a 26-case
  suite and the suite tripled underneath it.
- **The boundary moved, not the cases.** No case was weakened, no assertion relaxed,
  and the eight run-cases that moved are already covered by Phase 4's criterion.
  Every compile-error case in all six categories must still exit non-zero under
  `ymir run`.
- 2 new cases, 87 total.
- **Next:** M2, the instruction set and disassembler.

### 2026-09-02 — Phase 3 M2: the instruction set and disassembler

- `compiler/bytecode`: `Op`, `Instr`, `Chunk` (code, a parallel line table,
  an interned constant pool), `Function`, `Program`, and a disassembler.
- **A stack machine.** Registers are faster and harder to compile to and read;
  Phase 3 exists to pin down semantics. Nothing forecloses a register pass later,
  because bytecode is produced and consumed in the same process and is not a
  distributed artifact.
- **Arithmetic opcodes are typed** — `AddInt` and `AddFloat`, never one
  polymorphic `Add`. The checker already proved the operand types and put them in
  `check.Info`, so a typed opcode spends information we have rather than
  re-deriving it at runtime. It also puts R5's overflow trap only on the `int`
  opcodes, leaving `float` to IEEE.
- Equality is *not* typed, because chapter 04 defines `==` on any unrestricted
  type; it dispatches on the value's kind. Ordered comparison is typed.
- The line table is parallel to the code, so a panic can build the stack trace
  chapter 06 requires.
- **The disassembler is written before the compiler that feeds it**, because
  every milestone after this one is debugged through it. It annotates operands
  with what they resolve to, and prints `<no such constant>` for a dangling index
  rather than a bare number that reads as fine.
- `bytecode` does not import `vm`. The dependency runs the other way, so the
  runtime's `Value` representation (R10) stays the runtime's business and the
  compile-time `Const` is its own type.
- **Next:** M3, the compiler and VM spine — `main` printing a literal, end to end.

### 2026-09-02 — Phase 3 M3: the pipeline is real

- `ymir run conformance/cases/decl/main_entry_point.ymr` prints `main ran` and
  exits 0, through parse → check → compile → bytecode → VM. That is the whole
  point of this milestone: the pipeline exists end to end before it is widened.
- **The suite went from 0 passed to 65 passed, 19 failed, 3 skipped.** The 65 are
  every compile-error case, which now exit non-zero with their asserted message
  because `ymir run` type-checks first, plus the two run-cases needing nothing
  but `print` of literals. All 19 failures are run-cases waiting on M4–M7.
- **A construct the compiler cannot yet handle reports with a position and exits
  non-zero** — `a binary operator is not implemented yet` at 14:12 — rather than
  compiling to nothing. Compiling to nothing is exactly how legacy's `func main()`
  became a silent no-op, and `TestUnimplementedConstructsReportRatherThanVanish`
  pins it.
- `vm.Value` is R10's uniform tagged struct. A whole float prints as `4.0`, not
  `4`, or a float and an int would be indistinguishable in output — which
  `types/float_literal_arithmetic` asserts.
- Panics carry a stack trace built from the chunk's line table, as chapter 06
  requires, and exit 2.
- `ymir build -S` prints the listing. `ymir build` without it says writing an
  executable is Phase 6 rather than doing nothing.
- **Next:** M4, arithmetic with R5's overflow trap.

### 2026-09-02 — Phase 3 M4: arithmetic, comparison, and locals

- Locals came in with arithmetic rather than waiting for M5, because the two
  target cases both need them — `x := 3` before `x == -3 + 6` means anything.
- **A local needs no store instruction.** Its initializer is already on top of
  the stack, and that slot *is* the local. The invariant is that after every
  statement the stack holds exactly the frame's live locals, which `endScope`
  maintains by popping. The VM's `OpCall` was corrected to match: it no longer
  pre-pushes slots, because locals push themselves as they are declared.
- The opcode for an operator is chosen from the type the checker already proved,
  so `x / 2.0` emits `DivFloat` and never asks a question at runtime.
- **R5's overflow trap is implemented and tested** on `+`, `-`, `*`, `**`, unary
  `-`, and `MinInt64 / -1`. Float is left to IEEE, where chapter 04 says division
  by zero yields an infinity — the typed opcodes are what let the two differ
  without a runtime check.
- **70 passed, 14 failed, 3 skipped.** Green this milestone:
  `lexical/operator_munch`, `types/float_literal_arithmetic`,
  `scope/forward_reference`, `scope/module_var_mutation`,
  `errors/discard_with_blank_is_legal`.
- `TestUnimplementedConstructsReportRatherThanVanish` now probes an array
  literal, since `:=` is implemented. It needs a still-pending construct each
  milestone — and when nothing is left to probe, the compiler has caught up with
  the checker.
- **Next:** M5, control flow. `scope/shadowing` is its target.

### 2026-09-02 — Phase 3 M5 and M6: control flow, and a global that was never initialized

- `if`/`else`, `while`, the C-style `for`, `break`, `continue`, `++`/`--`, and
  short-circuiting `&&`/`||`. Chapter 04 makes short-circuit evaluation
  normative rather than an optimization — the right operand may have effects —
  so it is lowered to jumps rather than evaluated and discarded.
- M6's targets were already green from M4, since a call with parameters needed
  frames and locals to work at all. Its remaining work was one real bug.
- **`scope/module_var_mutation` was passing for the wrong reason.** Module-level
  `var` initializers were never compiled, so a global held the zero `Value` —
  whose numeric payload is 0 — and `total = total + 10` produced 10 while the
  initializer had never run. `var name: string = "hello"` printed `nil`.
- Fixed with a synthetic `<init>` function the VM runs before `main`, and case
  `scope/module_var_initializer`, which would have caught it. This is precisely
  what standing rule 2 is for: the rule existed, the case did not, so the rule
  was not enforced.
- **New open question Q15: in what order do module-level initializers run?**
  Declaration order today, so `var a: int = b` reads `b`'s zero value when `b` is
  declared below. Silent, and silence is the objection. The alternatives are
  making a forward reference an error, or dependency ordering as Go does.
- `TestNoJumpIsLeftUnpatched` walks every compiled form and asserts no jump still
  carries its placeholder. An unpatched jump sends the VM to a wild pc and is
  invisible until some branch happens to be taken.
- **73 passed, 12 failed, 3 skipped.** Green: `scope/shadowing`,
  `types/narrowing_else_branch`, `scope/module_var_initializer`.
- **Next:** M7. `decl/main_returns_error` is the last Phase 3 target, and needs
  destructuring a multi-valued call.
