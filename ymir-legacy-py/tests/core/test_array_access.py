import os

import pytest

from ymir.interpreter import YmirInterpreter


@pytest.fixture
def interpreter():
    return YmirInterpreter()


class TestArrayAccess:
    """Tests for array index access functionality."""

    def test_basic_array_access(self, interpreter, capsys):
        """Test basic array access with single index."""
        script_code = """
        module main

        var arr: array[int] = [1, 2, 3, 4, 5]
        print(arr[0])
        print(arr[2])
        print(arr[4])
        """

        temp_script_path = "temp_array_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["1", "3", "5"]

    def test_array_access_chaining(self, interpreter, capsys):
        """Test chained array access (e.g., arr[0][1])."""
        script_code = """
        module main

        var arr: array[array[int]] = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        print(arr[0][1])
        print(arr[1][2])
        print(arr[2][0])
        """

        temp_script_path = "temp_array_chain_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["2", "6", "7"]

    def test_array_access_with_variables(self, interpreter, capsys):
        """Test array access using variables as indices."""
        script_code = """
        module main

        var arr: array[int] = [10, 20, 30, 40, 50]
        var i: int = 1
        var j: int = 3
        print(arr[i])
        print(arr[j])
        print(arr[i + 1])
        """

        temp_script_path = "temp_array_var_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["20", "40", "30"]

    def test_array_access_with_expressions(self, interpreter, capsys):
        """Test array access with complex expressions as indices."""
        script_code = """
        module main

        var arr: array[int] = [100, 200, 300, 400, 500]
        print(arr[2 * 2])
        print(arr[5 - 2])
        print(arr[8 / 2])
        """

        temp_script_path = "temp_array_expr_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["500", "400", "500"]

    def test_array_access_with_function_calls(self, interpreter, capsys):
        """Test array access using function calls as indices."""
        script_code = """
        module main

        func get_index() -> int {
            return 2
        }

        func get_offset() -> int {
            return 1
        }

        var arr: array[int] = [100, 200, 300, 400, 500]
        print(arr[get_index()])
        print(arr[get_index() + get_offset()])
        """

        temp_script_path = "temp_array_func_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["300", "400"]

    def test_array_access_with_string_arrays(self, interpreter, capsys):
        """Test array access with string arrays."""
        script_code = """
        module main

        var arr: array[string] = ["hello", "world", "ymir", "programming"]
        print(arr[0])
        print(arr[2])
        print(arr[1] + " " + arr[3])
        """

        temp_script_path = "temp_array_string_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["hello", "ymir", "world programming"]

    def test_array_access_with_float_arrays(self, interpreter, capsys):
        """Test array access with float arrays."""
        script_code = """
        module main

        var arr: array[float] = [1.5, 2.7, 3.14, 4.2, 5.0]
        print(arr[0])
        print(arr[2])
        print(arr[1] + arr[3])
        """

        temp_script_path = "temp_array_float_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["1.5", "3.14", "6.9"]

    def test_array_access_in_loops(self, interpreter, capsys):
        """Test array access within loops."""
        script_code = """
        module main

        var arr: array[int] = [10, 20, 30, 40, 50]
        var i: int = 0
        while (i < 5) {
            print(arr[i])
            i = i + 1
        }
        """

        temp_script_path = "temp_array_loop_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["10", "20", "30", "40", "50"]

    def test_array_access_with_stdlib_math(self, interpreter, capsys):
        """Test array access combined with stdlib math functions."""
        script_code = """
        module main

        import stdlib.math

        var arr: array[float] = [1.5, 2.7, 3.14, 4.2, 5.0]
        print(abs(arr[0]))
        print(floor(arr[2]))
        print(ceil(arr[1]))
        """

        temp_script_path = "temp_array_math_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        # Filter out debug lines and get actual output
        output_lines = [line.strip() for line in captured.out.strip().split("\n") if line.strip()]
        # Remove debug lines that start with [DEBUG] or contain DEBUG:
        output = [line for line in output_lines if not (line.startswith("[DEBUG]") or "DEBUG:" in line)]
        assert output == ["1.5", "3", "3"]
