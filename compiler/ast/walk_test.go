package ast

import (
	"fmt"
	"os"
	"regexp"
	"strings"
	"testing"

	"github.com/bjornaer/ymir/compiler/token"
)

// collector records the concrete Go type of every node Walk visits.
type collector struct{ seen map[string]int }

func (c *collector) Visit(n Node) Visitor {
	if n == nil {
		return nil
	}
	c.seen[fmt.Sprintf("%T", n)]++
	return c
}

func walkAll(n Node) map[string]int {
	c := &collector{seen: map[string]int{}}
	Walk(c, n)
	return c.seen
}

// Minimal well-formed children. The parser guarantees these are non-nil, so
// Walk descends into them without a guard; only the genuinely optional fields
// (VarDecl.Type, IfStmt.Else, Param.Type, CommClause.Comm, Pattern.Variant,
// and the nil entries in Pattern.Binds) are nil-checked.
func id() *Ident           { return &Ident{Name: "x"} }
func qid() *QualifiedIdent { return &QualifiedIdent{Parts: []*Ident{id()}} }
func ty() Type             { return &NamedType{Name: qid()} }
func ex() Expr             { return &BasicLit{Kind: token.INT, Value: "1"} }
func blk() *BlockStmt      { return &BlockStmt{Stmts: []Stmt{&ExprStmt{X: ex()}}} }
func pat() *Pattern        { return &Pattern{Variant: id(), Binds: []*Ident{id(), nil}} }
func prm() *Param          { return &Param{Name: id(), Type: ty()} }
func kv() *KeyValue        { return &KeyValue{Key: ex(), Value: ex()} }
func fi() *FieldInit       { return &FieldInit{Name: id(), Value: ex()} }
func arm() *MatchArm       { return &MatchArm{Pattern: pat(), Body: blk()} }
func comm() *CommClause    { return &CommClause{Body: []Stmt{&ExprStmt{X: ex()}}} }
func fld() *Field          { return &Field{Name: id(), Type: ty()} }
func vnt() *Variant        { return &Variant{Name: id(), Payload: []Type{ty()}} }
func fn() *FuncDecl {
	return &FuncDecl{Name: id(), Params: []*Param{prm()}, Results: []Type{ty()}, Body: blk()}
}

