// Package parser builds an ast.File from Ymir source.
//
// Recursive descent over the grammar in docs/spec/09-grammar.md. The parser
// recovers at statement and declaration boundaries so one syntax error does not
// cascade; it reports every error it can distinguish rather than stopping at the
// first.
package parser

import (
	"strconv"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/diag"
	"github.com/bjornaer/ymir/compiler/lexer"
	"github.com/bjornaer/ymir/compiler/token"
)

type parser struct {
	toks []token.Token
	pos  int
	errs *diag.List

	// noStructLit suppresses composite literals while parsing a control-flow
	// header, where `{` starts the body. Spec 09 §Known ambiguities (1).
	noStructLit bool
}

// ParseFile parses src. It returns the file and any diagnostics; the file is
// non-nil even when there are errors, with ast.Bad nodes where recovery happened.
func ParseFile(file, src string) (*ast.File, *diag.List) {
	errs := diag.NewList(file, src)
	toks := lexer.Tokens(file, src, errs)
	p := &parser{toks: toks, errs: errs}
	f := p.parseFile()
	errs.Sort()
	return f, errs
}

// ---------------------------------------------------------------- token access

func (p *parser) tok() token.Token     { return p.toks[p.pos] }
func (p *parser) kind() token.Kind     { return p.toks[p.pos].Kind }
func (p *parser) at(k token.Kind) bool { return p.toks[p.pos].Kind == k }

func (p *parser) peek(n int) token.Token {
	i := p.pos + n
	if i >= len(p.toks) {
		return p.toks[len(p.toks)-1]
	}
	return p.toks[i]
}

func (p *parser) next() token.Token {
	t := p.toks[p.pos]
	if p.pos < len(p.toks)-1 {
		p.pos++
	}
	return t
}

// accept consumes the token if it matches.
func (p *parser) accept(k token.Kind) bool {
	if p.at(k) {
		p.next()
		return true
	}
	return false
}

// expect consumes the token if it matches, and reports otherwise.
func (p *parser) expect(k token.Kind, context string) token.Token {
	if p.at(k) {
		return p.next()
	}
	p.errs.Addf(p.tok().Pos, "expected %s %s, found %s", k, context, describe(p.tok()))
	return token.Token{Kind: token.INVALID, Pos: p.tok().Pos}
}

func describe(t token.Token) string {
	switch t.Kind {
	case token.EOF:
		return "end of file"
	case token.SEMI:
		return "end of statement"
	case token.IDENT:
		return "identifier " + strconv.Quote(t.Lit)
	case token.STRING:
		return "string literal"
	case token.INT, token.FLOAT, token.IMAG:
		return "literal " + t.Lit
	}
	return strconv.Quote(t.Kind.String())
}

// skipSemis consumes redundant statement terminators, which blank lines produce.
func (p *parser) skipSemis() {
	for p.at(token.SEMI) {
		p.next()
	}
}

// expectSemi requires a statement terminator, tolerating a closing brace so the
// last statement in a block needs no explicit one.
func (p *parser) expectSemi() {
	switch p.kind() {
	case token.RBRACE, token.EOF:
		return
	case token.SEMI:
		p.next()
		return
	}
	p.errs.Addf(p.tok().Pos, "expected end of statement, found %s", describe(p.tok()))
	p.syncStmt()
}

// syncStmt discards tokens to the next statement boundary.
func (p *parser) syncStmt() {
	depth := 0
	for {
		switch p.kind() {
		case token.EOF:
			return
		case token.SEMI:
			if depth == 0 {
				p.next()
				return
			}
		case token.LBRACE:
			depth++
		case token.RBRACE:
			if depth == 0 {
				return
			}
			depth--
		}
		p.next()
	}
}

// syncDecl discards tokens to the next declaration boundary.
func (p *parser) syncDecl() {
	for {
		switch p.kind() {
		case token.EOF, token.FUNC, token.GATE, token.STRUCT, token.ENUM,
			token.CONST, token.VAR, token.EXPORT, token.IMPORT:
			return
		}
		p.next()
	}
}

