import os

import pytest

from ymir.interpreter import YmirInterpreter


@pytest.fixture
def interpreter():
    return YmirInterpreter()


def test_stdlib_math_functions(interpreter, capsys):
    """
    Tests the functions in the stdlib math module.
    """
    script_code = """
module main
import stdlib.math
print(stdlib.math.add(5, 3))
print(stdlib.math.subtract(5, 3))
print(stdlib.math.multiply(5, 3))
print(stdlib.math.divide(6, 3))
    """

    temp_script_path = "temp_stdlib_math_test.ymr"
    with open(temp_script_path, "w") as temp_file:
        temp_file.write(script_code)

    interpreter.run_ymir_script(temp_script_path)

    os.remove(temp_script_path)

    captured = capsys.readouterr()
    output = captured.out.strip().splitlines()

    # Filter out debug lines and get only the actual output
    actual_output = [line for line in output if not line.startswith("[DEBUG]")]

    assert "8" in actual_output[0]
    assert "2" in actual_output[1]
    assert "15" in actual_output[2]
    assert "2.0" in actual_output[3]


def test_stdlib_math_constants(interpreter, capsys):
    """
    Tests the constants in the stdlib math module.
    """
    script_code = """
module main
import stdlib.math
print(stdlib.math.PI)
print(stdlib.math.E)
    """

    temp_script_path = "temp_stdlib_math_constants_test.ymr"
    with open(temp_script_path, "w") as temp_file:
        temp_file.write(script_code)

    interpreter.run_ymir_script(temp_script_path)

    os.remove(temp_script_path)

    captured = capsys.readouterr()
    output = captured.out.strip().splitlines()

    # Filter out debug lines and get only the actual output
    actual_output = [line for line in output if not line.startswith("[DEBUG]")]

    assert "3.141592653589793" in actual_output[0]
    assert "2.718281828459045" in actual_output[1]
