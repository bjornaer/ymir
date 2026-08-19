#!/usr/bin/env python3
"""Ymir conformance suite runner.

Implementation-agnostic: drives a command that executes a .ymr file, then checks
stdout and exit code against the `#@` directives in the file's header.

  python3 conformance/run.py --ymir "./bin/ymir run"
  python3 conformance/run.py --ymir "poetry run ymir run" --cwd ymir-legacy-py
"""
import argparse
import pathlib
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
CASES = ROOT / "cases"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


class Case:
    def __init__(self, path):
        self.path = path
        self.id = None
        self.spec = None
        self.exit = None          # int | "nonzero" | None
        self.stdout = None        # list[str] | None
        self.contains = None      # list[str] | None
        self.compile_error = None # list[str] | None
        self.skip = None
        self._parse()

    def _parse(self):
        block = None
        for raw in self.path.read_text().splitlines():
            line = raw.strip()
            if not line.startswith("#@"):
                if line.startswith("#") or not line:
                    continue
                break  # header ends at the first real line of code
            body = line[2:].strip()
            if body.startswith("|"):
                text = body[1:]
                if text.startswith(" "):
                    text = text[1:]
                if block is None:
                    raise ValueError(f"{self.path}: '|' continuation with no directive")
                block.append(text)
                continue
            parts = body.split(None, 1)
            key = parts[0]
            val = parts[1] if len(parts) > 1 else ""
            block = None
            if key == "case":
                self.id = val
            elif key == "spec":
                self.spec = val
            elif key == "exit":
                self.exit = "nonzero" if val == "nonzero" else int(val)
            elif key == "stdout":
                self.stdout = block = []
            elif key == "stdout-contains":
                self.contains = block = []
            elif key == "compile-error":
                self.compile_error = block = []
            elif key == "skip":
                self.skip = val or "no reason given"
            else:
                raise ValueError(f"{self.path}: unknown directive '{key}'")
        if not self.id:
            raise ValueError(f"{self.path}: missing 'case' directive")
        if not self.spec:
            raise ValueError(f"{self.path}: missing 'spec' directive")
        expected_id = self.path.relative_to(CASES).with_suffix("").as_posix()
        if self.id != expected_id:
            raise ValueError(f"{self.path}: case id '{self.id}' != path '{expected_id}'")

    def run(self, cmd, cwd, timeout):
        target = self.path if cwd is None else self.path.resolve()
        try:
            p = subprocess.run(
                shlex.split(cmd) + [str(target)],
                capture_output=True, text=True, timeout=timeout, cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            return [f"timed out after {timeout}s"]

        out, err, code = p.stdout, p.stderr, p.returncode
        fails = []

        if self.compile_error is not None:
            if code == 0:
                fails.append("expected a compile error, but the program ran and exited 0")
            for want in self.compile_error:
                if want not in err and want not in out:
                    fails.append(f"expected compile error mentioning {want!r}\n  stderr: {err.strip()[:400]!r}")
            return fails

        if self.exit == "nonzero" and code == 0:
            fails.append("expected a non-zero exit code, got 0")
        elif isinstance(self.exit, int) and code != self.exit:
            fails.append(f"exit code: want {self.exit}, got {code}\n  stderr: {err.strip()[:400]!r}")

        if self.stdout is not None:
            want = "\n".join(self.stdout)
            got = out.rstrip("\n")
            if got != want:
                fails.append(f"stdout mismatch\n  want: {want!r}\n  got:  {got!r}")

        if self.contains is not None:
            for want in self.contains:
                if want not in out:
                    fails.append(f"stdout missing {want!r}\n  got: {out.strip()[:400]!r}")

        return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ymir", required=True, help="command that runs a .ymr file")
    ap.add_argument("--cwd", default=None, help="working directory for the command")
    ap.add_argument("--filter", default="", help="only run cases whose id contains this")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--run-skipped", action="store_true")
    args = ap.parse_args()

    paths = sorted(CASES.rglob("*.ymr"))
    if not paths:
        print(f"no cases found under {CASES}", file=sys.stderr)
        return 1

    passed = failed = skipped = 0
    failures = []

    for path in paths:
        try:
            case = Case(path)
        except ValueError as e:
            print(f"{RED}MALFORMED{RESET} {e}")
            failed += 1
            continue

        if args.filter and args.filter not in case.id:
            continue
        if case.skip and not args.run_skipped:
            print(f"{YELLOW}SKIP{RESET} {case.id} {DIM}({case.skip}){RESET}")
            skipped += 1
            continue

        fails = case.run(args.ymir, args.cwd, args.timeout)
        if fails:
            failed += 1
            print(f"{RED}FAIL{RESET} {case.id} {DIM}[{case.spec}]{RESET}")
            failures.append((case, fails))
        else:
            passed += 1
            print(f"{GREEN}PASS{RESET} {case.id}")

    if failures:
        print(f"\n{RED}{'=' * 60}{RESET}")
        for case, fails in failures:
            print(f"\n{RED}FAIL{RESET} {case.id}  {DIM}({case.path.relative_to(ROOT.parent)}){RESET}")
            print(f"  spec: docs/spec/{case.spec}")
            for f in fails:
                print(f"  - {f}")

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