// ---------------------------------------------------------------- file

func (p *parser) parseFile() *ast.File {
	f := &ast.File{}
	p.skipSemis()

	// Spec 03: every file begins with a module declaration.
	if p.at(token.MODULE) {
		f.Module = p.parseModuleDecl()
	} else {
		p.errs.AddHint(p.tok().Pos,
			"file must begin with a module declaration",
			"add `module <name>` as the first line")
	}
	p.skipSemis()

	for p.at(token.IMPORT) {
		f.Imports = append(f.Imports, p.parseImportDecl())
		p.skipSemis()
	}

	for !p.at(token.EOF) {
		before := p.pos
		if d := p.parseDecl(); d != nil {
			f.Decls = append(f.Decls, d)
		}
		p.skipSemis()
		if p.pos == before { // no progress: force one, so we cannot loop forever
			p.next()
		}
	}
	return f
}

func (p *parser) parseModuleDecl() *ast.ModuleDecl {
	kw := p.next().Pos
	d := &ast.ModuleDecl{Keyword: kw, Name: p.parseQualifiedIdent()}
	p.expectSemi()
	return d
}

func (p *parser) parseImportDecl() *ast.ImportDecl {
	kw := p.next().Pos
	d := &ast.ImportDecl{Keyword: kw, Path: p.parseQualifiedIdent()}
	// `as` is not a keyword; it is a contextual identifier here, which keeps it
	// usable as a variable name everywhere else.
	if p.at(token.IDENT) && p.tok().Lit == "as" {
		p.next()
		d.Alias = p.parseIdent()
	}
	p.expectSemi()
	return d
}

func (p *parser) parseIdent() *ast.Ident {
	t := p.expect(token.IDENT, "")
	return &ast.Ident{NamePos: t.Pos, Name: t.Lit}
}

func (p *parser) parseQualifiedIdent() *ast.QualifiedIdent {
	q := &ast.QualifiedIdent{Parts: []*ast.Ident{p.parseIdent()}}
	for p.accept(token.PERIOD) {
		q.Parts = append(q.Parts, p.parseIdent())
	}
	return q
}

// ---------------------------------------------------------------- declarations

func (p *parser) parseDecl() ast.Decl {
	export := false
	exportPos := p.tok().Pos
	if p.at(token.EXPORT) {
		export = true
		p.next()
	}

	switch p.kind() {
	case token.FUNC:
		return p.parseFuncDecl(export, false)
	case token.GATE:
		return p.parseFuncDecl(export, true)
	case token.STRUCT:
		return p.parseStructDecl(export)
	case token.ENUM:
		return p.parseEnumDecl(export)
	case token.CONST:
		return p.parseConstDecl(export)
	case token.VAR:
		d := p.parseVarDecl()
		d.Export = export
		if export {
			// Spec 03: there are no mutable globals across module boundaries.
			p.errs.AddHint(exportPos, "`var` cannot be exported",
				"export a `const`, or a function that returns the value")
		}
		p.expectSemi()
		return d
	}

	if export {
		p.errs.Addf(exportPos, "expected a declaration after `export`, found %s",
			describe(p.tok()))
	} else {
		p.errs.AddHint(p.tok().Pos,
			"expected a declaration, found "+describe(p.tok()),
			"a module body holds only declarations; executable statements go in a function")
	}
	from := p.tok().Pos
	p.syncDecl()
	return &ast.VarDecl{Keyword: from, Name: &ast.Ident{NamePos: from, Name: "_"}}
}

