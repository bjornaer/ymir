package check

import (
	"sort"

	"github.com/bjornaer/ymir/compiler/ast"
	"github.com/bjornaer/ymir/compiler/types"
)

// `match` and exhaustiveness. Chapter 05 §match, §Patterns and §Exhaustiveness,
// and chapter 06 §Qualified patterns and §Nil narrowing.
//
// "A match that omits a variant and has no `_` arm is a compile error naming the
// missing variants. This is the enforcement mechanism referenced throughout this
// spec: adding a variant to an enum breaks every match on it, which is the
// intent."
//
// Exhaustiveness is computed over the whole scrutinee: every variant of every
// member of a union, plus the nil case when the scrutinee is an un-narrowed ?T.

// variantKey identifies one arm of the candidate set. Two enums may share a
// variant name, which is why the enum is part of the key and why a union
// requires qualified patterns.
type variantKey struct {
	enum *types.Named
	name string
}

func (c *checker) matchStmt(scope *Scope, m *ast.MatchStmt) {
	scrut := c.expr(scope, m.X)

	// A ?T scrutinee needs a nil arm; a narrowed one does not, and must not
	// have one (chapter 05 §Matching a union).
	inner := scrut
	nullable := false
	if n, ok := scrut.(*types.Nullable); ok {
		inner, nullable = n.Elem, true
	}

	members, isEnum := types.Members(inner)
	if !isEnum {
		if !types.IsInvalid(inner) {
			c.hint(m.X.Pos(),
				"match is defined on enums and unions of enums, and "+scrut.String()+" is neither",
				"an enum value is inspected only by match; other types are compared with == or if")
		}
		c.matchArmsUnchecked(scope, m)
		return
	}

	// Qualification is required when two members could share a variant name.
	requireQualified := len(members) > 1

	covered := map[variantKey]bool{}
	nilArms := 0
	wildcard := false
	unresolved := false

	// Rule L4: every arm must leave the same linear bindings live.
	beforeArms := c.snapshotLinear()
	var armStates []linearState
	var armLabels []string

	for _, arm := range m.Arms {
		c.restoreLinear(beforeArms)
		// "Bindings introduced by a pattern are scoped to that arm."
		armScope := NewScope(scope, BlockScope)
		p := arm.Pattern

		switch {
		case p.IsWildcard:
			if wildcard {
				c.errorf(p.Pos(), "duplicate _ arm")
			}
			wildcard = true

		case p.IsNil:
			if !nullable {
				c.hint(p.Pos(),
					scrut.String()+" is never nil, so this match must not have a nil arm",
					"the value was narrowed, or was never nullable; remove the arm")
			}
			nilArms++
			if nilArms > 1 {
				c.errorf(p.Pos(), "a match may have at most one nil arm")
			}

		default:
			key, v, ok := c.resolvePattern(scope, p, members, requireQualified)
			if ok {
				if covered[key] {
					c.errorf(p.Pos(), "duplicate arm for %s.%s", key.enum.Name, key.name)
				}
				covered[key] = true
				c.bindPattern(armScope, p, v)
			} else {
				// Coverage cannot be computed past a pattern that did not
				// resolve, so the exhaustiveness check is skipped rather than
				// piling a second, misleading error on top of the first.
				unresolved = true
				c.bindPattern(armScope, p, nil)
			}
		}

		c.stmt(armScope, arm.Body)
		armStates = append(armStates, c.snapshotLinear())
		armLabels = append(armLabels, armLabel(p))
	}
	c.joinBranches(m.Keyword, beforeArms, armStates, armLabels)

	// A `_` arm satisfies exhaustiveness. Chapter 05 SHOULD-avoids it on enums
	// you own, which is a lint rather than an error, and diag has no warning
	// severity yet.
	if wildcard || unresolved {
		return
	}

	var missing []string
	for _, e := range members {
		for _, v := range e.Variants {
			if !covered[variantKey{enum: e, name: v.Name}] {
				missing = append(missing, qualify(e, v.Name, requireQualified))
			}
		}
	}
	sort.Strings(missing)

	if len(missing) > 0 {
		c.hint(m.Keyword,
			"match is not exhaustive: missing "+joinNames(missing),
			"add an arm for each, or a _ arm — though a _ defeats the check that a new variant breaks this match")
	}

	if nullable && nilArms == 0 {
		c.hint(m.Keyword,
			"match on "+scrut.String()+" must include exactly one nil arm",
			"add `nil => ...`, or narrow it first with `if x != nil`")
	}
}

