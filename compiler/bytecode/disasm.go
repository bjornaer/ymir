package bytecode

import (
	"fmt"
	"io"
	"strings"
)

// Disassembly.
//
// Written before the compiler that produces the code, because every milestone
// after this one is debugged through it. `ymir build -S` prints exactly this.

// Disassemble writes a listing of the whole program.
func (p *Program) Disassemble(w io.Writer) error {
	var b strings.Builder

	if len(p.Globals) > 0 {
		b.WriteString("globals:\n")
		for i, g := range p.Globals {
			fmt.Fprintf(&b, "  %-4d %s\n", i, g)
		}
		b.WriteString("\n")
	}

	for i, f := range p.Funcs {
		if i > 0 {
			b.WriteString("\n")
		}
		marker := ""
		if i == p.Main {
			marker = "  ; entry point"
			if p.MainReturnsError {
				marker = "  ; entry point, returns an error"
			}
		}
		fmt.Fprintf(&b, "func %s/%d%s\n", f.Name, f.Arity, marker)
		f.Chunk.disassemble(&b, p)
	}

	_, err := io.WriteString(w, b.String())
	return err
}

// Disassemble writes a listing of one function.
func (f *Function) Disassemble(w io.Writer, p *Program) error {
	var b strings.Builder
	fmt.Fprintf(&b, "func %s/%d\n", f.Name, f.Arity)
	f.Chunk.disassemble(&b, p)
	_, err := io.WriteString(w, b.String())
	return err
}

func (c *Chunk) disassemble(b *strings.Builder, p *Program) {
	prevLine := int32(-1)
	for pc, in := range c.Code {
		// The line column is printed only when it changes, so a listing reads
		// as a sequence of source lines rather than a wall of repetition.
		line := c.LineAt(pc)
		if line != prevLine {
			fmt.Fprintf(b, "  %04d  %4d  ", pc, line)
			prevLine = line
		} else {
			fmt.Fprintf(b, "  %04d     |  ", pc)
		}

		if !in.Op.HasOperand() {
			fmt.Fprintf(b, "%s\n", in.Op)
			continue
		}
		fmt.Fprintf(b, "%-14s %-5d%s\n", in.Op, in.A, c.annotate(in, p))
	}
}

// annotate explains an operand: which constant, which global, which function.
// An index the program cannot resolve is reported as such rather than silently
// printed bare, because a dangling index is a compiler bug worth seeing.
func (c *Chunk) annotate(in Instr, p *Program) string {
	switch in.Op {
	case OpConst:
		if int(in.A) < len(c.Consts) {
			return "  ; " + c.Consts[in.A].String()
		}
		return "  ; <no such constant>"

	case OpGetGlobal, OpSetGlobal:
		if p != nil && int(in.A) < len(p.Globals) {
			return "  ; " + p.Globals[in.A]
		}
		return "  ; <no such global>"

	case OpCall:
		if p != nil && int(in.A) < len(p.Funcs) {
			f := p.Funcs[in.A]
			return fmt.Sprintf("  ; %s/%d", f.Name, f.Arity)
		}
		return "  ; <no such function>"

	case OpJump, OpJumpIfFalse:
		return fmt.Sprintf("  ; -> %04d", in.A)

	case OpPrint:
		return "  ; args"
	}
	return ""
}
