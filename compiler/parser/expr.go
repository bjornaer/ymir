package parser

import (
	"strconv"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
)

// precedence returns the binding power of a binary operator, or 0 if it is not
// one. Levels follow the table in docs/spec/04-expressions.md.
func precedence(k token.Kind) int {
	switch k {
	case token.LOR:
		return 1
	case token.LAND:
		return 2
	case token.EQL, token.NEQ:
		return 3
	case token.LSS, token.LEQ, token.GTR, token.GEQ:
		return 4
	case token.ADD, token.SUB:
		return 5
	case token.MUL, token.QUO, token.REM, token.AT:
		return 6
	case token.POW:
		return 7
	}
	return 0
}

// powPrecedence is the level of `**`, which is the one right-associative
// operator: 2 ** 3 ** 2 is 2 ** (3 ** 2).
const powPrecedence = 7

func (p *parser) parseExpr() ast.Expr { return p.parseBinaryExpr(1) }

func (p *parser) parseBinaryExpr(minPrec int) ast.Expr {
	x := p.parseUnaryExpr()
	for {
		prec := precedence(p.kind())
		if prec == 0 || prec < minPrec {
			return x
		}
		op := p.next()
		// Right-associative operators recurse at their own level; left-
		// associative ones recurse one level tighter.
		next := prec + 1
		if prec == powPrecedence {
			next = prec
		}
		y := p.parseBinaryExpr(next)
		if lit := complexLit(x, op.Kind, y); lit != nil {
			x = lit
			continue
		}
		x = &ast.BinaryExpr{X: x, OpPos: op.Pos, Op: op.Kind, Y: y}
	}
}

// complexLit folds `a + bi` into a single complex literal, or returns nil.
//
// Resolved question R7: a complex literal is a numeric literal, then `+` or `-`,
// then an imaginary literal. `0.0 + 0.0i` is one constant of type complex, not
// float + complex — which the operand table of spec 04 would reject, leaving
// complex with no writable zero value.
//
// This is done here rather than in the lexer deliberately. Lexing `1.0+2.0i` as
// one token requires deciding where the literal ends, and the only signal is
// whitespace, so `1.0+2.0i` and `1.0 + 2.0i` would lex differently. That is the
// maximal-munch ambiguity that made the legacy lexer read `x==-3` as `x` `==-`
// `3`, and it would make the language depend on spacing. Folding here gives the
// same surface language with no lexer change.
//
// Both parts MUST be literals. `x + 2.0i` for a `float` binding x stays a
// BinaryExpr, and the checker rejects it: there is no implicit conversion.
func complexLit(x ast.Expr, op token.Kind, y ast.Expr) *ast.BasicLit {
	if op != token.ADD && op != token.SUB {
		return nil
	}
	im, ok := y.(*ast.BasicLit)
	if !ok || im.Kind != token.IMAG {
		return nil
	}

	// The real part is a numeric literal, optionally negated: `-1.0 + 2.0i`
	// parses as unary minus applied to a literal.
	re, isLit := x.(*ast.BasicLit)
	neg := false
	if !isLit {
		u, isUnary := x.(*ast.UnaryExpr)
		if !isUnary || u.Op != token.SUB {
			return nil
		}
		re, _ = u.X.(*ast.BasicLit)
		neg = true
	}
	if re == nil || (re.Kind != token.INT && re.Kind != token.FLOAT) {
		return nil
	}

	text := re.Value
	if neg {
		text = "-" + text
	}
	if op == token.ADD {
		text += "+"
	} else {
		text += "-"
	}
	text += im.Value

	start := x.Pos()
	width := im.End().Offset - start.Offset
	return ast.NewBasicLit(start, token.IMAG, text, width)
}

func (p *parser) parseUnaryExpr() ast.Expr {
	switch p.kind() {
	case token.SUB, token.NOT:
		op := p.next()
		return &ast.UnaryExpr{OpPos: op.Pos, Op: op.Kind, X: p.parseUnaryOperand()}

	case token.CHAN_OP:
		// Receive: `<-ch`. A send is a statement and is handled there.
		op := p.next()
		return &ast.UnaryExpr{OpPos: op.Pos, Op: op.Kind, X: p.parseUnaryOperand()}

	case token.ADD:
		// Unary plus is not in the grammar; it is always a no-op or a typo.
		op := p.next()
		p.errs.AddHint(op.Pos, "unary `+` is not an operator", "remove it")
		return p.parseUnaryExpr()

	case token.TRY:
		// `try f()` (spec 06 §Propagation). Binds tighter than any binary
		// operator, so `try f() + 1` is `(try f()) + 1`.
		kw := p.next().Pos
		call := p.parsePostfixExpr()
		if !isCallLike(call) {
			p.errs.AddHint(call.Pos(), "`try` applies to a call",
				"write `try f(args)`; try is error propagation, not a block")
		}
		return &ast.TryExpr{Keyword: kw, Call: call}
	}
	return p.parsePostfixExpr()
}

