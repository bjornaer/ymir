import os

import pytest

from ymir.interpreter import YmirInterpreter


@pytest.fixture
def interpreter():
    return YmirInterpreter()


class TestStdlibMath:
    def test_functions(self, interpreter, capsys):
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

    def test_constants(self, interpreter, capsys):
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


class TestTrigonometricFormulas:
    def test_formulas(self, interpreter, capsys):
        """
        Tests the trigonometric formulas in the stdlib math module.
        """
        script_code = """
module main
import stdlib.math

# Test sin_sum: sin(pi/6 + pi/3) = sin(pi/2) = 1.0
pi = stdlib.math.PI
print(stdlib.math.sin_sum(pi / 6.0, pi / 3.0))

# Test cos_sum: cos(pi/6 + pi/3) = cos(pi/2) = 0.0
print(stdlib.math.cos_sum(pi / 6.0, pi / 3.0))

# Test tan_sum: tan(pi/8 + pi/8) = tan(pi/4) = 1.0
print(stdlib.math.tan_sum(pi / 8.0, pi / 8.0))

# Test law_of_cosines: for a 3-4-5 triangle, the angle opposite the 5 side is pi/2
# c^2 = a^2 + b^2 - 2ab*cos(C) => 5^2 = 3^2 + 4^2 - 2*3*4*cos(C)
# => 25 = 9 + 16 - 24*cos(C) => 0 = -24*cos(C) => cos(C)=0 => C=pi/2
print(stdlib.math.law_of_cosines(3.0, 4.0, pi / 2.0))
        """

        temp_script_path = "temp_trig_test.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

        captured = capsys.readouterr()
        output = [line for line in captured.out.strip().splitlines() if not line.startswith("[DEBUG]")]

        assert abs(float(output[0]) - 1.0) < 1e-9
        assert abs(float(output[1]) - 0.0) < 1e-9
        assert abs(float(output[2]) - 1.0) < 1e-9
        assert abs(float(output[3]) - 5.0) < 1e-9
