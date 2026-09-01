# Ymir — Migration Plan

**Read this first if you are picking up cold.** It is the single source of truth for
where the project stands and what happens next. Update the *Status* and *Session log*
sections whenever you do meaningful work.

- **Last updated:** 2026-09-01
- **Current phase:** Phase 2 — type checker. In progress on `phase-2-typechecker`.
- **Blocking:** nothing. R1–R6 are resolved; Q6 blocks Phase 5, Q4 blocks Phase 3.

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
conformance/          Executable form of the spec. run.py + 30 cases.
examples/tour.ymr     Exercises the full grammar. Keep it parsing.
ymir-legacy-py/       Frozen Python implementation. Reference only. Delete at Phase 8.

compiler/token/       EXISTS. Token kinds, closed operator set, positions.
compiler/lexer/       EXISTS. Maximal munch, escape decoding. Has tests.
compiler/ast/         EXISTS. Syntax tree, tree printer, Walk/Inspect.
compiler/parser/      EXISTS. Recursive descent over chapter 09. Has tests.
compiler/diag/        EXISTS. Errors with position, source excerpt, caret.
cmd/ymir/             EXISTS. CLI; `parse` and `check`.

compiler/types/       EXISTS. Semantic types, identity, assignability, universe.
compiler/check/       EXISTS. Skeleton + the conformance gate. Rules land M3-M10.
compiler/bytecode/    PHASE 3.
vm/                   PHASE 3.

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

### Phase 2 — Type checker  🚧 IN PROGRESS

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
- [ ] **M3** — scope resolution (five levels, module pre-pass, imports, shadowing)
- [ ] **M4** — local inference (`:=` and `var x := e`) and assignability at every site
- [ ] **M5** — expression typing, calls, composite literals, constant folding
- [ ] **M6** — nullables and narrowing (N1–N6)
- [ ] **M7** — `match` exhaustiveness over enums and unions
- [ ] **M8** — error sets, `try`, unhandled errors
- [ ] **M9** — returns on every path, `main`'s signature
- [ ] **M10** — linearity L1–L6, CI `ymir check -q` gate, phase close

**Position accuracy is enforced Go-side, not by `run.py`.** The runner checks only that
each `compile-error` substring appears somewhere in stdout or stderr, and never checks
line or column — a runtime failure printing the right word would pass it. The
`compiler/check` conformance test carries the expected `line:column` per case.

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
| R5 | Integer overflow: wrap, trap, or saturate? | — | **resolved: traps** |
| Q6 | Data races on shared `array`/`map` between tasks | **Phase 5** | open |
| Q7 | Structured concurrency instead of Go's detached `spawn`? | Phase 5 | open |
| R6 | Immutability by default for locals (`let`/`mut`)? | — | **resolved: not in v1** |
| R3 | Should error-position nullability be written into the type? | — | **resolved: `?T`, general** |
| R4 | Should error sets be inferred? | — | **resolved: explicit for now** |
| Q12 | Are `as` and `default` reserved words or contextual identifiers? | Phase 6 | open, found in Phase 1 |

R1–R6 are recorded in `docs/spec/00-overview.md` under *Resolved questions*, with the
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