func (p *parser) parseFuncDecl(export, isGate bool) *ast.FuncDecl {
	kw := p.next().Pos
	d := &ast.FuncDecl{Keyword: kw, Export: export, IsGate: isGate}

	// A method declares its receiver before the name: func (p: Point) mag() ...
	if !isGate && p.at(token.LPAREN) {
		d.Recv = p.parseReceiver()
	}

	d.Name = p.parseIdent()
	d.Params = p.parseParams()

	if p.accept(token.ARROW) {
		d.Results = p.parseResultTypes()
	}
	if isGate && len(d.Results) > 0 {
		// Spec 08: a gate is a unitary operation and returns nothing.
		p.errs.Add(d.Name.Pos(), "a gate cannot declare a result type")
	}

	d.Body = p.parseBlock()
	p.expectSemi()
	return d
}

func (p *parser) parseReceiver() *ast.Param {
	p.expect(token.LPAREN, "before the receiver")
	recv := &ast.Param{Name: p.parseIdent()}
	p.expect(token.COLON, "after the receiver name")
	recv.Mut = p.accept(token.MUT)
	recv.Type = p.parseType()
	p.expect(token.RPAREN, "after the receiver")
	return recv
}

func (p *parser) parseParams() []*ast.Param {
	p.expect(token.LPAREN, "before the parameter list")
	var params []*ast.Param
	for !p.at(token.RPAREN) && !p.at(token.EOF) {
		prm := &ast.Param{Name: p.parseIdent()}
		if p.accept(token.COLON) {
			prm.Mut = p.accept(token.MUT)
			prm.Type = p.parseType()
		} else if prm.Name.Name != "self" {
			// Spec 02 §Type inference: parameters are always annotated.
			p.errs.AddHint(prm.Name.Pos(),
				"parameter "+strconv.Quote(prm.Name.Name)+" needs a type annotation",
				"write `"+prm.Name.Name+": <type>`")
		}
		params = append(params, prm)
		if !p.accept(token.COMMA) {
			break
		}
	}
	p.expect(token.RPAREN, "after the parameter list")
	return params
}

// parseResultTypes reads what follows `->`: one type, or a parenthesized list.
func (p *parser) parseResultTypes() []ast.Type {
	if !p.at(token.LPAREN) {
		return []ast.Type{p.parseType()}
	}
	p.next()
	var out []ast.Type
	for !p.at(token.RPAREN) && !p.at(token.EOF) {
		out = append(out, p.parseType())
		if !p.accept(token.COMMA) {
			break
		}
	}
	p.expect(token.RPAREN, "after the result list")
	return out
}

func (p *parser) parseStructDecl(export bool) *ast.StructDecl {
	kw := p.next().Pos
	d := &ast.StructDecl{Keyword: kw, Export: export, Name: p.parseIdent()}
	p.expect(token.LBRACE, "before the field list")
	p.skipSemis()
	for !p.at(token.RBRACE) && !p.at(token.EOF) {
		f := &ast.Field{Name: p.parseIdent()}
		p.expect(token.COLON, "after the field name")
		f.Type = p.parseType()
		d.Fields = append(d.Fields, f)
		if !p.accept(token.COMMA) {
			p.skipSemis()
			break
		}
		p.skipSemis()
	}
	d.Rbrace = p.expect(token.RBRACE, "after the field list").Pos
	p.expectSemi()
	return d
}

func (p *parser) parseEnumDecl(export bool) *ast.EnumDecl {
	kw := p.next().Pos
	d := &ast.EnumDecl{Keyword: kw, Export: export, Name: p.parseIdent()}
	p.expect(token.LBRACE, "before the variant list")
	p.skipSemis()
	for !p.at(token.RBRACE) && !p.at(token.EOF) {
		v := &ast.Variant{Name: p.parseIdent()}
		if p.accept(token.LPAREN) {
			for !p.at(token.RPAREN) && !p.at(token.EOF) {
				v.Payload = append(v.Payload, p.parseType())
				if !p.accept(token.COMMA) {
					break
				}
			}
			v.Rparen = p.expect(token.RPAREN, "after the variant payload").Pos
		}
		d.Variants = append(d.Variants, v)
		if !p.accept(token.COMMA) {
			p.skipSemis()
			break
		}
		p.skipSemis()
	}
	d.Rbrace = p.expect(token.RBRACE, "after the variant list").Pos
	p.expectSemi()
	return d
}

