package check_test

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/bjornaer/ymir/compiler/check"
	"github.com/bjornaer/ymir/compiler/parser"
)

// The Phase 2 exit gate.
//
// conformance/run.py checks only that each `compile-error` substring appears
// somewhere in stdout or stderr. It never checks the line or the column, and it
// cannot tell a compile error from a runtime failure that happened to print the
// right word. PLAN.md's bar is "the right error at the right position", so
// position is enforced here, in Go, against the same case files.
//
// The table below is the source of truth for what the checker is expected to
// catch. It grows one milestone at a time; a case with a `compile-error` header
// that is absent from the table is reported as pending rather than failing, so
// the test output doubles as the Phase 2 progress report.

// want is one expected diagnostic.
type want struct {
	line, col int      // 1-based, as token.Position reports them
	contains  []string // substrings the message must contain, in no order
}

// expected maps a conformance case id to the diagnostics the checker must
// produce, in position order. An entry with no diagnostics means the case must
// check clean even though it is a compile-error case elsewhere — there are none
// of those today.
//
// Every entry names the milestone that added it, so an unexplained gap is
// visible.
var expected = map[string][]want{
	// M3 — scope resolution.
	"decl/undefined_variable": {{10, 11, []string{"undefined", "cuont"}}},
	// The error belongs on the *second* print(inner), at line 13. The use on
	// line 11 is inside the if-block where inner is still live.
	"scope/block_scope": {{13, 11, []string{"undefined", "inner"}}},

	"decl/redeclared_in_same_scope": {{10, 5, []string{"count", "redeclared"}}},
	"decl/blank_cannot_be_read":     {{10, 11, []string{"blank identifier"}}},
	"decl/assign_to_const":          {{11, 5, []string{"cannot assign to constant", "LIMIT"}}},
	"control/break_outside_loop":    {{10, 9, []string{"break outside a loop"}}},
	"decl/ambiguous_variant":        {{17, 10, []string{"ambiguous variant", "Point"}}},

	// Type formation, also M3: a written type is rejected where it is written.
	"types/union_member_must_be_enum":    {{12, 28, []string{"union members must be enums", "int"}}},
	"types/nullable_rejects_linear":      {{8, 14, []string{"unrestricted", "qubit", "linear"}}},
	"types/map_key_must_be_hashable":     {{14, 21, []string{"map key", "Color", "not hashable"}}},
	"types/matrix_element_must_be_float": {{9, 22, []string{"float or complex", "int"}}},
	"types/undefined_type":               {{13, 19, []string{"undefined type", "Poitn"}}},

	// M4 — literals, operators, inference, assignability, constant folding.
	"types/no_implicit_conversion":  {{11, 13, []string{"mismatched types", "int", "float"}}},
	"types/nil_not_on_plain_type":   {{10, 10, []string{"int is never nil"}}},
	"types/const_overflow_is_error": {{8, 38, []string{"overflows int"}}},
	"decl/no_zero_value_needs_init": {{14, 9, []string{"Shape has no zero value"}}},
	"types/chan_has_no_zero_value":  {{9, 9, []string{"chan[int] has no zero value"}}},
	"types/const_division_by_zero":  {{8, 23, []string{"division by zero"}}},
	"types/no_truthiness":           {{10, 8, []string{"if condition is int", "want bool"}}},
	"types/complex_not_ordered":     {{11, 10, []string{"complex is not ordered"}}},
	"types/modulo_only_on_int":      {{11, 13, []string{"only on int", "float"}}},
	"decl/cannot_infer_from_nil":    {{9, 5, []string{"cannot infer a type", "nil"}}},

	// M5 — calls, method sets, selection, return values.
	"expr/call_arity_mismatch":      {{13, 16, []string{"add takes 2 arguments", "got 1"}}},
	"expr/call_argument_type":       {{13, 18, []string{"cannot use float as int"}}},
	"expr/multi_valued_call_nested": {{13, 11, []string{"multi-valued call", "divmod"}}},
	"expr/enum_has_no_fields":       {{15, 13, []string{"inspected only by match", "Shape"}}},
	"errors/error_set_not_superset": {{17, 15, []string{"?(IOError | ParseError)", "?IOError"}}},

	// M7 — nullables and narrowing (N1-N6).
	"types/nullable_needs_narrowing":       {{14, 13, []string{"?int must be narrowed", "int"}}},
	"types/narrowing_ends_at_reassignment": {{16, 17, []string{"?int must be narrowed"}}},
	"types/narrowing_is_not_flow_typing":   {{17, 13, []string{"?int must be narrowed"}}},

	// M6 — composite literals and indexing.
	"types/array_is_homogeneous":             {{9, 15, []string{"same type", "float", "int"}}},
	"types/empty_literal_needs_annotation":   {{9, 11, []string{"cannot infer the element type"}}},
	"types/matrix_rows_must_match":           {{9, 44, []string{"same length"}}},
	"decl/struct_literal_must_be_exhaustive": {{14, 22, []string{"Point literal is missing y"}}},
	"expr/struct_literal_unknown_field":      {{14, 32, []string{"Point has no field z"}}},
	"expr/tuple_index_out_of_range":          {{10, 13, []string{"no element 2"}}},
	// M6 — nullables and narrowing.
	// M7 — match exhaustiveness.
	// M8 — error sets, try, unhandled errors.
	// M9 — returns on every path.
}

