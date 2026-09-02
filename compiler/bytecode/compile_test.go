package bytecode_test

import (
	"strings"
	"testing"

	"github.com/bjornaer/ymir/compiler/bytecode"
	"github.com/bjornaer/ymir/compiler/check"
	"github.com/bjornaer/ymir/compiler/parser"
)

// compileSrc runs the whole front half of the pipeline the way `ymir run` does.
func compileSrc(t *testing.T, src string) (*bytecode.Program, string) {
	t.Helper()
	file, errs := parser.ParseFile("t.ymr", src)
	if !errs.Empty() {
		t.Fatalf("source does not parse:\n%s", errs.Render())
	}
	info, errs := check.Check(file, "t.ymr", src)
	if !errs.Empty() {
		t.Fatalf("source does not type-check:\n%s", errs.Render())
	}
	prog, errs := bytecode.Compile(file, info, "t.ymr", src)
	return prog, errs.Render()
}

func listing(t *testing.T, src string) string {
	t.Helper()
	prog, errs := compileSrc(t, src)
	if errs != "" {
		t.Fatalf("compile reported:\n%s", errs)
	}
	var b strings.Builder
	if err := prog.Disassemble(&b); err != nil {
		t.Fatalf("Disassemble: %v", err)
	}
	return b.String()
}

func TestCompilesMainPrintingALiteral(t *testing.T) {
	got := listing(t, "module t\n\nfunc main() {\n    print(\"main ran\")\n}\n")
	for _, want := range []string{"func main/0", "entry point", `; "main ran"`, "Print", "Return"} {
		if !strings.Contains(got, want) {
			t.Errorf("listing does not contain %q:\n%s", want, got)
		}
	}
}

func TestLiteralsBecomeConstants(t *testing.T) {
	got := listing(t, `module t

func main() {
    print(1)
    print(2.5)
    print("s")
    print(true)
    print(1.0 + 2.0i)
}
`)
	for _, want := range []string{"; 1", "; 2.5", `; "s"`, "True", "; 1+2i"} {
		if !strings.Contains(got, want) {
			t.Errorf("listing does not contain %q:\n%s", want, got)
		}
	}
}

func TestFunctionsGetIndicesBeforeAnyBodyIsCompiled(t *testing.T) {
	// A call may name a function declared later (chapter 03 §Scope), so the
	// call site needs its index before the callee is compiled.
	prog, errs := compileSrc(t, `module t

func main() {
    later()
}

func later() {
    print("ok")
}
`)
	if errs != "" {
		t.Fatalf("compile reported:\n%s", errs)
	}
	if len(prog.Funcs) != 2 {
		t.Fatalf("compiled %d functions, want 2", len(prog.Funcs))
	}

	var b strings.Builder
	_ = prog.Disassemble(&b)
	if !strings.Contains(b.String(), "; later/0") {
		t.Errorf("the call site does not resolve to later:\n%s", b.String())
	}
}

func TestMainIsFoundAndItsFormRecorded(t *testing.T) {
	prog, _ := compileSrc(t, "module t\n\nfunc main() {\n    print(1)\n}\n")
	if prog.Main < 0 {
		t.Fatal("main was not found")
	}
	if prog.MainReturnsError {
		t.Error("plain main must not be marked as returning an error")
	}

	// R9's second form.
	prog, _ = compileSrc(t, "module t\n\nfunc main() -> ?error {\n    return nil\n}\n")
	if !prog.MainReturnsError {
		t.Error("main() -> ?error must be marked as returning an error")
	}
}

func TestModuleVarsBecomeGlobals(t *testing.T) {
	prog, _ := compileSrc(t, `module t

var total: int = 0

func main() {
    print(1)
}
`)
	if len(prog.Globals) != 1 || prog.Globals[0] != "total" {
		t.Errorf("globals = %v, want [total]", prog.Globals)
	}
}

func TestUnimplementedConstructsReportRatherThanVanish(t *testing.T) {
	// The failure mode this guards against is legacy's: `func main()` compiled
	// to nothing and the program silently did nothing. A construct the checker
	// accepts but the compiler cannot yet handle must say so, with a position.
	//
	// An array literal is the probe because arrays are Phase 4. As each
	// milestone lands, this test needs a construct that is still pending —
	// which is the point: when nothing is left to probe, the compiler has caught
	// up with the checker.
	_, errs := compileSrc(t, "module t\n\nfunc main() {\n    var xs: array[int] = [1, 2]\n    print(1)\n}\n")
	if errs == "" {
		t.Fatal("an array literal compiled silently; arrays are not implemented yet")
	}
	for _, want := range []string{"not implemented yet", "t.ymr:4"} {
		if !strings.Contains(errs, want) {
			t.Errorf("diagnostics do not contain %q:\n%s", want, errs)
		}
	}
}

func TestEveryFunctionEndsInAReturn(t *testing.T) {
	prog, _ := compileSrc(t, "module t\n\nfunc main() {\n    print(1)\n}\n")
	code := prog.Funcs[prog.Main].Chunk.Code
	if len(code) == 0 {
		t.Fatal("main compiled to nothing")
	}
	if last := code[len(code)-1].Op; last != bytecode.OpReturn {
		t.Errorf("main ends in %s, want Return; the VM would run off the end", last)
	}
}

func TestLineTableTracksTheSource(t *testing.T) {
	prog, _ := compileSrc(t, "module t\n\nfunc main() {\n    print(1)\n}\n")
	chunk := &prog.Funcs[prog.Main].Chunk
	if got := chunk.LineAt(0); got != 4 {
		t.Errorf("first instruction is on line %d, want 4; a stack trace would point at the wrong place", got)
	}
}
