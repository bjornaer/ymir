// Package diag reports compiler errors with a position and a source excerpt.
//
// This is a Phase 1 requirement, not a later polish step. The legacy
// implementation reported errors like "Undefined variable: total" with no file,
// no line, and no context, which made every failure a search.
package diag

import (
	"fmt"
	"sort"
	"strings"

	"github.com/bjornaer/ymir/compiler/token"
)

// Error is a single diagnostic anchored at a source position.
type Error struct {
	Pos token.Position
	Msg string
	// Hint is optional guidance shown under the excerpt. Use it for the fix,
	// never to restate the message.
	Hint string
}

func (e *Error) Error() string {
	if e.Pos.IsValid() {
		return fmt.Sprintf("%s: %s", e.Pos, e.Msg)
	}
	return e.Msg
}

// List accumulates diagnostics in source order.
type List struct {
	errs []*Error
	// src is the file content, retained so excerpts can be rendered.
	src  string
	file string
}

func NewList(file, src string) *List { return &List{src: src, file: file} }

// Add appends a diagnostic.
func (l *List) Add(pos token.Position, msg string) {
	l.errs = append(l.errs, &Error{Pos: pos, Msg: msg})
}

// Addf appends a formatted diagnostic.
func (l *List) Addf(pos token.Position, format string, args ...any) {
	l.Add(pos, fmt.Sprintf(format, args...))
}

// AddHint appends a diagnostic with guidance on the fix.
func (l *List) AddHint(pos token.Position, msg, hint string) {
	l.errs = append(l.errs, &Error{Pos: pos, Msg: msg, Hint: hint})
}

func (l *List) Len() int      { return len(l.errs) }
func (l *List) Empty() bool   { return len(l.errs) == 0 }
func (l *List) All() []*Error { return l.errs }

// Err returns the list as an error, or nil when empty.
func (l *List) Err() error {
	if l.Empty() {
		return nil
	}
	return l
}

func (l *List) Error() string {
	switch len(l.errs) {
	case 0:
		return "no errors"
	case 1:
		return l.errs[0].Error()
	}
	return fmt.Sprintf("%s (and %d more)", l.errs[0], len(l.errs)-1)
}

// Sort orders diagnostics by position. Parsers can recover out of order.
func (l *List) Sort() {
	sort.SliceStable(l.errs, func(i, j int) bool {
		return l.errs[i].Pos.Offset < l.errs[j].Pos.Offset
	})
}

// Render writes every diagnostic with its source excerpt:
//
//	example.ymr:4:15: undefined: cuont
//	  |
//	4 |     print(cuont + 1)
//	  |           ^
func (l *List) Render() string {
	var b strings.Builder
	lines := strings.Split(l.src, "\n")
	for i, e := range l.errs {
		if i > 0 {
			b.WriteString("\n")
		}
		fmt.Fprintf(&b, "%s: %s\n", e.Pos, e.Msg)
		if e.Pos.IsValid() && e.Pos.Line-1 < len(lines) {
			src := lines[e.Pos.Line-1]
			gutter := fmt.Sprintf("%d", e.Pos.Line)
			pad := strings.Repeat(" ", len(gutter))
			fmt.Fprintf(&b, "%s |\n", pad)
			fmt.Fprintf(&b, "%s | %s\n", gutter, src)
			fmt.Fprintf(&b, "%s | %s^\n", pad, caretPad(src, e.Pos.Column))
		}
		if e.Hint != "" {
			fmt.Fprintf(&b, "  hint: %s\n", e.Hint)
		}
	}
	return b.String()
}

// caretPad builds the run of spaces before a caret, preserving tabs from the
// source so the caret lines up under a tab-indented line.
func caretPad(src string, col int) string {
	if col < 1 {
		col = 1
	}
	var b strings.Builder
	for i := 0; i < col-1 && i < len(src); i++ {
		if src[i] == '\t' {
			b.WriteByte('\t')
		} else {
			b.WriteByte(' ')
		}
	}
	return b.String()
}
