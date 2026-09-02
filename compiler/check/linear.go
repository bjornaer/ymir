package check

import (
	"sort"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/token"
	"github.com/bjornaer/ymir/compiler/types"
)

// Linearity, rules L1 through L6 of chapter 02.
//
// Built in Phase 2 per decision D3, months before the quantum fragment that
// supplies the only linear types. "Linear typing is not a feature that can be
// bolted onto a finished type checker — it constrains how bindings, assignment,
// calls, and scope exit are all defined."
//
// A linear value is reachable from source today even though `qubit()` is
// refused until Phase 7: a parameter may be declared `qubit`, and a struct may
// hold one. That is enough to exercise every rule here from a conformance case
// rather than only from a Go test.
//
// The state is one bit per binding — consumed, or not — carried in a map that
// branches snapshot and restore. That is the whole mechanism; there is no
// dataflow lattice, because Ymir has no goto and no fallthrough, so control flow
// is the statement tree.

// linearState is the position at which a binding was consumed. Absent means
// still live.
type linearState map[*Object]token.Position

func (c *checker) snapshotLinear() linearState {
	out := make(linearState, len(c.consumed))
	for k, v := range c.consumed {
		out[k] = v
	}
	return out
}

// restoreLinear resets the state to a snapshot.
//
// It copies rather than aliasing. Assigning the snapshot directly would let the
// next branch mutate the baseline the join is about to compare against, so every
// branch after the first would start from the previous one's effects — which
// silently defeats L4 rather than failing loudly.
func (c *checker) restoreLinear(s linearState) {
	out := make(linearState, len(s))
	for k, v := range s {
		out[k] = v
	}
	c.consumed = out
}

// isLinearBinding reports whether an object is one this analysis tracks.
func isLinearBinding(o *Object) bool {
	// A borrowed binding is not owned here: the caller still holds the
	// obligation, and rule L3 says a `mut` parameter borrows for the call's
	// duration rather than consuming.
	return o != nil && o.Kind == Var && !o.Borrowed && types.IsLinear(o.Type)
}

// consume records a use of a linear binding, reporting a second one.
//
// L1: "two uses is an error (linear value used twice)".
// L2: "Binding a linear value to a new name invalidates the old name. Reading a
// moved-from binding is a compile error. This is the no-cloning theorem,
// enforced by the type checker."
func (c *checker) consume(o *Object, pos token.Position, id *ast.Ident) {
	if !isLinearBinding(o) {
		return
	}
	if at, already := c.consumed[o]; already {
		c.hint(pos,
			"use of moved value "+id.Name,
			o.Type.String()+" is linear, so it is consumed exactly once; it was already used at "+at.String())
		return
	}
	if c.borrowDepth > 0 {
		// A `mut` parameter borrows for the duration of the call (L3), and a
		// gate borrows its qubits without consuming them (chapter 08 §Gates).
		return
	}
	c.consumed[o] = pos
}

// borrow runs f with consumption suppressed, for a `mut` argument.
func (c *checker) borrow(f func()) {
	c.borrowDepth++
	f()
	c.borrowDepth--
}

// checkScopeExit reports linear bindings that leave a scope unconsumed.
//
// L1: "Every linear binding MUST be consumed exactly once on every path from
// its introduction to the end of its scope. Zero uses is an error."
func (c *checker) checkScopeExit(s *Scope) {
	var pending []*Object
	for _, o := range s.names {
		if !isLinearBinding(o) {
			continue
		}
		if _, used := c.consumed[o]; !used {
			pending = append(pending, o)
		}
	}
	// Map iteration is unordered; sort so the diagnostics are deterministic
	// even before diag sorts them by offset.
	sort.Slice(pending, func(i, j int) bool { return pending[i].Pos.Offset < pending[j].Pos.Offset })

	for _, o := range pending {
		c.hint(o.Pos,
			o.Name+" is not consumed",
			"a "+o.Type.String()+" must be consumed exactly once: measure, reset or discard it, return it, or pass it on")
		// Mark it, so an enclosing scope does not report the same binding again.
		c.consumed[o] = o.Pos
	}
}

