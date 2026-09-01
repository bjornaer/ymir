package check_test

import (
	"strings"
	"testing"

	"github.com/bjornaer/ymir/compiler/check"
	"github.com/bjornaer/ymir/compiler/parser"
	"github.com/bjornaer/ymir/compiler/types"
)

// checkSrc parses and checks a source string, failing the test if it does not
// parse. It is the helper every later milestone's tests build on.
func checkSrc(t *testing.T, src string) (*check.Info, string) {
	t.Helper()
	file, errs := parser.ParseFile("test.ymr", src)
	if !errs.Empty() {
		t.Fatalf("source does not parse:\n%s", errs.Render())
	}
	info, errs := check.Check(file, "test.ymr", src)
	return info, errs.Render()
}

// wrap puts statements inside a module and a main function.
func wrap(stmts string) string {
	return "module t\n\nfunc main() {\n" + stmts + "\n}\n"
}

func TestCheckReturnsUsableInfo(t *testing.T) {
	info, rendered := checkSrc(t, wrap("    print(1)"))
	if rendered != "" {
		t.Fatalf("unexpected diagnostics:\n%s", rendered)
	}
	if info == nil {
		t.Fatal("Check returned a nil Info")
	}
	if info.Types == nil || info.Defs == nil || info.Uses == nil {
		t.Error("Info maps must be allocated, so callers can read them without a nil check")
	}
}

func TestTypeOfIsInvalidForUnvisitedNodes(t *testing.T) {
	// A missing key means "never visited", and must not be mistaken for a
	// successfully inferred type. Nothing is visited yet at this milestone.
	info, _ := checkSrc(t, wrap("    print(1)"))
	if got := info.TypeOf(nil); got != types.Type(types.Invalid) {
		t.Errorf("TypeOf(unvisited) = %s, want invalid type", got)
	}
	if info.ObjectOf(nil) != nil {
		t.Error("ObjectOf(unknown) must be nil")
	}
}

func TestObjKindStrings(t *testing.T) {
	// These appear verbatim in diagnostics, so they are part of the contract.
	for kind, want := range map[check.ObjKind]string{
		check.Var:      "variable",
		check.Const:    "constant",
		check.Func:     "function",
		check.TypeName: "type",
		check.Module:   "module",
		check.Builtin:  "builtin",
	} {
		if got := kind.String(); got != want {
			t.Errorf("ObjKind(%d).String() = %q, want %q", kind, got, want)
		}
	}
}

func TestCheckToleratesAnEmptyFile(t *testing.T) {
	_, rendered := checkSrc(t, "module t\n")
	if strings.TrimSpace(rendered) != "" {
		t.Errorf("a module with no declarations must check clean, got:\n%s", rendered)
	}
}
