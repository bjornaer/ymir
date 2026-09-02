package bytecode

import (
	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/check"
	"github.com/bjornaer/ymir/compiler/diag"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Compiling a checked syntax tree.
//
// The input MUST have passed compiler/check. This pass does not re-derive
// types, it reads them out of check.Info — that is the whole reason Phase 2 kept
// them in a side table keyed by node instead of throwing them away. A construct
// the checker rejected can never reach here, so anything this pass cannot
// compile is a gap in the compiler rather than a program error, and it says so.

// Compile turns a checked file into a program.
//
// Diagnostics are returned rather than panicked, so a construct that is not yet
// implemented reports its position and exits non-zero. Silence would be the
// legacy failure mode all over again.
func Compile(file *ast.File, info *check.Info, name, src string) (*Program, *diag.List) {
	c := &compiler{
		info:    info,
		errs:    diag.NewList(name, src),
		program: &Program{File: name, Main: -1},
		funcIdx: map[string]int{},
		globals: map[string]int32{},
	}
	c.run(file)
	c.errs.Sort()
	return c.program, c.errs
}

type compiler struct {
	info    *check.Info
	errs    *diag.List
	program *Program

	funcIdx map[string]int   // function name -> index into Program.Funcs
	globals map[string]int32 // module-level var name -> global slot

	fn     *Function // the function being compiled
	locals []local   // its locals, innermost last
	scopes []int     // the number of locals at each open block's start
	slots  int       // the high-water mark of locals, for Function.Slots
	obj    map[*check.Object]int32
}

// A local is one slot in the current frame.
type local struct {
	name string
	obj  *check.Object
	slot int32
}

func (c *compiler) run(file *ast.File) {
	if file == nil {
		return
	}

	// Two passes over the declarations, for the same reason the checker needs
	// them: a call may name a function declared later (chapter 03 §Scope), so
	// every function must have an index before any body is compiled.
	for _, d := range file.Decls {
		switch x := d.(type) {
		case *ast.FuncDecl:
			if x.Recv != nil {
				continue // methods arrive with structs in Phase 4
			}
			c.funcIdx[x.Name.Name] = len(c.program.Funcs)
			c.program.Funcs = append(c.program.Funcs, &Function{
				Name:    x.Name.Name,
				Arity:   len(x.Params),
				Results: len(x.Results),
			})
		case *ast.VarDecl:
			slot := int32(len(c.program.Globals))
			c.globals[x.Name.Name] = slot
			c.program.Globals = append(c.program.Globals, x.Name.Name)
		}
	}

	for _, d := range file.Decls {
		x, isFunc := d.(*ast.FuncDecl)
		if !isFunc || x.Recv != nil {
			continue
		}
		c.function(x)
	}

	if idx, ok := c.funcIdx["main"]; ok {
		c.program.Main = idx
		c.program.MainReturnsError = c.program.Funcs[idx].Results > 0
	}
}

// function compiles one function body into its already-allocated Function.
func (c *compiler) function(d *ast.FuncDecl) {
	c.fn = c.program.Funcs[c.funcIdx[d.Name.Name]]
	c.locals = c.locals[:0]
	c.scopes = c.scopes[:0]
	c.slots = 0
	c.obj = map[*check.Object]int32{}

	// Parameters occupy the first slots, in order.
	for _, p := range d.Params {
		c.declareLocal(p.Name)
	}

	if d.Body != nil {
		c.block(d.Body)
	}

	// Every function ends in a return. The checker has already proved that a
	// function with results returns on every path (chapter 05), so this is
	// reached only by one with none — where falling off the end is the return.
	c.emit(OpReturn, 0, d.Body.Rbrace)
	c.fn.Slots = c.slots
}

// ---------------------------------------------------------------------------
// Scopes and locals

func (c *compiler) beginScope() { c.scopes = append(c.scopes, len(c.locals)) }

// endScope drops the block's locals and pops their slots off the stack.
func (c *compiler) endScope(at token.Position) {
	n := c.scopes[len(c.scopes)-1]
	c.scopes = c.scopes[:len(c.scopes)-1]
	for len(c.locals) > n {
		c.emit(OpPop, 0, at)
		c.locals = c.locals[:len(c.locals)-1]
	}
}

// declareLocal gives a name the next slot. Shadowing is legal in a nested scope
// (chapter 03 §Variables), and works because lookup scans from the innermost.
func (c *compiler) declareLocal(id *ast.Ident) int32 {
	slot := int32(len(c.locals))
	l := local{name: id.Name, slot: slot}
	if o := c.info.ObjectOf(id); o != nil {
		l.obj = o
		c.obj[o] = slot
	}
	c.locals = append(c.locals, l)
	if len(c.locals) > c.slots {
		c.slots = len(c.locals)
	}
	return slot
}

// resolveLocal finds the slot a name refers to, innermost first.
func (c *compiler) resolveLocal(id *ast.Ident) (int32, bool) {
	// The object identity is authoritative: two locals may share a name across
	// scopes, and the checker already worked out which one this use means.
	if o := c.info.ObjectOf(id); o != nil {
		if slot, ok := c.obj[o]; ok {
			return slot, true
		}
	}
	for i := len(c.locals) - 1; i >= 0; i-- {
		if c.locals[i].name == id.Name {
			return c.locals[i].slot, true
		}
	}
	return 0, false
}

// ---------------------------------------------------------------------------
// Emitting

func (c *compiler) emit(op Op, a int32, pos token.Position) int {
	return c.fn.Chunk.Emit(op, a, int32(pos.Line))
}

func (c *compiler) constant(k Const, pos token.Position) {
	c.emit(OpConst, c.fn.Chunk.AddConst(k), pos)
}

// unsupported reports a construct the compiler does not handle yet.
//
// It is a diagnostic, not a panic and not silence: a program using it exits
// non-zero saying exactly what is missing and where.
func (c *compiler) unsupported(pos token.Position, what string) {
	c.errs.AddHint(pos,
		what+" is not implemented yet",
		"the type checker accepts it; the bytecode compiler has not caught up. See PLAN.md")
}

// typeOf reads an expression's type out of the checker's side table.
func (c *compiler) typeOf(e ast.Expr) types.Type { return c.info.TypeOf(e) }
