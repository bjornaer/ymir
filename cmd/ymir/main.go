// Command ymir is the Ymir toolchain.
//
// Phase 1 provides `parse` only. Execution arrives with the VM in Phase 3; see
// PLAN.md. There is exactly one execution engine by design, so there is no
// interpreter/compiler mode flag and there never will be.
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/diag"
	"github.com/bjornaer/ymir/compiler/lexer"
	"github.com/bjornaer/ymir/compiler/parser"
)

const usage = `ymir - the Ymir toolchain

usage:
  ymir parse [-tokens] <file.ymr>   parse a file and print its syntax tree
  ymir version

Phase 1 of the rewrite: the frontend only. Running programs arrives in Phase 3.
See PLAN.md and docs/spec/.
`

func main() { os.Exit(run()) }

func run() int {
	if len(os.Args) < 2 {
		fmt.Fprint(os.Stderr, usage)
		return 2
	}

	switch os.Args[1] {
	case "parse":
		return cmdParse(os.Args[2:])
	case "version":
		fmt.Println("ymir 0.3.0-dev (phase 1: frontend)")
		return 0
	case "-h", "--help", "help":
		fmt.Print(usage)
		return 0
	}

	fmt.Fprintf(os.Stderr, "ymir: unknown command %q\n\n%s", os.Args[1], usage)
	return 2
}

func cmdParse(args []string) int {
	fs := flag.NewFlagSet("parse", flag.ContinueOnError)
	showTokens := fs.Bool("tokens", false, "print the token stream instead of the tree")
	quiet := fs.Bool("q", false, "report errors only; print nothing on success")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if fs.NArg() != 1 {
		fmt.Fprint(os.Stderr, "usage: ymir parse [-tokens] [-q] <file.ymr>\n")
		return 2
	}

	path := fs.Arg(0)
	src, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ymir: %v\n", err)
		return 1
	}

	// Report paths relative to the working directory when that is shorter, so
	// diagnostics stay readable.
	name := path
	if cwd, err := os.Getwd(); err == nil {
		if rel, err := filepath.Rel(cwd, path); err == nil && len(rel) < len(path) {
			name = rel
		}
	}

	if *showTokens {
		errs := diag.NewList(name, string(src))
		for _, t := range lexer.Tokens(name, string(src), errs) {
			fmt.Printf("%-16s %s\n", t.Pos, t)
		}
		return finish(errs)
	}

	file, errs := parser.ParseFile(name, string(src))
	if errs.Empty() && !*quiet {
		if err := ast.Fprint(os.Stdout, file); err != nil {
			fmt.Fprintf(os.Stderr, "ymir: %v\n", err)
			return 1
		}
	}
	return finish(errs)
}

// finish renders diagnostics and picks the exit code.
//
// A non-zero exit on failure is normative (spec 06 §panic). The legacy CLI
// caught every exception and exited 0, which made its CI incapable of failing.
func finish(errs *diag.List) int {
	if errs.Empty() {
		return 0
	}
	errs.Sort()
	fmt.Fprint(os.Stderr, errs.Render())
	n := errs.Len()
	noun := "errors"
	if n == 1 {
		noun = "error"
	}
	fmt.Fprintf(os.Stderr, "\n%d %s\n", n, noun)
	return 1
}