// parseUnaryOperand reads the operand of a unary operator at the exponent
// level, so `**` binds tighter than unary minus: spec 04 gives `-x ** 2` as
// `-(x ** 2)`. Looser operators still bind less tightly, so `-a * b` is
// `(-a) * b`.
func (p *parser) parseUnaryOperand() ast.Expr {
	return p.parseBinaryExpr(powPrecedence)
}

func (p *parser) parsePostfixExpr() ast.Expr {
	x := p.parsePrimaryExpr()
	for {
		switch p.kind() {
		case token.LPAREN:
			x = p.parseCallSuffix(x)

		case token.LBRACK:
			p.next()
			idx := p.parseExprAllowingStructLit()
			rb := p.expect(token.RBRACK, "after the index")
			x = &ast.IndexExpr{X: x, Index: idx, Rbrack: rb.Pos}

		case token.PERIOD:
			p.next()
			// `t.0` is tuple indexing; the index must be an integer literal
			// (spec 04 §Indexing and selection).
			if p.at(token.INT) {
				t := p.next()
				n, err := strconv.Atoi(t.Lit)
				if err != nil {
					p.errs.Addf(t.Pos, "invalid tuple index %s", t.Lit)
					n = 0
				}
				x = ast.NewTupleIndex(x, n, t.Pos, len(t.Lit))
				continue
			}
			x = &ast.SelectorExpr{X: x, Sel: p.parseIdent()}

		case token.LBRACE:
			// A composite literal, but only where one is legal: `Point{...}`
			// after a type name. In a control-flow header `{` opens the body
			// instead (spec 09 §1).
			if p.noStructLit || !isTypeName(x) {
				return x
			}
			x = p.parseStructLitSuffix(x)

		default:
			return x
		}
	}
}

func (p *parser) parseCallSuffix(fun ast.Expr) ast.Expr {
	p.next() // '('
	call := &ast.CallExpr{Fun: fun}
	// Arguments are a fresh context: a composite literal is legal inside the
	// parentheses even within a control-flow header.
	saved := p.noStructLit
	p.noStructLit = false
	for !p.at(token.RPAREN) && !p.at(token.EOF) {
		call.Args = append(call.Args, p.parseExpr())
		if !p.accept(token.COMMA) {
			break
		}
	}
	p.noStructLit = saved
	call.Rparen = p.expect(token.RPAREN, "after the arguments").Pos
	return call
}

func (p *parser) parseStructLitSuffix(typ ast.Expr) ast.Expr {
	p.next() // '{'
	lit := &ast.StructLit{Type: exprAsType(typ)}
	saved := p.noStructLit
	p.noStructLit = false
	p.skipSemis()
	for !p.at(token.RBRACE) && !p.at(token.EOF) {
		f := &ast.FieldInit{Name: p.parseIdent()}
		p.expect(token.COLON, "after the field name")
		f.Value = p.parseExpr()
		lit.Fields = append(lit.Fields, f)
		if !p.accept(token.COMMA) {
			p.skipSemis()
			break
		}
		p.skipSemis()
	}
	p.noStructLit = saved
	lit.Rbrace = p.expect(token.RBRACE, "after the field values").Pos
	return lit
}

// parseExprAllowingStructLit parses inside brackets, where a composite literal
// is unambiguous regardless of the enclosing header.
func (p *parser) parseExprAllowingStructLit() ast.Expr {
	saved := p.noStructLit
	p.noStructLit = false
	e := p.parseExpr()
	p.noStructLit = saved
	return e
}

func (p *parser) parsePrimaryExpr() ast.Expr {
	t := p.tok()
	switch t.Kind {
	case token.INT, token.FLOAT, token.IMAG:
		p.next()
		return ast.NewBasicLit(t.Pos, t.Kind, t.Lit, len(t.Lit))

	case token.STRING:
		p.next()
		// Lit is already decoded; width comes from the source span so End is
		// accurate over escapes.
		return ast.NewBasicLit(t.Pos, token.STRING, t.Lit, p.sourceWidth(t))

	case token.TRUE:
		p.next()
		return &ast.BoolLit{ValuePos: t.Pos, Value: true}
	case token.FALSE:
		p.next()
		return &ast.BoolLit{ValuePos: t.Pos, Value: false}
	case token.NIL:
		p.next()
		return &ast.NilLit{ValuePos: t.Pos}

	case token.IDENT:
		p.next()
		return &ast.Ident{NamePos: t.Pos, Name: t.Lit}

	case token.QUBIT, token.MEASURE, token.RESET, token.DISCARD:
		// Reserved words that name builtin operations (spec 08). They are
		// reserved so they cannot be shadowed, but they are callable, so in
		// expression position they behave as identifiers.
		p.next()
		return &ast.Ident{NamePos: t.Pos, Name: t.Kind.String()}

	case token.FUNC:
		return p.parseFuncLit()

	case token.LBRACK:
		return p.parseArrayLit()

	case token.LBRACE:
		return p.parseMapLit()

	case token.LPAREN:
		return p.parseParenOrTuple()
	}

	p.errs.Addf(t.Pos, "expected an expression, found %s", describe(t))
	from := t.Pos
	if !p.at(token.SEMI) && !p.at(token.RBRACE) && !p.at(token.EOF) {
		p.next()
	}
	return &ast.BadExpr{From: from, To: p.tok().Pos}
}