func (p *parser) parseConstDecl(export bool) *ast.ConstDecl {
	kw := p.next().Pos
	d := &ast.ConstDecl{Keyword: kw, Export: export, Name: p.parseIdent()}
	// Spec 03: constants are typed; there are no untyped constants.
	if p.accept(token.COLON) {
		d.Type = p.parseType()
	} else {
		p.errs.AddHint(p.tok().Pos, "constant needs a type annotation",
			"write `const "+d.Name.Name+": <type> = ...`")
	}
	p.expect(token.ASSIGN, "before the constant value")
	d.Value = p.parseExpr()
	p.expectSemi()
	return d
}

// parseVarDecl handles `var x: T = e`, `var x: T`, and `var x := e`. It does not
// consume the terminator, since a var can head a C-style for clause.
func (p *parser) parseVarDecl() *ast.VarDecl {
	kw := p.next().Pos
	d := &ast.VarDecl{Keyword: kw, Name: p.parseIdent()}
	switch {
	case p.accept(token.COLON):
		d.Type = p.parseType()
		if p.accept(token.ASSIGN) {
			d.Value = p.parseExpr()
		}
	case p.accept(token.DEFINE):
		d.Value = p.parseExpr()
	default:
		p.errs.AddHint(p.tok().Pos,
			"expected `:` or `:=` after the variable name",
			"write `var "+d.Name.Name+": <type>` or `var "+d.Name.Name+" := <value>`")
	}
	return d
}

// ---------------------------------------------------------------- types

// parseType reads a type, including a union. Union members must be enum types,
// which the checker verifies (spec 02 §Union types).
func (p *parser) parseType() ast.Type {
	first := p.parseBaseType()
	if !p.at(token.OR) {
		return first
	}
	u := &ast.UnionType{Members: []ast.Type{first}}
	for p.accept(token.OR) {
		u.Members = append(u.Members, p.parseBaseType())
	}
	return u
}

func (p *parser) parseBaseType() ast.Type {
	// `?T` is the nullable type former (spec 02 §Nullable types). It takes a
	// single base type or a parenthesized type: `?(A | B)`, never `?A | B`,
	// so there is no precedence question between `?` and `|`.
	if p.at(token.QUESTION) {
		q := p.next().Pos
		if p.accept(token.LPAREN) {
			inner := p.parseType()
			p.expect(token.RPAREN, "after the nullable type")
			return &ast.NullableType{Question: q, Elem: inner}
		}
		return &ast.NullableType{Question: q, Elem: p.parseBaseType()}
	}

	switch p.kind() {
	case token.FUNC:
		return p.parseFuncType()
	case token.QUBIT:
		// `qubit` is reserved (spec 01) and names a type in the quantum fragment.
		t := p.next()
		return &ast.NamedType{Name: &ast.QualifiedIdent{
			Parts: []*ast.Ident{{NamePos: t.Pos, Name: "qubit"}}}}
	case token.IDENT:
		name := p.parseQualifiedIdent()
		// A single identifier followed by `[` is a built-in generic: array[T],
		// map[K, V], tuple[...], matrix[T], chan[T], qreg[N].
		if len(name.Parts) == 1 && p.at(token.LBRACK) {
			p.next()
			g := &ast.GenericType{Name: name.Parts[0]}
			// qreg[N] is parameterized by a compile-time integer constant
			// rather than a type (grammar 09 §Types). It is the only one.
			if g.Name.Name == "qreg" && p.at(token.INT) {
				t := p.next()
				g.Width = ast.NewBasicLit(t.Pos, token.INT, t.Lit, len(t.Lit))
				g.Rbrack = p.expect(token.RBRACK, "after the register width").Pos
				return g
			}
			for !p.at(token.RBRACK) && !p.at(token.EOF) {
				g.Args = append(g.Args, p.parseType())
				if !p.accept(token.COMMA) {
					break
				}
			}
			g.Rbrack = p.expect(token.RBRACK, "after the type arguments").Pos
			return g
		}
		return &ast.NamedType{Name: name}
	}

	p.errs.Addf(p.tok().Pos, "expected a type, found %s", describe(p.tok()))
	bad := p.tok().Pos
	return &ast.NamedType{Name: &ast.QualifiedIdent{
		Parts: []*ast.Ident{{NamePos: bad, Name: "_"}}}}
}