func TestConformanceCasesCheck(t *testing.T) {
	root := filepath.Join("..", "..", "conformance", "cases")
	if _, err := os.Stat(root); err != nil {
		t.Skipf("conformance suite not present: %v", err)
	}

	var files []string
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasSuffix(path, ".ymr") {
			files = append(files, path)
		}
		return nil
	})
	if err != nil {
		t.Fatalf("walking %s: %v", root, err)
	}
	if len(files) == 0 {
		t.Fatalf("no conformance cases found under %s", root)
	}

	var pending []string
	for _, path := range files {
		rel, _ := filepath.Rel(root, path)
		t.Run(filepath.ToSlash(rel), func(t *testing.T) {
			src, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("reading case: %v", err)
			}
			hdr, err := parseHeader(string(src))
			if err != nil {
				t.Fatalf("malformed case header: %v", err)
			}
			if hdr.skip != "" {
				t.Skipf("case is skipped: %s", hdr.skip)
			}

			name := filepath.ToSlash(rel)
			// The expectation table is keyed by case id, which is the path
			// without the extension — the same key run.py uses.
			caseID := strings.TrimSuffix(name, ".ymr")

			file, errs := parser.ParseFile(name, string(src))
			if !errs.Empty() {
				t.Fatalf("case does not parse, which the Phase 1 gate should have caught:\n%s", errs.Render())
			}

			_, errs = check.Check(file, name, string(src))
			got := errs.All()

			if len(hdr.compileError) == 0 {
				// The other half of the gate, and the easier one to forget:
				// a case that is supposed to run must type-check clean. A
				// false positive here is as much a bug as a missed error.
				if len(got) != 0 {
					t.Fatalf("case must check clean, but the checker reported:\n%s", errs.Render())
				}
				return
			}

			wants, known := expected[caseID]
			if !known {
				pending = append(pending, caseID)
				t.Skipf("not yet implemented; expects a compile error mentioning %q", hdr.compileError)
			}

			if len(got) != len(wants) {
				t.Fatalf("got %d diagnostics, want %d:\n%s", len(got), len(wants), errs.Render())
			}
			for i, w := range wants {
				g := got[i]
				if g.Pos.Line != w.line || g.Pos.Column != w.col {
					t.Errorf("diagnostic %d at %d:%d, want %d:%d\n  %s",
						i, g.Pos.Line, g.Pos.Column, w.line, w.col, g.Msg)
				}
				for _, sub := range w.contains {
					if !strings.Contains(g.Msg, sub) {
						t.Errorf("diagnostic %d message %q does not contain %q", i, g.Msg, sub)
					}
				}
			}

			// What run.py will check, checked here too so the two agree.
			all := errs.Render()
			for _, sub := range hdr.compileError {
				if !strings.Contains(all, sub) {
					t.Errorf("no diagnostic contains %q, which the case header requires:\n%s", sub, all)
				}
			}
		})
	}

	if len(pending) > 0 {
		t.Logf("%d compile-error cases not yet implemented: %s",
			len(pending), strings.Join(pending, ", "))
	}
}