// sourceWidth measures a token's span in the source, which differs from the
// decoded literal's length whenever escapes are present.
func (p *parser) sourceWidth(t token.Token) int {
	next := p.tok()
	if next.Pos.Line == t.Pos.Line && next.Pos.Offset > t.Pos.Offset {
		return next.Pos.Offset - t.Pos.Offset
	}
	return len(t.Lit) + 2 // fall back to the decoded value plus quotes
}

func (p *parser) parseFuncLit() ast.Expr {
	kw := p.next().Pos
	lit := &ast.FuncLit{Keyword: kw, Params: p.parseParams()}
	if p.accept(token.ARROW) {
		lit.Results = p.parseResultTypes()
	}
	saved := p.noStructLit
	p.noStructLit = false
	lit.Body = p.parseBlock()
	p.noStructLit = saved
	return lit
}

func (p *parser) parseArrayLit() ast.Expr {
	lb := p.next().Pos
	lit := &ast.ArrayLit{Lbrack: lb}
	saved := p.noStructLit
	p.noStructLit = false
	p.skipSemis()
	for !p.at(token.RBRACK) && !p.at(token.EOF) {
		lit.Elements = append(lit.Elements, p.parseExpr())
		if !p.accept(token.COMMA) {
			p.skipSemis()
			break
		}
		p.skipSemis()
	}
	p.noStructLit = saved
	lit.Rbrack = p.expect(token.RBRACK, "after the array elements").Pos
	return lit
}

func (p *parser) parseMapLit() ast.Expr {
	lb := p.next().Pos
	lit := &ast.MapLit{Lbrace: lb}
	saved := p.noStructLit
	p.noStructLit = false
	p.skipSemis()
	for !p.at(token.RBRACE) && !p.at(token.EOF) {
		kv := &ast.KeyValue{Key: p.parseExpr()}
		p.expect(token.COLON, "between the key and value")
		kv.Value = p.parseExpr()
		lit.Entries = append(lit.Entries, kv)
		if !p.accept(token.COMMA) {
			p.skipSemis()
			break
		}
		p.skipSemis()
	}
	p.noStructLit = saved
	lit.Rbrace = p.expect(token.RBRACE, "after the map entries").Pos
	return lit
}

// parseParenOrTuple distinguishes `(x)` from `(x,)` and `(x, y)`. A one-element
// tuple requires the trailing comma (spec 09 §2).
func (p *parser) parseParenOrTuple() ast.Expr {
	lp := p.next().Pos
	saved := p.noStructLit
	p.noStructLit = false
	defer func() { p.noStructLit = saved }()

	if p.at(token.RPAREN) {
		rp := p.next().Pos
		p.errs.AddHint(lp, "empty parentheses are not an expression",
			"a zero-element tuple has no type in Ymir")
		return &ast.BadExpr{From: lp, To: rp}
	}

	first := p.parseExpr()
	if !p.at(token.COMMA) {
		rp := p.expect(token.RPAREN, "after the expression")
		return &ast.ParenExpr{Lparen: lp, X: first, Rparen: rp.Pos}
	}

	lit := &ast.TupleLit{Lparen: lp, Elements: []ast.Expr{first}}
	for p.accept(token.COMMA) {
		if p.at(token.RPAREN) {
			break // trailing comma
		}
		lit.Elements = append(lit.Elements, p.parseExpr())
	}
	lit.Rparen = p.expect(token.RPAREN, "after the tuple elements").Pos
	return lit
}

// isTypeName reports whether an expression could name a type, and so could be
// followed by a composite literal body.
func isTypeName(e ast.Expr) bool {
	switch x := e.(type) {
	case *ast.Ident:
		return true
	case *ast.SelectorExpr:
		return isTypeName(x.X)
	}
	return false
}

// exprAsType reinterprets a parsed expression as the type of a composite
// literal. Only names reach here, guarded by isTypeName.
func exprAsType(e ast.Expr) ast.Type {
	switch x := e.(type) {
	case *ast.Ident:
		return &ast.NamedType{Name: &ast.QualifiedIdent{Parts: []*ast.Ident{x}}}
	case *ast.SelectorExpr:
		if inner, ok := exprAsType(x.X).(*ast.NamedType); ok {
			return &ast.NamedType{Name: &ast.QualifiedIdent{
				Parts: append(append([]*ast.Ident{}, inner.Name.Parts...), x.Sel)}}
		}
	}
	return &ast.NamedType{Name: &ast.QualifiedIdent{
		Parts: []*ast.Ident{{NamePos: e.Pos(), Name: "_"}}}}
}