// joinBranches enforces L4 across the arms of an if or a match.
//
// "Every branch of an `if` or `match` MUST leave the same set of linear bindings
// live. Consuming a qubit in one arm but not another is an error."
//
// before is the state on entry; after holds one state per branch, and labels
// names them for the diagnostic.
func (c *checker) joinBranches(pos token.Position, before linearState, after []linearState, labels []string) {
	if len(after) < 2 {
		if len(after) == 1 {
			c.restoreLinear(after[0])
		}
		return
	}

	// Collect every binding some branch consumed but another did not.
	disagreed := map[*Object]bool{}
	for _, o := range trackedIn(before, after) {
		consumedIn := 0
		for _, st := range after {
			if _, ok := st[o]; ok {
				consumedIn++
			}
		}
		if consumedIn != 0 && consumedIn != len(after) {
			disagreed[o] = true
		}
	}

	var names []*Object
	for o := range disagreed {
		names = append(names, o)
	}
	sort.Slice(names, func(i, j int) bool { return names[i].Pos.Offset < names[j].Pos.Offset })

	for _, o := range names {
		var consuming, leaving []string
		for i, st := range after {
			if _, ok := st[o]; ok {
				consuming = append(consuming, labels[i])
			} else {
				leaving = append(leaving, labels[i])
			}
		}
		c.hint(pos,
			"branches disagree about "+o.Name+": consumed in "+joinNames(consuming)+
				", still live in "+joinNames(leaving),
			"every branch must leave the same linear bindings live (rule L4)")
	}

	// Merge conservatively: anything consumed on any path is treated as
	// consumed, so a disagreement produces one diagnostic rather than two.
	merged := c.snapshotLinear()
	for _, st := range after {
		for o, at := range st {
			if _, ok := merged[o]; !ok {
				merged[o] = at
			}
		}
	}
	c.restoreLinear(merged)
}

// trackedIn returns every linear binding any branch touched.
func trackedIn(before linearState, after []linearState) []*Object {
	seen := map[*Object]bool{}
	var out []*Object
	for _, st := range after {
		for o := range st {
			if _, already := before[o]; already {
				continue // consumed before the branch; not the branch's doing
			}
			if !seen[o] {
				seen[o] = true
				out = append(out, o)
			}
		}
	}
	return out
}

// checkLoopBody enforces L6.
//
// "A `while` or `for` body MUST NOT consume a linear binding declared outside
// it, since the body runs an unknown number of times."
func (c *checker) checkLoopBody(pos token.Position, before linearState) {
	var offenders []*Object
	for o, at := range c.consumed {
		if _, wasConsumed := before[o]; wasConsumed {
			continue
		}
		if !c.declaredInCurrentLoop[o] {
			offenders = append(offenders, o)
			_ = at
		}
	}
	sort.Slice(offenders, func(i, j int) bool { return offenders[i].Pos.Offset < offenders[j].Pos.Offset })

	for _, o := range offenders {
		c.hint(pos,
			o.Name+" is consumed inside a loop, but declared outside it",
			"the body runs an unknown number of times, so it would be consumed more than once (rule L6)")
		// Treat it as consumed from here, so scope exit does not report the
		// same mistake a second time as "not consumed".
		before[o] = pos
	}
}

// checkDroppedLinear reports a call whose linear result nobody binds.
//
// Rule L1 counts the value, not the name: a `qubit` returned into a statement
// context has been produced and never consumed, which is the same error as
// letting a binding fall out of scope. There is no implicit discard — chapter 08
// requires `discard` to be written.
func (c *checker) checkDroppedLinear(call *ast.CallExpr, results []types.Type) {
	for _, r := range results {
		if !types.IsLinear(r) {
			continue
		}
		c.hint(call.Pos(),
			"the "+r.String()+" returned by "+calleeName(call.Fun)+" is not consumed",
			"bind it and consume it; a linear value going out of scope is never an implicit discard")
		return
	}
}

// checkNoLinearCapture enforces L5 for closures.
//
// "A closure MUST NOT capture a linear value. A spawn'd call MUST NOT be passed
// one. Both would make single-use unverifiable."
func (c *checker) checkNoLinearCapture(scope *Scope, lit *ast.FuncLit) {
	ast.Inspect(lit.Body, func(n ast.Node) bool {
		id, ok := n.(*ast.Ident)
		if !ok {
			return true
		}
		o := c.info.Uses[id]
		if !isLinearBinding(o) {
			return true
		}
		// A binding declared inside the literal is not a capture.
		if _, inner := scope.LookupParent(o.Name); inner == nil {
			return true
		}
		if o != c.outerBinding(scope, o.Name) {
			return true
		}
		c.hint(id.Pos(),
			"a closure cannot capture "+id.Name+", which is linear",
			"single use cannot be verified across a closure's lifetime (rule L5)")
		return true
	})
}

// outerBinding resolves a name in the scope enclosing a function literal.
func (c *checker) outerBinding(scope *Scope, name string) *Object {
	o, _ := scope.LookupParent(name)
	return o
}

// checkNoLinearSpawn enforces the other half of L5.
func (c *checker) checkNoLinearSpawn(scope *Scope, call ast.Expr) {
	x, ok := call.(*ast.CallExpr)
	if !ok {
		return
	}
	for _, a := range x.Args {
		id, isIdent := a.(*ast.Ident)
		if !isIdent {
			continue
		}
		if o := c.info.Uses[id]; isLinearBinding(o) {
			c.hint(id.Pos(),
				"a spawned call cannot be passed "+id.Name+", which is linear",
				"the task outlives this scope, so single use cannot be verified (rule L5)")
		}
	}
}