// TestTourChecks holds examples/tour.ymr to the same bar as a clean conformance
// case. It exercises the whole grammar in one file, so it is the broadest single
// check that a new rule has not become a false positive.
func TestTourChecks(t *testing.T) {
	path := filepath.Join("..", "..", "examples", "tour.ymr")
	src, err := os.ReadFile(path)
	if err != nil {
		t.Skipf("tour not present: %v", err)
	}
	file, errs := parser.ParseFile("examples/tour.ymr", string(src))
	if !errs.Empty() {
		t.Fatalf("tour does not parse:\n%s", errs.Render())
	}
	if _, errs = check.Check(file, "examples/tour.ymr", string(src)); !errs.Empty() {
		t.Fatalf("tour must check clean, but the checker reported:\n%s", errs.Render())
	}
}

// ---------------------------------------------------------------------------
// The `#@` header
//
// A deliberate second implementation of conformance/run.py's Case._parse. Go
// tests cannot call it, and shelling out to Python from a unit test is worse
// than 40 lines of duplication. TestHeaderParserAgreesWithRunPy pins the two
// together on the directives this file relies on.

type header struct {
	id           string
	compileError []string
	skip         string
}

func parseHeader(src string) (*header, error) {
	h := &header{}
	var block *[]string

	sc := bufio.NewScanner(strings.NewReader(src))
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())

		// A blank line or an ordinary comment does not end the header; any
		// other non-directive line does. errors/unhandled_is_compile_error has
		// a blank line in the middle of its header and relies on this.
		if line == "" {
			continue
		}
		if !strings.HasPrefix(line, "#@") {
			if strings.HasPrefix(line, "#") {
				continue
			}
			break
		}

		rest := strings.TrimSpace(strings.TrimPrefix(line, "#@"))

		if strings.HasPrefix(rest, "|") {
			if block == nil {
				return nil, fmt.Errorf("continuation line with no block directive: %q", line)
			}
			*block = append(*block, strings.TrimPrefix(rest[1:], " "))
			continue
		}

		block = nil
		key, arg, _ := strings.Cut(rest, " ")
		arg = strings.TrimSpace(arg)

		switch key {
		case "case":
			h.id = arg
		case "compile-error":
			block = &h.compileError
		case "skip":
			if arg == "" {
				arg = "no reason given"
			}
			h.skip = arg
		case "spec", "exit", "stdout", "stdout-contains":
			// Not consulted here. stdout and stdout-contains are block
			// directives, so their continuation lines must still be absorbed.
			if key == "stdout" || key == "stdout-contains" {
				var discard []string
				block = &discard
			}
		default:
			return nil, fmt.Errorf("unknown directive %q", key)
		}
	}
	return h, sc.Err()
}

// TestHeaderParserMatchesCaseIDs checks this file's header parser against the
// invariant run.py enforces: a case's declared id equals its path under cases/.
// If the two parsers disagree about where a header ends, this is where it shows.
func TestHeaderParserMatchesCaseIDs(t *testing.T) {
	root := filepath.Join("..", "..", "conformance", "cases")
	if _, err := os.Stat(root); err != nil {
		t.Skipf("conformance suite not present: %v", err)
	}

	n := 0
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || !strings.HasSuffix(path, ".ymr") {
			return err
		}
		src, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		h, err := parseHeader(string(src))
		if err != nil {
			t.Errorf("%s: %v", path, err)
			return nil
		}
		rel, _ := filepath.Rel(root, path)
		wantID := strings.TrimSuffix(filepath.ToSlash(rel), ".ymr")
		if h.id != wantID {
			t.Errorf("%s: header declares case %q, want %q", path, h.id, wantID)
		}
		n++
		return nil
	})
	if err != nil {
		t.Fatalf("walking %s: %v", root, err)
	}
	if n == 0 {
		t.Fatal("no cases inspected")
	}
}

// TestExpectedTableHasNoStaleEntries guards the other direction: an entry for a
// case that no longer exists, or that no longer expects a compile error, is a
// silent hole in the gate.
func TestExpectedTableHasNoStaleEntries(t *testing.T) {
	root := filepath.Join("..", "..", "conformance", "cases")
	if _, err := os.Stat(root); err != nil {
		t.Skipf("conformance suite not present: %v", err)
	}
	for id := range expected {
		path := filepath.Join(root, filepath.FromSlash(id)+".ymr")
		src, err := os.ReadFile(path)
		if err != nil {
			t.Errorf("expected table names %q, which does not exist", id)
			continue
		}
		h, err := parseHeader(string(src))
		if err != nil {
			t.Errorf("%s: %v", id, err)
			continue
		}
		if len(h.compileError) == 0 {
			t.Errorf("expected table names %q, but that case does not declare a compile-error", id)
		}
	}
}
