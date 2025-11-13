"""LLVM execution smoke tests.

Tests basic LLVM compilation and execution for core language features.
"""

from ymir.interpreter import YmirInterpreter


class TestLLVMExecution:
    """Basic LLVM execution tests."""

    def test_simple_print(self, tmp_path):
        """Test basic LLVM execution with print."""
        code = """module test

func main() {
    print("Hello")
}

main()
"""
        script = tmp_path / "test.ymr"
        script.write_text(code)

        interpreter = YmirInterpreter(verbosity="ERROR", load_stdlib=False)
        # Should execute via LLVM without errors
        interpreter.run_ymir_script(str(script), mode="llvm")

    def test_arithmetic(self, tmp_path):
        """Test LLVM execution with arithmetic."""
        code = """module test

func add(a: int, b: int) -> int {
    return a + b
}

func main() {
    result = add(5, 3)
    print(str(result))
}

main()
"""
        script = tmp_path / "test.ymr"
        script.write_text(code)

        interpreter = YmirInterpreter(verbosity="ERROR", load_stdlib=False)
        interpreter.run_ymir_script(str(script), mode="llvm")

    def test_variables_and_assignment(self, tmp_path):
        """Test LLVM execution with variables."""
        code = """module test

func main() {
    x = 10
    y = 20
    z = x + y
    print(str(z))
}

main()
"""
        script = tmp_path / "test.ymr"
        script.write_text(code)

        interpreter = YmirInterpreter(verbosity="ERROR", load_stdlib=False)
        interpreter.run_ymir_script(str(script), mode="llvm")

    def test_if_statement(self, tmp_path):
        """Test LLVM execution with if statement."""
        code = """module test

func main() {
    x = 5
    if x > 0 {
        print("positive")
    } else {
        print("not positive")
    }
}

main()
"""
        script = tmp_path / "test.ymr"
        script.write_text(code)

        interpreter = YmirInterpreter(verbosity="ERROR", load_stdlib=False)
        interpreter.run_ymir_script(str(script), mode="llvm")

    def test_while_loop(self, tmp_path):
        """Test LLVM execution with while loop."""
        code = """module test

func main() {
    i = 0
    while i < 3 {
        print(str(i))
        i = i + 1
    }
}

main()
"""
        script = tmp_path / "test.ymr"
        script.write_text(code)

        interpreter = YmirInterpreter(verbosity="ERROR", load_stdlib=False)
        interpreter.run_ymir_script(str(script), mode="llvm")

    def test_for_in_loop(self, tmp_path):
        """Test that for-in loops correctly raise UnsupportedFeatureError in LLVM mode."""
        code = """module test

func main() {
    arr = [1, 2, 3]
    for x in arr {
        print(str(x))
    }
}

main()
"""
        script = tmp_path / "test.ymr"
        script.write_text(code)

        interpreter = YmirInterpreter(verbosity="ERROR", load_stdlib=False)

        # Verify LLVM mode raises UnsupportedFeatureError
        import pytest

        from ymir.tools.codegen import UnsupportedFeatureError

        with pytest.raises(UnsupportedFeatureError):
            interpreter.run_ymir_script(str(script), mode="llvm")

        # Verify auto mode falls back to interpreter successfully
        interpreter.run_ymir_script(str(script), mode="auto")