func (p *parser) parseFuncType() ast.Type {
	kw := p.next().Pos
	t := &ast.FuncType{Keyword: kw}
	p.expect(token.LPAREN, "before the parameter types")
	for !p.at(token.RPAREN) && !p.at(token.EOF) {
		t.Params = append(t.Params, p.parseType())
		if !p.accept(token.COMMA) {
			break
		}
	}
	rp := p.expect(token.RPAREN, "after the parameter types")
	t.SetEnd(shiftPos(rp.Pos, 1))
	if p.accept(token.ARROW) {
		t.Results = p.parseResultTypes()
		t.SetEnd(t.Results[len(t.Results)-1].End())
	}
	return t
}

// ---------------------------------------------------------------- statements

func (p *parser) parseBlock() *ast.BlockStmt {
	lb := p.expect(token.LBRACE, "to open a block")
	b := &ast.BlockStmt{Lbrace: lb.Pos}
	p.skipSemis()
	for !p.at(token.RBRACE) && !p.at(token.EOF) {
		before := p.pos
		if s := p.parseStmt(); s != nil {
			b.Stmts = append(b.Stmts, s)
		}
		p.skipSemis()
		if p.pos == before {
			p.next()
		}
	}
	b.Rbrace = p.expect(token.RBRACE, "to close the block").Pos
	return b
}

func (p *parser) parseStmt() ast.Stmt {
	switch p.kind() {
	case token.VAR:
		d := p.parseVarDecl()
		p.expectSemi()
		return d
	case token.IF:
		return p.parseIfStmt()
	case token.WHILE:
		return p.parseWhileStmt()
	case token.FOR:
		return p.parseForStmt()
	case token.MATCH:
		return p.parseMatchStmt()
	case token.SELECT:
		return p.parseSelectStmt()
	case token.RETURN:
		return p.parseReturnStmt()
	case token.SPAWN:
		return p.parseSpawnStmt()
	case token.BREAK, token.CONTINUE:
		t := p.next()
		p.expectSemi()
		return &ast.BranchStmt{Keyword: t.Pos, Tok: t.Kind}
	case token.LBRACE:
		b := p.parseBlock()
		p.expectSemi()
		return b
	}
	return p.parseSimpleStmt(true, true)
}

