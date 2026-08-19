# Ymir — working notes for Claude

## Read these first

1. **[`PLAN.md`](PLAN.md)** — current phase, what's blocking, session log. Start here.
2. **[`docs/spec/`](docs/spec/)** — the normative language definition. Chapter 00 has
   the locked decisions and the open questions.
3. **[`conformance/README.md`](conformance/README.md)** — how the spec is tested.

For deep compiler work, use the `ymir-compiler` agent (`.claude/agents/`).

## What this project is

Ymir is being rewritten from Python to Go: a statically typed language with ADTs,
**error sets** (errors as values, `-> (T, IOError | ParseError)`, propagated with
`try`), Go-style concurrency, and a **linearly typed quantum fragment** where
no-cloning and use-after-measurement are compile errors. Execution is a bytecode VM
shipped as one static binary.

The old Python implementation is **frozen** at `ymir-legacy-py/`. It is a reference
for what the language used to do, not an authority on what it should do.

## Standing rules

1. **The spec is normative.** If an implementation disagrees with `docs/spec/`, the
   implementation is the bug. Changing the spec is a deliberate, separate commit that
   states what it invalidates.
2. **No feature without a conformance case.** Adding behavior means adding a case in
   `conformance/cases/`. A rule with no case is not a rule.
3. **Never weaken a conformance case to make code pass.** Fix the code, or change the
   spec and say so.
4. **One execution engine.** Never add a second backend or a "fast path" fallback. The
   legacy implementation's worst bug — `func main()` running under one engine and
   silently doing nothing under the other — came from exactly this.
5. **No silent failure.** Every error path exits non-zero. No bare `except`/`recover`
   that swallows an error. Legacy's CLI always exited 0, which made its CI incapable
   of failing.
6. **Do not fix `ymir-legacy-py/`.** It is frozen. Its bugs are documentation.

## Things that look wrong but are intentional

- `docs/spec/08-quantum.md` specifies a fragment nothing implements. That is decision
  D3: linear typing constrains the type checker's core design and cannot be retrofitted.
- The linearity machinery (chapter 02, rules L1–L6) is built in Phase 2, months before
  any linear type exists. Same reason.
- Older docs (`docs/context.md`, `docs/syntax_guidelines.md`, `docs/concurrency.md`,
  `docs/stdlib_reference.md`) describe the legacy language and contain disproved
  claims. Kept for history. `docs/spec/` wins on every conflict.
- `conformance/` cases currently fail. That is the point — they assert the target
  behavior, and the legacy baseline is 2 passed / 15 failed.

## Commands

```bash
# conformance against the Go implementation (once it exists)
python3 conformance/run.py --ymir "./bin/ymir run"

# conformance against the frozen Python reference
python3 conformance/run.py --ymir "poetry run ymir run" --cwd ymir-legacy-py

# legacy test suite (needs Python 3.13 — it does NOT build on 3.14)
cd ymir-legacy-py && poetry run pytest --no-cov -q
```

`poetry install` fails on Python 3.14: llvmlite 0.43 has no 3.14 wheel and
`pyproject.toml` allows `<3.15`. Setup steps are in `ymir-legacy-py/README.md`.

## Conventions

- Go code: standard `gofmt`, no exceptions. Package layout per `PLAN.md` §3.
- Compiler errors carry file, line, column, and a source excerpt. This is a hard
  requirement from Phase 1, not a polish item.
- Commit messages state what changed in the *language*, not just in the code. A commit
  that changes observable behavior names the conformance cases it affects.
- Update `PLAN.md`'s *Session log* and *Current phase* when you do meaningful work.
