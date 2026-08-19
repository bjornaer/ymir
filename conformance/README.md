# Ymir Conformance Suite

Executable form of `/docs/spec/`. Every normative rule in the spec **SHOULD** have a
case here. A spec change without a corresponding case change is incomplete.

This suite is the contract between the frozen Python implementation and the Go one.
It is deliberately implementation-agnostic: it drives a binary, reads stdout and the
exit code, and knows nothing else.

## Running

```bash
python3 conformance/run.py --ymir <command to run a .ymr file>

# against the Go implementation (once it exists)
python3 conformance/run.py --ymir "./bin/ymir run"

# against the frozen Python one
python3 conformance/run.py --ymir "poetry run ymir run" --cwd ymir-legacy-py
```

Exit code is 0 only if every non-skipped case passes.

## Case format

One case per `.ymr` file under `cases/<category>/`. Expectations live in a `#@` header
block at the top of the file, so the program and its contract are never separated.

```ymr
#@ case scope/module_var_mutation
#@ spec 03-declarations.md#scope
#@ exit 0
#@ stdout
#@ | 10

module m
var total: int = 0
func bump() { total = total + 10 }
func main() {
    bump()
    print(total)
}
```

### Directives

| Directive | Meaning |
|---|---|
| `case <id>` | unique identifier; **MUST** match the file's path under `cases/` |
| `spec <file>#<anchor>` | the spec section this case pins; required |
| `exit <n>` | required exit code |
| `exit nonzero` | any non-zero exit code |
| `stdout` + `\| <line>` | exact expected stdout, line by line |
| `stdout-contains` + `\| <text>` | substring match, for messages whose exact wording is not normative |
| `compile-error` + `\| <text>` | **MUST** fail before execution; stderr contains each text |
| `skip <reason>` | not yet expected to pass; reported, not failed |

`stdout` is matched exactly after stripping one trailing newline. Use
`stdout-contains` wherever the spec does not fix the exact wording — error message
text is not normative, error *presence* is.

## Categories

| Category | Chapter |
|---|---|
| `lexical/` | 01 |
| `types/` | 02 |
| `decl/`, `scope/`, `module/` | 03 |
| `expr/` | 04 |
| `control/`, `match/` | 05 |
| `errors/` | 06 |
| `concurrency/` | 07 |
| `quantum/` | 08 |

## Rules

1. A case asserts **one** rule. If it fails, the reason must be unambiguous.
2. Cases that encode legacy defects use `skip` with a reason naming the defect, so the
   suite is honest about what does not yet work rather than omitting it.
3. Never weaken a case to make an implementation pass. Fix the implementation, or
   change the spec and say so in the commit message.