// parseSimpleStmt reads an assignment, a short declaration, an inc/dec, a send,
// or a bare call.
//
// semi controls whether it consumes the terminator, since the clauses of a
// C-style for must not. list controls whether a comma extends the target list;
// inside a match arm the comma terminates the arm instead, so it must not.
func (p *parser) parseSimpleStmt(semi, list bool) ast.Stmt {
	start := p.tok().Pos
	lhs := []ast.Expr{p.parseExpr()}
	if list {
		for p.accept(token.COMMA) {
			lhs = append(lhs, p.parseExpr())
		}
	}

	switch p.kind() {
	case token.ASSIGN, token.DEFINE, token.ADD_ASSIGN, token.SUB_ASSIGN,
		token.MUL_ASSIGN, token.QUO_ASSIGN, token.REM_ASSIGN, token.POW_ASSIGN:
		t := p.next()
		rhs := []ast.Expr{p.parseExpr()}
		if list {
			for p.accept(token.COMMA) {
				rhs = append(rhs, p.parseExpr())
			}
		}
		if semi {
			p.expectSemi()
		}
		return &ast.AssignStmt{Lhs: lhs, TokPos: t.Pos, Tok: t.Kind, Rhs: rhs}

	case token.INC, token.DEC:
		t := p.next()
		if len(lhs) != 1 {
			p.errs.Addf(t.Pos, "%s applies to a single target", t.Kind)
		}
		if semi {
			p.expectSemi()
		}
		return &ast.IncDecStmt{X: lhs[0], TokPos: t.Pos, Tok: t.Kind}

	case token.CHAN_OP:
		// `ch <- v`. A receive in expression position was already consumed as a
		// unary operator, so reaching here means a send.
		t := p.next()
		if len(lhs) != 1 {
			p.errs.Add(t.Pos, "channel send takes a single channel")
		}
		v := p.parseExpr()
		if semi {
			p.expectSemi()
		}
		return &ast.SendStmt{Chan: lhs[0], ArrowPos: t.Pos, Value: v}
	}

	if len(lhs) != 1 {
		p.errs.Add(start, "expected an assignment after the expression list")
		if semi {
			p.expectSemi()
		}
		return &ast.BadStmt{From: start, To: p.tok().Pos}
	}

	// Spec 05 §Statement-level expressions: only calls may stand alone. A bare
	// `x + 1` computes a value and discards it, which is always a mistake.
	if !isCallLike(lhs[0]) {
		p.errs.AddHint(start, "expression is not a statement",
			"only a call can stand alone; did you mean to assign the result?")
		if semi {
			p.expectSemi()
		}
		return &ast.BadStmt{From: start, To: p.tok().Pos}
	}
	if semi {
		p.expectSemi()
	}
	return &ast.ExprStmt{X: lhs[0]}
}

func isCallLike(e ast.Expr) bool {
	switch x := e.(type) {
	case *ast.CallExpr:
		return true
	case *ast.TryExpr:
		return isCallLike(x.Call)
	}
	return false
}

// parseControlHeader parses a control-flow condition with composite literals
// suppressed, so the `{` that follows opens the body (spec 09 §1).
func (p *parser) parseControlHeader() ast.Expr {
	saved := p.noStructLit
	p.noStructLit = true
	e := p.parseExpr()
	p.noStructLit = saved
	return e
}

func (p *parser) parseIfStmt() ast.Stmt {
	kw := p.next().Pos
	s := &ast.IfStmt{Keyword: kw, Cond: p.parseControlHeader()}
	s.Then = p.parseBlock()
	if p.accept(token.ELSE) {
		if p.at(token.IF) {
			s.Else = p.parseIfStmt()
			return s
		}
		s.Else = p.parseBlock()
	}
	p.expectSemi()
	return s
}

func (p *parser) parseWhileStmt() ast.Stmt {
	kw := p.next().Pos
	s := &ast.WhileStmt{Keyword: kw, Cond: p.parseControlHeader()}
	s.Body = p.parseBlock()
	p.expectSemi()
	return s
}

// parseForStmt handles both forms. The range form is detected by scanning for
// `in` before the header ends.
func (p *parser) parseForStmt() ast.Stmt {
	kw := p.next().Pos

	if p.isRangeForm() {
		s := &ast.RangeStmt{Keyword: kw}
		s.Names = append(s.Names, p.parseIdent())
		for p.accept(token.COMMA) {
			s.Names = append(s.Names, p.parseIdent())
		}
		p.expect(token.IN, "in a for-in loop")
		s.X = p.parseControlHeader()
		s.Body = p.parseBlock()
		p.expectSemi()
		return s
	}

	s := &ast.ForStmt{Keyword: kw}
	saved := p.noStructLit
	p.noStructLit = true
	if !p.at(token.SEMI) {
		if p.at(token.VAR) {
			s.Init = p.parseVarDecl()
		} else {
			s.Init = p.parseSimpleStmt(false, true)
		}
	}
	p.expect(token.SEMI, "after the for loop's init clause")
	if !p.at(token.SEMI) {
		s.Cond = p.parseExpr()
	}
	p.expect(token.SEMI, "after the for loop's condition")
	if !p.at(token.LBRACE) {
		s.Post = p.parseSimpleStmt(false, true)
	}
	p.noStructLit = saved

	s.Body = p.parseBlock()
	p.expectSemi()
	return s
}

