// Package lexer turns Ymir source into tokens.
//
// See docs/spec/01-lexical.md. Three rules here exist because the legacy
// implementation got them wrong:
//
//   - Operators are matched by longest prefix against a closed set, never as a
//     run of operator characters. `x==-3` lexes as `x` `==` `-` `3`.
//   - String escapes are decoded here, and the token carries the decoded value
//     without its delimiters. Legacy kept the quotes and never decoded `\n`.
//   - Comments are discarded and never reach the token stream.
package lexer

import (
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"

	"github.com/bjornaer/ymir/compiler/diag"
	"github.com/bjornaer/ymir/compiler/token"
)

type Lexer struct {
	src  string
	file string
	errs *diag.List

	offset   int // byte offset of the next character to read
	line     int
	lineHead int // byte offset where the current line starts

	last token.Token // last significant token, for newline handling
}

// New returns a lexer over src. Diagnostics accumulate in errs.
func New(file, src string, errs *diag.List) *Lexer {
	return &Lexer{src: src, file: file, errs: errs, line: 1}
}

// Tokens lexes the whole input. The final token is always EOF.
func Tokens(file, src string, errs *diag.List) []token.Token {
	l := New(file, src, errs)
	var out []token.Token
	for {
		t := l.Next()
		out = append(out, t)
		if t.Kind == token.EOF {
			return out
		}
	}
}

func (l *Lexer) pos(offset int) token.Position {
	return token.Position{
		File:   l.file,
		Line:   l.line,
		Column: offset - l.lineHead + 1,
		Offset: offset,
	}
}

func (l *Lexer) atEnd() bool { return l.offset >= len(l.src) }

func (l *Lexer) peek() byte {
	if l.atEnd() {
		return 0
	}
	return l.src[l.offset]
}

func (l *Lexer) peekAt(n int) byte {
	if l.offset+n >= len(l.src) {
		return 0
	}
	return l.src[l.offset+n]
}

func (l *Lexer) advance() byte {
	c := l.src[l.offset]
	l.offset++
	return c
}

func (l *Lexer) newline() {
	l.line++
	l.lineHead = l.offset
}

func (l *Lexer) emit(t token.Token) token.Token {
	l.last = t
	return t
}

// Next returns the next token, inserting a SEMI where a newline terminates a
// statement (spec 01 §Semicolons).
func (l *Lexer) Next() token.Token {
	for {
		// Skip spaces, tabs, and carriage returns. A newline either terminates a
		// statement or is skipped, depending on the previous token.
		for !l.atEnd() {
			c := l.peek()
			if c == ' ' || c == '\t' || c == '\r' {
				l.offset++
				continue
			}
			if c == '\n' {
				start := l.offset
				l.offset++
				terminates := l.last.EndsStatement()
				l.newline()
				if terminates {
					// Position the SEMI at the newline, so "expected X" points at
					// the end of the offending line rather than the next one.
					p := token.Position{File: l.file, Line: l.line - 1,
						Column: start - posLineHead(l.src, start) + 1, Offset: start}
					return l.emit(token.Token{Kind: token.SEMI, Pos: p})
				}
				continue
			}
			break
		}

		if l.atEnd() {
			return l.emit(token.Token{Kind: token.EOF, Pos: l.pos(l.offset)})
		}

		start := l.offset
		pos := l.pos(start)
		c := l.peek()

		switch {
		case c == '#':
			// Comment: discard to end of line. The newline itself is handled on
			// the next pass, so a comment cannot suppress a statement terminator.
			for !l.atEnd() && l.peek() != '\n' {
				l.offset++
			}
			continue

		case isLetter(c):
			for !l.atEnd() && isIdentChar(l.peek()) {
				l.offset++
			}
			lit := l.src[start:l.offset]
			kind := token.Lookup(lit)
			if kind == token.IDENT {
				return l.emit(token.Token{Kind: token.IDENT, Lit: lit, Pos: pos})
			}
			return l.emit(token.Token{Kind: kind, Pos: pos})

		case isDigit(c):
			return l.emit(l.number(start, pos))

		case c == '"':
			return l.emit(l.stringLit(start, pos))
		}

		// Operators first, longest match over the closed set. This must precede
		// the delimiter check: ':' is a delimiter but also the prefix of ':=',
		// and checking delimiters first would make ':=' unreachable.
		if kind, n, ok := l.matchOperator(); ok {
			l.offset += n
			return l.emit(token.Token{Kind: kind, Pos: pos})
		}

		// Delimiters are single characters and never begin an operator.
		if kind, ok := delimiters[c]; ok {
			l.offset++
			return l.emit(token.Token{Kind: kind, Pos: pos})
		}

		// Unknown character. Consume one rune so lexing makes progress and the
		// caller sees every bad character rather than only the first.
		r, size := utf8.DecodeRuneInString(l.src[l.offset:])
		l.offset += size
		l.errs.Addf(pos, "unexpected character %q", r)
		return l.emit(token.Token{Kind: token.INVALID, Lit: string(r), Pos: pos})
	}
}