// resolvePattern works out which variant of which enum a pattern names.
func (c *checker) resolvePattern(scope *Scope, p *ast.Pattern, members []*types.Named, requireQualified bool) (variantKey, *types.Variant, bool) {
	if p.Variant == nil {
		return variantKey{}, nil, false
	}

	if p.Enum == nil {
		if requireQualified {
			c.hint(p.Pos(),
				"a pattern over a union must name its enum, as in "+
					ownerOf(members, p.Variant.Name)+"."+p.Variant.Name,
				"two members of a union may share a variant name")
			return variantKey{}, nil, false
		}
		e := members[0]
		v := e.LookupVariant(p.Variant.Name)
		if v == nil {
			c.errorf(p.Variant.Pos(), "enum %s has no variant %s", e.Name, p.Variant.Name)
			return variantKey{}, nil, false
		}
		return variantKey{enum: e, name: v.Name}, v, true
	}

	// Qualified. The qualifier must be one of the scrutinee's members, not just
	// any enum in scope.
	for _, e := range members {
		if e.Name != p.Enum.Name {
			continue
		}
		if o, _ := scope.LookupParent(p.Enum.Name); o != nil {
			c.info.Uses[p.Enum] = o
		}
		v := e.LookupVariant(p.Variant.Name)
		if v == nil {
			c.errorf(p.Variant.Pos(), "enum %s has no variant %s", e.Name, p.Variant.Name)
			return variantKey{}, nil, false
		}
		return variantKey{enum: e, name: v.Name}, v, true
	}

	c.hint(p.Enum.Pos(),
		p.Enum.Name+" is not part of this match's type",
		"the scrutinee is "+listMembers(members))
	return variantKey{}, nil, false
}

// bindPattern binds a pattern's names to the variant's payload types. A nil
// variant means the pattern did not resolve, so the names are bound as unknown
// rather than left undeclared — that keeps one bad pattern from producing an
// "undefined" error for every name in its arm.
func (c *checker) bindPattern(scope *Scope, p *ast.Pattern, v *types.Variant) {
	if v != nil && len(p.Binds) != len(v.Payload) {
		c.errorf(p.Pos(), "%s carries %s, but this pattern binds %d",
			p.Variant.Name, plural(len(v.Payload), "value"), len(p.Binds))
		v = nil
	}
	for i, b := range p.Binds {
		if b == nil {
			continue // `_`, which discards
		}
		var t types.Type = types.Invalid
		if v != nil {
			t = v.Payload[i]
		}
		c.declareLocal(scope, b, t)
	}
}

// matchArmsUnchecked walks the arms of a match whose scrutinee did not type, so
// their bodies are still checked.
func (c *checker) matchArmsUnchecked(scope *Scope, m *ast.MatchStmt) {
	for _, arm := range m.Arms {
		inner := NewScope(scope, BlockScope)
		c.bindPattern(inner, arm.Pattern, nil)
		c.stmt(inner, arm.Body)
	}
}

// ownerOf names the union member carrying a variant, for the qualify-it hint.
func ownerOf(members []*types.Named, variant string) string {
	for _, e := range members {
		if e.LookupVariant(variant) != nil {
			return e.Name
		}
	}
	return members[0].Name
}

// armLabel names an arm for the L4 diagnostic.
func armLabel(p *ast.Pattern) string {
	switch {
	case p.IsWildcard:
		return "the _ arm"
	case p.IsNil:
		return "the nil arm"
	case p.Variant != nil:
		return "the " + p.Variant.Name + " arm"
	}
	return "an arm"
}

func qualify(e *types.Named, variant string, always bool) string {
	if always {
		return e.Name + "." + variant
	}
	return variant
}

func listMembers(members []*types.Named) string {
	names := make([]string, len(members))
	for i, m := range members {
		names[i] = m.Name
	}
	return joinNames(names)
}