// isRangeForm reports whether the for header is `names... in expr`, by scanning
// the identifier-and-comma prefix for `in`.
func (p *parser) isRangeForm() bool {
	i := 0
	for {
		if p.peek(i).Kind != token.IDENT {
			return false
		}
		i++
		switch p.peek(i).Kind {
		case token.IN:
			return true
		case token.COMMA:
			i++
		default:
			return false
		}
	}
}

func (p *parser) parseMatchStmt() ast.Stmt {
	kw := p.next().Pos
	s := &ast.MatchStmt{Keyword: kw, X: p.parseControlHeader()}
	p.expect(token.LBRACE, "before the match arms")
	p.skipSemis()
	for !p.at(token.RBRACE) && !p.at(token.EOF) {
		arm := &ast.MatchArm{Pattern: p.parsePattern()}
		p.expect(token.FATARROW, "after the pattern")
		if p.at(token.LBRACE) {
			arm.Body = p.parseBlock()
			p.accept(token.COMMA) // optional after a block arm
		} else {
			arm.Body = p.parseMatchArmBody()
			p.accept(token.COMMA)
		}
		s.Arms = append(s.Arms, arm)
		p.skipSemis()
	}
	s.Rbrace = p.expect(token.RBRACE, "after the match arms").Pos
	p.expectSemi()
	return s
}

// parseMatchArmBody reads a single-statement arm body, where a comma terminates
// the arm rather than continuing the statement.
//
// A comma is therefore never available to separate multiple return values here,
// so a multi-value return needs a block arm (spec 05 §Arms). Resolving that
// ambiguity by lookahead was tried and is not worth it: `Rect(w, h) => return
// w, h` and `A => return x, B => ...` are genuinely indistinguishable without
// knowing the enum.
func (p *parser) parseMatchArmBody() ast.Stmt {
	switch p.kind() {
	case token.RETURN:
		kw := p.next().Pos
		s := &ast.ReturnStmt{Keyword: kw}
		s.SetEnd(shiftPos(kw, 6))
		if !p.at(token.COMMA) && !p.at(token.SEMI) && !p.at(token.RBRACE) {
			s.Results = append(s.Results, p.parseExpr())
			if p.at(token.COMMA) && !p.commaStartsNextArm() {
				p.errs.AddHint(p.tok().Pos,
					"a single-statement match arm cannot return multiple values",
					"use a block arm: `=> { return a, b }`")
				// Consume the rest so one mistake yields one diagnostic rather
				// than a cascade of pattern errors on the same line.
				for p.accept(token.COMMA) {
					if p.commaStartsNextArm() {
						break
					}
					s.Results = append(s.Results, p.parseExpr())
				}
			}
		}
		return s
	case token.BREAK, token.CONTINUE:
		t := p.next()
		return &ast.BranchStmt{Keyword: t.Pos, Tok: t.Kind}
	case token.SPAWN:
		kw := p.next().Pos
		return &ast.SpawnStmt{Keyword: kw, Call: p.parseExpr()}
	}
	return p.parseSimpleStmt(false, false)
}