// TestWalkHandlesEveryNodeKind is the coverage gate. Walk panics on a node kind
// its switch does not name, so adding an AST node without adding it to walk.go
// fails here rather than silently going unchecked by the type checker.
//
// Every node kind in ast.go must appear in this table.
func TestWalkHandlesEveryNodeKind(t *testing.T) {
	nodes := []Node{
		// File and names
		&File{Module: &ModuleDecl{Name: qid()}, Imports: []*ImportDecl{{Path: qid()}}, Decls: []Decl{fn()}},
		id(),
		qid(),

		// Declarations
		&ModuleDecl{Name: qid()},
		&ImportDecl{Path: qid(), Alias: id()},
		prm(),
		fn(),
		fld(),
		&StructDecl{Name: id(), Fields: []*Field{fld()}},
		vnt(),
		&EnumDecl{Name: id(), Variants: []*Variant{vnt()}},
		&ConstDecl{Name: id(), Type: ty(), Value: ex()},
		&VarDecl{Name: id(), Type: ty(), Value: ex()},
		&VarDecl{Name: id()}, // no type, no initializer: both fields nil

		// Types
		&NamedType{Name: qid()},
		&GenericType{Name: id(), Args: []Type{ty()}},
		&FuncType{Params: []Type{ty()}, Results: []Type{ty()}},
		&NullableType{Elem: ty()},
		&UnionType{Members: []Type{ty(), ty()}},

		// Expressions
		&BasicLit{Kind: token.INT, Value: "1"},
		&BoolLit{Value: true},
		&NilLit{},
		&BadExpr{},
		&UnaryExpr{Op: token.SUB, X: ex()},
		&BinaryExpr{X: ex(), Op: token.ADD, Y: ex()},
		&CallExpr{Fun: ex(), Args: []Expr{ex()}},
		&TryExpr{Call: ex()},
		&IndexExpr{X: ex(), Index: ex()},
		&SelectorExpr{X: ex(), Sel: id()},
		&TupleIndexExpr{X: ex()},
		&ParenExpr{X: ex()},
		&ArrayLit{Elements: []Expr{ex()}},
		kv(),
		&MapLit{Entries: []*KeyValue{kv()}},
		&TupleLit{Elements: []Expr{ex()}},
		fi(),
		&StructLit{Type: ty(), Fields: []*FieldInit{fi()}},
		&FuncLit{Params: []*Param{prm()}, Results: []Type{ty()}, Body: blk()},

		// Statements
		blk(),
		&ExprStmt{X: ex()},
		&AssignStmt{Lhs: []Expr{ex()}, Tok: token.DEFINE, Rhs: []Expr{ex()}},
		&IncDecStmt{X: ex(), Tok: token.INC},
		&IfStmt{Cond: ex(), Then: blk(), Else: blk()},
		&IfStmt{Cond: ex(), Then: blk()}, // no else
		&WhileStmt{Cond: ex(), Body: blk()},
		&RangeStmt{Names: []*Ident{id()}, X: ex(), Body: blk()},
		&ForStmt{Init: &ExprStmt{X: ex()}, Cond: ex(), Post: &ExprStmt{X: ex()}, Body: blk()},
		&ForStmt{Body: blk()}, // all three clauses nil
		pat(),
		&Pattern{IsWildcard: true},          // Variant and Enum nil
		&Pattern{IsNil: true},               // likewise
		&Pattern{Enum: id(), Variant: id()}, // qualified
		arm(),
		&MatchStmt{X: ex(), Arms: []*MatchArm{arm()}},
		&ReturnStmt{Results: []Expr{ex()}},
		&ReturnStmt{}, // bare return
		&BranchStmt{Tok: token.BREAK},
		&BadStmt{},
		&SpawnStmt{Call: ex()},
		&SendStmt{Chan: ex(), Value: ex()},
		comm(),
		&CommClause{Comm: &ExprStmt{X: ex()}, Body: []Stmt{&ExprStmt{X: ex()}}},
		&SelectStmt{Cases: []*CommClause{comm()}},
	}

	covered := map[string]bool{}
	for _, n := range nodes {
		name := fmt.Sprintf("%T", n)
		covered[strings.TrimPrefix(name, "*ast.")] = true
		t.Run(name, func(t *testing.T) {
			defer func() {
				if r := recover(); r != nil {
					t.Fatalf("Walk panicked on %s: %v", name, r)
				}
			}()
			if seen := walkAll(n); seen[name] != 1 {
				t.Errorf("Walk visited %s %d times, want 1", name, seen[name])
			}
		})
	}

	// The table above is hand-maintained, so check it against the source of
	// truth: every node struct declared in ast.go must be exercised. Without
	// this, adding a node and forgetting both walk.go and this table would go
	// unnoticed until a rule quietly stopped being enforced.
	src, err := os.ReadFile("ast.go")
	if err != nil {
		t.Fatalf("reading ast.go: %v", err)
	}
	decl := regexp.MustCompile(`(?m)^type (\w+) struct`)
	for _, m := range decl.FindAllStringSubmatch(string(src), -1) {
		if !covered[m[1]] {
			t.Errorf("ast.%s is declared in ast.go but not exercised by TestWalkHandlesEveryNodeKind", m[1])
		}
	}
}

func TestWalkDescendsIntoChildren(t *testing.T) {
	// `x + 1` inside a block inside a function: the walk must reach the leaf.
	f := &FuncDecl{
		Name: id(),
		Body: &BlockStmt{Stmts: []Stmt{
			&ExprStmt{X: &BinaryExpr{X: id(), Op: token.ADD, Y: ex()}},
		}},
	}
	seen := walkAll(f)
	for _, want := range []string{
		"*ast.FuncDecl", "*ast.BlockStmt", "*ast.ExprStmt", "*ast.BinaryExpr",
		"*ast.Ident", "*ast.BasicLit",
	} {
		if seen[want] == 0 {
			t.Errorf("Walk never reached %s", want)
		}
	}
	if seen["*ast.Ident"] != 2 { // the function's name and the operand
		t.Errorf("visited %d idents, want 2", seen["*ast.Ident"])
	}
}

func TestInspectPrunes(t *testing.T) {
	f := &FuncDecl{Name: id(), Body: blk()}

	var reached []string
	Inspect(f, func(n Node) bool {
		reached = append(reached, fmt.Sprintf("%T", n))
		// Do not descend into the body.
		_, isBlock := n.(*BlockStmt)
		return !isBlock
	})

	for _, r := range reached {
		if r == "*ast.ExprStmt" {
			t.Error("Inspect descended into a subtree the visitor pruned")
		}
	}
	if len(reached) == 0 {
		t.Fatal("Inspect visited nothing")
	}
}

func TestWalkSkipsNilChildren(t *testing.T) {
	// Every optional field left nil at once. The walk must not panic and must
	// not visit a nil node.
	n := &VarDecl{Name: id()}
	c := &collector{seen: map[string]int{}}
	Walk(c, n)
	if c.seen["<nil>"] != 0 {
		t.Error("Walk visited a nil node")
	}
}
