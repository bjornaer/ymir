package parser_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/bjornaer/ymir/compiler/parser"
)

// TestConformanceCasesParse is the Phase 1 exit criterion: every conformance
// case must parse, or report a syntax error with an accurate position.
//
// Cases assert semantic rules the checker and VM will enforce later, so at this
// phase they must all be syntactically valid. A failure here means either the
// parser is wrong or a case uses syntax the spec does not define.
func TestConformanceCasesParse(t *testing.T) {
	root := filepath.Join("..", "..", "conformance", "cases")
	if _, err := os.Stat(root); err != nil {
		t.Skipf("conformance cases not found: %v", err)
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

	for _, path := range files {
		name, _ := filepath.Rel(root, path)
		t.Run(name, func(t *testing.T) {
			src, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("reading: %v", err)
			}
			if _, errs := parser.ParseFile(name, string(src)); !errs.Empty() {
				t.Errorf("case does not parse:\n%s", errs.Render())
			}
		})
	}
}