func (p *parser) parsePattern() *ast.Pattern {
	start := p.tok().Pos
	pat := &ast.Pattern{StartPos: start}

	switch {
	case p.at(token.IDENT) && p.tok().Lit == "_":
		t := p.next()
		pat.IsWildcard = true
		pat.SetEnd(shiftPos(t.Pos, 1))
		return pat
	case p.at(token.NIL):
		t := p.next()
		pat.IsNil = true
		pat.SetEnd(shiftPos(t.Pos, 3))
		return pat
	}

	name := p.parseIdent()
	// A qualified pattern names its enum: `IOError.NotFound(p)`. Required when
	// matching a union (spec 06 §Qualified patterns).
	if p.accept(token.PERIOD) {
		pat.Enum = name
		pat.Variant = p.parseIdent()
	} else {
		pat.Variant = name
	}
	pat.SetEnd(pat.Variant.End())

	if p.accept(token.LPAREN) {
		for !p.at(token.RPAREN) && !p.at(token.EOF) {
			if p.at(token.IDENT) && p.tok().Lit == "_" {
				p.next()
				pat.Binds = append(pat.Binds, nil)
			} else {
				pat.Binds = append(pat.Binds, p.parseIdent())
			}
			if !p.accept(token.COMMA) {
				break
			}
		}
		rp := p.expect(token.RPAREN, "after the pattern bindings")
		pat.SetEnd(shiftPos(rp.Pos, 1))
	}
	return pat
}

func (p *parser) parseSelectStmt() ast.Stmt {
	kw := p.next().Pos
	s := &ast.SelectStmt{Keyword: kw}
	p.expect(token.LBRACE, "before the select cases")
	p.skipSemis()
	for p.at(token.CASE) {
		c := &ast.CommClause{Keyword: p.next().Pos}
		// `default` is a contextual identifier, not a keyword.
		if p.at(token.IDENT) && p.tok().Lit == "default" {
			p.next()
		} else {
			c.Comm = p.parseSimpleStmt(false, true)
		}
		p.expect(token.COLON, "after the select case")
		p.skipSemis()
		for !p.at(token.CASE) && !p.at(token.RBRACE) && !p.at(token.EOF) {
			before := p.pos
			if st := p.parseStmt(); st != nil {
				c.Body = append(c.Body, st)
			}
			p.skipSemis()
			if p.pos == before {
				p.next()
			}
		}
		c.SetEnd(p.tok().Pos)
		s.Cases = append(s.Cases, c)
	}
	s.Rbrace = p.expect(token.RBRACE, "after the select cases").Pos
	p.expectSemi()
	return s
}

func (p *parser) parseReturnStmt() ast.Stmt {
	kw := p.next().Pos
	s := &ast.ReturnStmt{Keyword: kw}
	s.SetEnd(shiftPos(kw, 6))
	if !p.at(token.SEMI) && !p.at(token.RBRACE) && !p.at(token.EOF) {
		s.Results = append(s.Results, p.parseExpr())
		for p.accept(token.COMMA) {
			s.Results = append(s.Results, p.parseExpr())
		}
	}
	p.expectSemi()
	return s
}

func (p *parser) parseSpawnStmt() ast.Stmt {
	kw := p.next().Pos
	call := p.parseExpr()
	if !isCallLike(call) {
		p.errs.AddHint(call.Pos(), "spawn takes a call",
			"write `spawn f(args)`")
	}
	p.expectSemi()
	return &ast.SpawnStmt{Keyword: kw, Call: call}
}

// commaStartsNextArm reports whether the comma at the cursor terminates the arm,
// by scanning for the `=>` that would follow the next arm's pattern. Reaching a
// closing brace or another top-level comma first means it does not, so what
// follows is a second return value.
func (p *parser) commaStartsNextArm() bool {
	// A trailing comma before the closing brace ends the last arm; the spec
	// permits it in every bracketed list.
	for i := 1; ; i++ {
		switch p.peek(i).Kind {
		case token.SEMI:
			continue
		case token.RBRACE, token.EOF:
			return true
		}
		break
	}

	depth := 0
	for i := 1; ; i++ {
		switch p.peek(i).Kind {
		case token.FATARROW:
			return depth == 0
		case token.LPAREN, token.LBRACK, token.LBRACE:
			depth++
		case token.RPAREN, token.RBRACK:
			depth--
		case token.RBRACE:
			if depth == 0 {
				return false
			}
			depth--
		case token.COMMA:
			if depth == 0 {
				return false
			}
		case token.EOF:
			return false
		}
	}
}

func shiftPos(p token.Position, n int) token.Position {
	p.Column += n
	p.Offset += n
	return p
}