// matchOperator tries the operator table longest-first.
func (l *Lexer) matchOperator() (token.Kind, int, bool) {
	remaining := len(l.src) - l.offset
	max := token.MaxOperatorLen
	if remaining < max {
		max = remaining
	}
	for n := max; n >= 1; n-- {
		if kind, ok := token.LookupOperator(l.src[l.offset : l.offset+n]); ok {
			return kind, n, true
		}
	}
	return token.INVALID, 0, false
}

var delimiters = map[byte]token.Kind{
	'(': token.LPAREN, ')': token.RPAREN,
	'[': token.LBRACK, ']': token.RBRACK,
	'{': token.LBRACE, '}': token.RBRACE,
	',': token.COMMA, '.': token.PERIOD, ';': token.SEMI,
	':': token.COLON,
}

// number lexes an int, float, or complex literal.
//
// Spec 01: a float needs a digit on both sides of the point, so `1.` and `.5`
// are errors; that removes the ambiguity with the `.` selector, which is what
// makes `t.0` tuple indexing unambiguous.
func (l *Lexer) number(start int, pos token.Position) token.Token {
	// Non-decimal bases: 0x, 0o, 0b. No float or complex form.
	if l.peek() == '0' && l.offset+1 < len(l.src) {
		switch lower(l.peekAt(1)) {
		case 'x', 'o', 'b':
			base := lower(l.peekAt(1))
			l.offset += 2
			digits := 0
			for !l.atEnd() && (isBaseDigit(l.peek(), base) || l.peek() == '_') {
				if l.peek() != '_' {
					digits++
				}
				l.offset++
			}
			lit := l.src[start:l.offset]
			if digits == 0 {
				l.errs.Addf(pos, "%s literal has no digits", baseName(base))
				return token.Token{Kind: token.INVALID, Lit: lit, Pos: pos}
			}
			return token.Token{Kind: token.INT, Lit: lit, Pos: pos}
		}
	}

	for !l.atEnd() && (isDigit(l.peek()) || l.peek() == '_') {
		l.offset++
	}

	isFloat := false
	// A '.' starts a fraction only when a digit follows. Otherwise it is the
	// selector, as in `t.0`, and belongs to the next token.
	if l.peek() == '.' && isDigit(l.peekAt(1)) {
		isFloat = true
		l.offset++
		for !l.atEnd() && (isDigit(l.peek()) || l.peek() == '_') {
			l.offset++
		}
	} else if l.peek() == '.' && !isDigit(l.peekAt(1)) {
		// Catch `1.` explicitly: without this the '.' would lex as a selector
		// and the error would surface far from the cause.
		if !isIdentStart(l.peekAt(1)) {
			l.offset++
			l.errs.AddHint(pos, "float literal needs a digit after the decimal point",
				fmt.Sprintf("write %s0", l.src[start:l.offset]))
			return token.Token{Kind: token.INVALID, Lit: l.src[start:l.offset], Pos: pos}
		}
	}

	if lower(l.peek()) == 'e' {
		next := l.peekAt(1)
		if isDigit(next) || ((next == '+' || next == '-') && isDigit(l.peekAt(2))) {
			isFloat = true
			l.offset++
			if l.peek() == '+' || l.peek() == '-' {
				l.offset++
			}
			for !l.atEnd() && (isDigit(l.peek()) || l.peek() == '_') {
				l.offset++
			}
		}
	}

	// An `i` suffix makes it complex (spec 01 §Complex).
	if lower(l.peek()) == 'i' && !isIdentChar(l.peekAt(1)) {
		l.offset++
		return token.Token{Kind: token.IMAG, Lit: l.src[start:l.offset], Pos: pos}
	}

	lit := l.src[start:l.offset]
	if isFloat {
		return token.Token{Kind: token.FLOAT, Lit: lit, Pos: pos}
	}
	return token.Token{Kind: token.INT, Lit: lit, Pos: pos}
}

