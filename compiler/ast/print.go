package ast

import (
	"fmt"
	"io"
	"strconv"
	"strings"

	"github.com/bjornaer/ymir/compiler/token"
)

// Fprint writes an indented tree rendering of n. It is a debugging aid for
// `ymir parse`, not a formatter: it shows structure, not source.
func Fprint(w io.Writer, n any) error {
	p := &printer{w: w}
	p.node(n, 0)
	return p.err
}

// Sprint renders n to a string.
func Sprint(n any) string {
	var b strings.Builder
	_ = Fprint(&b, n)
	return b.String()
}

type printer struct {
	w   io.Writer
	err error
}

func (p *printer) printf(format string, args ...any) {
	if p.err != nil {
		return
	}
	_, p.err = fmt.Fprintf(p.w, format, args...)
}

func (p *printer) line(depth int, format string, args ...any) {
	p.printf("%s%s\n", strings.Repeat("  ", depth), fmt.Sprintf(format, args...))
}

func (p *printer) node(n any, d int) {
	switch x := n.(type) {
	case nil:
		return

	case *File:
		p.line(d, "File")
		if x.Module != nil {
			p.node(x.Module, d+1)
		}
		for _, im := range x.Imports {
			p.node(im, d+1)
		}
		for _, dec := range x.Decls {
			p.node(dec, d+1)
		}

	case *ModuleDecl:
		p.line(d, "Module %s", x.Name)
	case *ImportDecl:
		if x.Alias != nil {
			p.line(d, "Import %s as %s", x.Path, x.Alias.Name)
		} else {
			p.line(d, "Import %s", x.Path)
		}

	case *FuncDecl:
		kind := "Func"
		if x.IsGate {
			kind = "Gate"
		} else if x.Recv != nil {
			kind = "Method"
		}
		p.line(d, "%s %s%s", kind, x.Name.Name, exportMark(x.Export))
		if x.Recv != nil {
			p.line(d+1, "Recv %s%s: %s", x.Recv.Name.Name, mutMark(x.Recv.Mut), typeStr(x.Recv.Type))
		}
		for _, prm := range x.Params {
			p.line(d+1, "Param %s%s: %s", prm.Name.Name, mutMark(prm.Mut), typeStr(prm.Type))
		}
		for _, r := range x.Results {
			p.line(d+1, "Result %s", typeStr(r))
		}
		p.node(x.Body, d+1)

	case *StructDecl:
		p.line(d, "Struct %s%s", x.Name.Name, exportMark(x.Export))
		for _, f := range x.Fields {
			p.line(d+1, "Field %s: %s", f.Name.Name, typeStr(f.Type))
		}

	case *EnumDecl:
		p.line(d, "Enum %s%s", x.Name.Name, exportMark(x.Export))
		for _, v := range x.Variants {
			if len(v.Payload) == 0 {
				p.line(d+1, "Variant %s", v.Name.Name)
				continue
			}
			parts := make([]string, len(v.Payload))
			for i, t := range v.Payload {
				parts[i] = typeStr(t)
			}
			p.line(d+1, "Variant %s(%s)", v.Name.Name, strings.Join(parts, ", "))
		}

	case *ConstDecl:
		p.line(d, "Const %s: %s%s", x.Name.Name, typeStr(x.Type), exportMark(x.Export))
		p.node(x.Value, d+1)

	case *VarDecl:
		if x.Type != nil {
			p.line(d, "Var %s: %s", x.Name.Name, typeStr(x.Type))
		} else {
			p.line(d, "Var %s (inferred)", x.Name.Name)
		}
		p.node(x.Value, d+1)

	case *BlockStmt:
		p.line(d, "Block")
		for _, s := range x.Stmts {
			p.node(s, d+1)
		}

	case *ExprStmt:
		p.line(d, "ExprStmt")
		p.node(x.X, d+1)

	case *AssignStmt:
		p.line(d, "Assign %s", x.Tok)
		for _, e := range x.Lhs {
			p.node(e, d+1)
		}
		p.line(d+1, "<-")
		for _, e := range x.Rhs {
			p.node(e, d+1)
		}

	case *IncDecStmt:
		p.line(d, "IncDec %s", x.Tok)
		p.node(x.X, d+1)

	case *IfStmt:
		p.line(d, "If")
		p.node(x.Cond, d+1)
		p.node(x.Then, d+1)
		if x.Else != nil {
			p.line(d+1, "Else")
			p.node(x.Else, d+2)
		}

	case *WhileStmt:
		p.line(d, "While")
		p.node(x.Cond, d+1)
		p.node(x.Body, d+1)

	case *RangeStmt:
		names := make([]string, len(x.Names))
		for i, n := range x.Names {
			names[i] = n.Name
		}
		p.line(d, "ForIn %s", strings.Join(names, ", "))
		p.node(x.X, d+1)
		p.node(x.Body, d+1)

	case *ForStmt:
		p.line(d, "For")
		p.node(x.Init, d+1)
		p.node(x.Cond, d+1)
		p.node(x.Post, d+1)
		p.node(x.Body, d+1)

	case *MatchStmt:
		p.line(d, "Match")
		p.node(x.X, d+1)
		for _, arm := range x.Arms {
			p.line(d+1, "Arm %s", patternStr(arm.Pattern))
			p.node(arm.Body, d+2)
		}

	case *SelectStmt:
		p.line(d, "Select")
		for _, c := range x.Cases {
			if c.Comm == nil {
				p.line(d+1, "Default")
			} else {
				p.line(d+1, "Case")
				p.node(c.Comm, d+2)
			}
			for _, s := range c.Body {
				p.node(s, d+2)
			}
		}

	case *ReturnStmt:
		p.line(d, "Return")
		for _, e := range x.Results {
			p.node(e, d+1)
		}

	case *BranchStmt:
		if x.Tok == token.BREAK {
			p.line(d, "Break")
		} else {
			p.line(d, "Continue")
		}

	case *SpawnStmt:
		p.line(d, "Spawn")
		p.node(x.Call, d+1)

	case *SendStmt:
		p.line(d, "Send")
		p.node(x.Chan, d+1)
		p.node(x.Value, d+1)

	case *BadStmt:
		p.line(d, "BadStmt")
	case *BadExpr:
		p.line(d, "BadExpr")

	case *Ident:
		p.line(d, "Ident %s", x.Name)

	case *BasicLit:
		p.line(d, "Lit %s %s", x.Kind, strconv.Quote(x.Value))
	case *BoolLit:
		p.line(d, "Lit bool %t", x.Value)
	case *NilLit:
		p.line(d, "Lit nil")

	case *UnaryExpr:
		p.line(d, "Unary %s", x.Op)
		p.node(x.X, d+1)

	case *BinaryExpr:
		p.line(d, "Binary %s", x.Op)
		p.node(x.X, d+1)
		p.node(x.Y, d+1)

	case *ParenExpr:
		p.line(d, "Paren")
		p.node(x.X, d+1)

	case *CallExpr:
		p.line(d, "Call")
		p.node(x.Fun, d+1)
		for _, a := range x.Args {
			p.node(a, d+1)
		}

	case *TryExpr:
		p.line(d, "Try")
		p.node(x.Call, d+1)

	case *IndexExpr:
		p.line(d, "Index")
		p.node(x.X, d+1)
		p.node(x.Index, d+1)

	case *SelectorExpr:
		p.line(d, "Selector .%s", x.Sel.Name)
		p.node(x.X, d+1)

	case *TupleIndexExpr:
		p.line(d, "TupleIndex .%d", x.Index)
		p.node(x.X, d+1)

	case *ArrayLit:
		p.line(d, "ArrayLit")
		for _, e := range x.Elements {
			p.node(e, d+1)
		}

	case *MapLit:
		p.line(d, "MapLit")
		for _, kv := range x.Entries {
			p.node(kv.Key, d+1)
			p.node(kv.Value, d+2)
		}

	case *TupleLit:
		p.line(d, "TupleLit")
		for _, e := range x.Elements {
			p.node(e, d+1)
		}

	case *StructLit:
		p.line(d, "StructLit %s", typeStr(x.Type))
		for _, f := range x.Fields {
			p.line(d+1, "Field %s", f.Name.Name)
			p.node(f.Value, d+2)
		}

	case *FuncLit:
		p.line(d, "FuncLit")
		for _, prm := range x.Params {
			p.line(d+1, "Param %s%s: %s", prm.Name.Name, mutMark(prm.Mut), typeStr(prm.Type))
		}
		for _, r := range x.Results {
			p.line(d+1, "Result %s", typeStr(r))
		}
		p.node(x.Body, d+1)

	default:
		p.line(d, "%T", n)
	}
}

