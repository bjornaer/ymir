package bytecode_test

import (
	"strings"
	"testing"
)

// Control flow, chapter 05. The listing is the assertion: a jump that lands in
// the wrong place is invisible in output until some branch happens to be taken.

func TestIfWithoutElseJumpsPastTheBody(t *testing.T) {
	got := listing(t, `module t

func main() {
    if true {
        print(1)
    }
    print(2)
}
`)
	if !strings.Contains(got, "JumpIfFalse") {
		t.Errorf("no JumpIfFalse in:\n%s", got)
	}
	// With no else there is nothing to skip, so no unconditional jump is
	// emitted after the body.
	if strings.Contains(got, "Jump  ") && strings.Count(got, "Jump ") > 1 {
		t.Errorf("an if with no else should emit one jump:\n%s", got)
	}
}

func TestIfElseEmitsBothJumps(t *testing.T) {
	got := listing(t, `module t

func main() {
    if true {
        print(1)
    } else {
        print(2)
    }
}
`)
	if !strings.Contains(got, "JumpIfFalse") || !strings.Contains(got, "Jump ") {
		t.Errorf("if/else needs a conditional and an unconditional jump:\n%s", got)
	}
}

func TestWhileJumpsBackward(t *testing.T) {
	got := listing(t, `module t

func main() {
    while false {
        print(1)
    }
}
`)
	// The loop's back-edge targets the condition, which is pc 0 here.
	if !strings.Contains(got, "; -> 0000") {
		t.Errorf("the while back-edge does not target the condition:\n%s", got)
	}
}

func TestShortCircuit(t *testing.T) {
	// "&& and || evaluate their right operand only if the result is not
	// already determined. This is normative, not an optimization."
	and := listing(t, "module t\n\nfunc main() {\n    print(true && false)\n}\n")
	if !strings.Contains(and, "JumpIfFalse") {
		t.Errorf("&& must skip its right operand on a false left:\n%s", and)
	}
	or := listing(t, "module t\n\nfunc main() {\n    print(true || false)\n}\n")
	if !strings.Contains(or, "JumpIfTrue") {
		t.Errorf("|| must skip its right operand on a true left:\n%s", or)
	}
}

func TestBreakAndContinuePatchToTheEnclosingLoop(t *testing.T) {
	got := listing(t, `module t

func main() {
    while true {
        if true {
            break
        }
        continue
    }
}
`)
	if strings.Contains(got, "-> -001") || strings.Contains(got, "-> -1") {
		t.Errorf("an unpatched jump survived compilation:\n%s", got)
	}
}

func TestNoJumpIsLeftUnpatched(t *testing.T) {
	// An unpatched jump carries -1 and would send the VM to a wild pc. This is
	// the invariant every control-flow form above depends on.
	for _, src := range []string{
		"module t\n\nfunc main() {\n    if true {\n        print(1)\n    }\n}\n",
		"module t\n\nfunc main() {\n    if true {\n        print(1)\n    } else {\n        print(2)\n    }\n}\n",
		"module t\n\nfunc main() {\n    while false {\n        print(1)\n    }\n}\n",
		"module t\n\nfunc main() {\n    for i := 0; i < 3; i = i + 1 {\n        print(i)\n    }\n}\n",
		"module t\n\nfunc main() {\n    while true {\n        break\n    }\n}\n",
		"module t\n\nfunc main() {\n    print(true && false)\n}\n",
		"module t\n\nfunc main() {\n    print(true || false)\n}\n",
	} {
		prog, errs := compileSrc(t, src)
		if errs != "" {
			t.Fatalf("compile reported:\n%s", errs)
		}
		for _, fn := range prog.Funcs {
			for pc, in := range fn.Chunk.Code {
				if in.Op.IsJump() && in.A < 0 {
					t.Errorf("%s pc %d: %s left unpatched\nsource:\n%s", fn.Name, pc, in.Op, src)
				}
			}
		}
	}
}

func TestModuleVarInitializersAreCompiled(t *testing.T) {
	// The bug this guards: globals silently held the zero Value, whose numeric
	// payload is 0, so `total = total + 10` produced 10 and the program looked
	// correct while the initializer had never run.
	prog, errs := compileSrc(t, `module t

var total: int = 100

func main() {
    print(total)
}
`)
	if errs != "" {
		t.Fatalf("compile reported:\n%s", errs)
	}
	if prog.Init < 0 {
		t.Fatal("a module with an initialized var has no init function")
	}
	init := prog.Funcs[prog.Init]
	if init.Name != "<init>" {
		t.Errorf("init function is named %q", init.Name)
	}
	var setsGlobal bool
	for _, in := range init.Chunk.Code {
		if in.Op.String() == "SetGlobal" {
			setsGlobal = true
		}
	}
	if !setsGlobal {
		t.Error("the init function does not store to the global")
	}

	// And a module with no initialized var has none.
	prog, _ = compileSrc(t, "module t\n\nfunc main() {\n    print(1)\n}\n")
	if prog.Init >= 0 {
		t.Error("a module with no initialized var should have no init function")
	}
}