// stringLit lexes a string and decodes its escapes. The returned Lit is the
// decoded value with the quotes removed.
func (l *Lexer) stringLit(start int, pos token.Position) token.Token {
	l.offset++ // opening quote
	var b strings.Builder

	for {
		if l.atEnd() {
			l.errs.Add(pos, "string literal is not terminated")
			return token.Token{Kind: token.INVALID, Lit: b.String(), Pos: pos}
		}
		c := l.peek()
		if c == '\n' {
			l.errs.AddHint(pos, "string literal is not terminated",
				`string literals cannot span lines; use \n`)
			return token.Token{Kind: token.INVALID, Lit: b.String(), Pos: pos}
		}
		if c == '"' {
			l.offset++
			return token.Token{Kind: token.STRING, Lit: b.String(), Pos: pos}
		}
		if c != '\\' {
			b.WriteByte(l.advance())
			continue
		}

		escPos := l.pos(l.offset)
		l.offset++ // backslash
		if l.atEnd() {
			l.errs.Add(pos, "string literal is not terminated")
			return token.Token{Kind: token.INVALID, Lit: b.String(), Pos: pos}
		}
		switch e := l.advance(); e {
		case 'n':
			b.WriteByte('\n')
		case 'r':
			b.WriteByte('\r')
		case 't':
			b.WriteByte('\t')
		case '\\':
			b.WriteByte('\\')
		case '"':
			b.WriteByte('"')
		case '0':
			b.WriteByte(0)
		case 'u':
			r, ok := l.unicodeEscape(escPos)
			if ok {
				b.WriteRune(r)
			}
		default:
			l.errs.Addf(escPos, "unknown escape sequence %q", `\`+string(e))
		}
	}
}

// unicodeEscape reads the \u{XXXX} form, having already consumed `\u`.
func (l *Lexer) unicodeEscape(escPos token.Position) (rune, bool) {
	if l.peek() != '{' {
		l.errs.AddHint(escPos, "unicode escape needs braces", `write \u{1F600}`)
		return 0, false
	}
	l.offset++
	var v rune
	digits := 0
	for !l.atEnd() && l.peek() != '}' {
		d, ok := hexVal(l.peek())
		if !ok {
			l.errs.Addf(escPos, "invalid hex digit %q in unicode escape", l.peek())
			return 0, false
		}
		v = v*16 + rune(d)
		digits++
		if digits > 6 {
			l.errs.Add(escPos, "unicode escape has more than 6 hex digits")
			return 0, false
		}
		l.offset++
	}
	if l.atEnd() {
		l.errs.Add(escPos, "unicode escape is not terminated")
		return 0, false
	}
	l.offset++ // closing brace
	if digits == 0 {
		l.errs.Add(escPos, "unicode escape has no digits")
		return 0, false
	}
	if v > unicode.MaxRune || (v >= 0xD800 && v <= 0xDFFF) {
		l.errs.Addf(escPos, "unicode escape %#x is not a valid scalar value", v)
		return 0, false
	}
	return v, true
}

// posLineHead finds the start offset of the line containing off. Used only when
// reporting a SEMI at a newline, where lineHead has already moved on.
func posLineHead(src string, off int) int {
	i := strings.LastIndexByte(src[:off], '\n')
	return i + 1
}

func isDigit(c byte) bool      { return c >= '0' && c <= '9' }
func isLetter(c byte) bool     { return c == '_' || (c|0x20 >= 'a' && c|0x20 <= 'z') }
func isIdentStart(c byte) bool { return isLetter(c) }
func isIdentChar(c byte) bool  { return isLetter(c) || isDigit(c) }
func lower(c byte) byte        { return c | 0x20 }

func isBaseDigit(c byte, base byte) bool {
	switch base {
	case 'x':
		_, ok := hexVal(c)
		return ok
	case 'o':
		return c >= '0' && c <= '7'
	case 'b':
		return c == '0' || c == '1'
	}
	return false
}

func baseName(base byte) string {
	switch base {
	case 'x':
		return "hexadecimal"
	case 'o':
		return "octal"
	case 'b':
		return "binary"
	}
	return "numeric"
}

func hexVal(c byte) (int, bool) {
	switch {
	case c >= '0' && c <= '9':
		return int(c - '0'), true
	case c >= 'a' && c <= 'f':
		return int(c-'a') + 10, true
	case c >= 'A' && c <= 'F':
		return int(c-'A') + 10, true
	}
	return 0, false
}