func exportMark(b bool) string {
	if b {
		return " (export)"
	}
	return ""
}

func mutMark(b bool) string {
	if b {
		return " mut"
	}
	return ""
}

func patternStr(p *Pattern) string {
	switch {
	case p == nil:
		return "?"
	case p.IsWildcard:
		return "_"
	case p.IsNil:
		return "nil"
	}
	s := ""
	if p.Enum != nil {
		s = p.Enum.Name + "."
	}
	s += p.Variant.Name
	if len(p.Binds) > 0 {
		parts := make([]string, len(p.Binds))
		for i, b := range p.Binds {
			if b == nil {
				parts[i] = "_"
			} else {
				parts[i] = b.Name
			}
		}
		s += "(" + strings.Join(parts, ", ") + ")"
	}
	return s
}

// typeStr renders a syntactic type back to something close to source.
func typeStr(t Type) string {
	switch x := t.(type) {
	case nil:
		return "?"
	case *NamedType:
		return x.Name.String()
	case *GenericType:
		if x.Width != nil {
			return x.Name.Name + "[" + x.Width.Value + "]"
		}
		parts := make([]string, len(x.Args))
		for i, a := range x.Args {
			parts[i] = typeStr(a)
		}
		return x.Name.Name + "[" + strings.Join(parts, ", ") + "]"
	case *NullableType:
		// Parenthesize a union so the rendering round-trips: `?A | B` would
		// read as a union of `?A` and `B`.
		if _, isUnion := x.Elem.(*UnionType); isUnion {
			return "?(" + typeStr(x.Elem) + ")"
		}
		return "?" + typeStr(x.Elem)
	case *UnionType:
		parts := make([]string, len(x.Members))
		for i, m := range x.Members {
			parts[i] = typeStr(m)
		}
		return strings.Join(parts, " | ")
	case *FuncType:
		params := make([]string, len(x.Params))
		for i, prm := range x.Params {
			params[i] = typeStr(prm)
		}
		s := "func(" + strings.Join(params, ", ") + ")"
		if len(x.Results) == 1 {
			return s + " -> " + typeStr(x.Results[0])
		}
		if len(x.Results) > 1 {
			rs := make([]string, len(x.Results))
			for i, r := range x.Results {
				rs[i] = typeStr(r)
			}
			return s + " -> (" + strings.Join(rs, ", ") + ")"
		}
		return s
	}
	return "?"
}
