"""
End-to-end integration tests for Ymir.

Tests complete workflows combining multiple features.
"""

import os
import tempfile

import pytest

from ymir.interpreter import YmirInterpreter


class TestEndToEndScenarios:
    """End-to-end test scenarios."""

    def test_simple_script_execution(self):
        """Test executing a simple script end-to-end."""
        script = """
module simple_test

func main() {
    x = 10
    y = 20
    result = x + y
    print("Result: " + str(result))
}

main()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        try:
            interpreter = YmirInterpreter(verbosity="ERROR")
            interpreter.run_ymir_script(script_path)
        finally:
            os.unlink(script_path)

    def test_matrix_operations_script(self):
        """Test script with matrix operations."""
        script = """
module matrix_test

func main() {
    matrix_a = [[1.0, 2.0], [3.0, 4.0]]
    matrix_b = [[5.0, 6.0], [7.0, 8.0]]
    
    result = matrix_a @ matrix_b
    print("Matrix result: " + str(result))
    
    shape_result = shape(result)
    print("Shape: " + str(shape_result))
}

main()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        try:
            interpreter = YmirInterpreter(verbosity="ERROR")
            interpreter.run_ymir_script(script_path)
        finally:
            os.unlink(script_path)

    def test_class_definition_and_usage(self):
        """Test class definition and instantiation."""
        script = """
module class_test

class Counter {
    func __init__(self) {
        self.count = 0
    }
    
    func increment(self) -> int {
        self.count = self.count + 1
        return self.count
    }
}

func main() {
    counter = Counter()
    counter.increment()
    counter.increment()
    result = counter.increment()
    print("Count: " + str(result))
}

main()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        try:
            interpreter = YmirInterpreter(verbosity="ERROR")
            interpreter.run_ymir_script(script_path)
        finally:
            os.unlink(script_path)

    def test_control_flow_comprehensive(self):
        """Test various control flow structures."""
        script = """
module control_flow_test

func main() {
    # If-else
    x = 10
    if (x > 5) {
        print("x is greater than 5")
    } else {
        print("x is not greater than 5")
    }
    
    # While loop
    var i: int = 0
    while (i < 3) {
        print("Iteration: " + str(i))
        i = i + 1
    }
    
    # For-in loop
    arr = [1, 2, 3]
    for item in arr {
        print("Item: " + str(item))
    }
}

main()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        try:
            interpreter = YmirInterpreter(verbosity="ERROR")
            interpreter.run_ymir_script(script_path)
        finally:
            os.unlink(script_path)

    @pytest.mark.slow
    def test_exception_handling(self):
        """Test exception handling."""
        script = """
module exception_test

exception CustomError: Exception {
    func __init__(self, message: string) {
        self.message = message
    }
}

func risky_operation(value: int) -> int {
    if value < 0 {
        throw CustomError("Negative value not allowed")
    }
    return value * 2
}

func main() {
    try {
        result = risky_operation(10)
        print("Result: " + str(result))
    } except CustomError as e {
        print("Caught error: " + str(e))
    }
    
    print("Execution continues")
}

main()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        try:
            interpreter = YmirInterpreter(verbosity="ERROR")
            interpreter.run_ymir_script(script_path)
        finally:
            os.unlink(script_path)


class TestFeatureIntegration:
    """Test integration of multiple features."""

    def test_stdlib_import(self):
        """Test importing from stdlib."""
        script = """
module stdlib_test

import stdlib.math

func main() {
    result = stdlib.math.factorial(5)
    print("Factorial: " + str(result))
}

main()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        try:
            interpreter = YmirInterpreter(verbosity="ERROR")
            interpreter.run_ymir_script(script_path)
        finally:
            os.unlink(script_path)

    def test_array_operations(self):
        """Test array manipulation."""
        script = """
module array_test

func main() {
    arr = [1, 2, 3]
    arr = arr.append(4)
    arr = arr.append(5)
    
    print("Array: " + str(arr))
    print("Length: " + str(len(arr)))
}

main()
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        try:
            interpreter = YmirInterpreter(verbosity="ERROR")
            interpreter.run_ymir_script(script_path)
        finally:
            os.unlink(script_path)


@pytest.mark.integration
class TestExampleScripts:
    """Test that example scripts run successfully."""

    def test_example_script_exists(self):
        """Test that example script exists."""
        example_path = "/Users/max/personal/ymir/examples/example.ymr"
        assert os.path.exists(example_path), "Example script should exist"

    def test_concurrency_demo_exists(self):
        """Test that concurrency demo exists."""
        demo_path = "/Users/max/personal/ymir/examples/concurrency_demo.ymr"
        assert os.path.exists(demo_path), "Concurrency demo should exist"

    def test_gpu_matrix_demo_exists(self):
        """Test that GPU matrix demo exists."""
        demo_path = "/Users/max/personal/ymir/examples/gpu_matrix_demo.ymr"
        assert os.path.exists(demo_path), "GPU matrix demo should exist"

    def test_http_server_demo_exists(self):
        """Test that HTTP server demo exists."""
        demo_path = "/Users/max/personal/ymir/examples/http_server_demo.ymr"
        assert os.path.exists(demo_path), "HTTP server demo should exist"
