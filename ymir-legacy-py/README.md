# ymir-legacy-py — Reference Implementation (frozen)

This directory holds the original Python implementation of Ymir (v0.2.1). It is
**frozen**. No new language features land here.

## Why it still exists

It is the *executable reference* used to build the conformance suite while the Go
implementation is written. When a spec question is ambiguous, this is where you go
to see what the language actually did. Once the Go implementation passes the full
conformance suite, this directory is deleted in one commit.

See `/docs/spec/` for the normative language definition and `/PLAN.md` for the
migration plan.

## Status: known-broken

The suite reports `278 passed, 5 skipped`, but that green is misleading. The tests
pin Python-internal behavior, not language behavior. Verified defects:

| Defect | Evidence |
|---|---|
| `func main()` is a silent no-op in interpreter mode, but runs in LLVM/auto mode | `ymir run f.ymr -i` prints nothing; `ymir run f.ymr` prints |
| Globals are invisible inside functions | `var total: int = 0` + `func f() { total = total + 1 }` → `Undefined variable: total` |
| Type checker types a float literal as `None` | `func half(x: float) -> float { return x / 2.0 }` → `Type mismatch: float / None` |
| Lexer merges adjacent operators | `x==-3` lexes as one `==-` token → SyntaxError |
| `ymir run` always exits 0 | Five bare `except Exception` in `ymir/cli/ymir_cli.py` print and swallow |
| CI "examples" job cannot fail | Consequence of the above; `examples/concurrency_demo.ymr` errors and CI stays green |
| LLVM: every function parameter is lowered to `i32` | `tools/codegen.py:216` indexes `param_types` (a `List[Type]`) as a dict; membership is always false |
| LLVM: `visit()` is `@functools.lru_cache`'d | `tools/codegen.py:161` memoizes a side-effecting IR emitter, 128-entry cap |

Do not "fix" these. They are recorded so the Go implementation does not reproduce
them, and so conformance tests can be written to assert the *correct* behavior.

## Running it

`poetry install` fails on Python 3.14 (llvmlite 0.43 has no 3.14 wheel, and
`pyproject.toml` allows `<3.15`). Use 3.13:

```bash
poetry env use $(pyenv prefix 3.13.7)/bin/python3.13
poetry run pip install "llvmlite==0.44.0" click toml requests pandas numpy \
    aiohttp gitpython pytest pytest-asyncio pytest-mock pytest-timeout pytest-cov
poetry run pip install -e . --no-deps
poetry run pytest --no-cov -q
```
