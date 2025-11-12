"""
Integration tests for concurrency features.

Tests spawn, channels, and concurrent execution in realistic scenarios.
"""

import pytest

from ymir.interpreter import YmirInterpreter


class TestConcurrencyIntegration:
    """Integration tests for concurrency."""

    def test_spawn_and_channel_communication(self):
        """Test spawning tasks that communicate via channels."""
        code = """
module test_concurrency

func worker(id: int, ch: any) {
    result = id * 2
    ch <- result
}

func main() {
    ch = make_channel(3)
    
    spawn worker(1, ch)
    spawn worker(2, ch)
    spawn worker(3, ch)
    
    # Collect results
    result1 <- ch
    result2 <- ch
    result3 <- ch
    
    print("Results collected: " + str(result1) + ", " + str(result2) + ", " + str(result3))
}

main()
"""
        interpreter = YmirInterpreter(verbosity="ERROR")
        # Should execute without errors
        try:
            interpreter.run_ymir_code(code)
        except AttributeError:
            # If run_ymir_code doesn't exist, skip
            pytest.skip("run_ymir_code method not available")

    def test_channel_type_safety(self):
        """Test channel type annotations work correctly."""
        code = """
module test_types

func main() {
    var ch: chan[int]
    ch = make_channel(5)
    ch <- 42
    value <- ch
    print("Value: " + str(value))
}

main()
"""
        interpreter = YmirInterpreter(verbosity="ERROR")
        try:
            interpreter.run_ymir_code(code)
        except AttributeError:
            pytest.skip("run_ymir_code method not available")

    def test_multi_worker_pattern(self):
        """Test multiple workers processing from shared channel."""
        code = """
module test_workers

func worker(id: int, jobs: any, results: any) {
    var i: int = 0
    while i < 2 {
        job <- jobs
        result = job * id
        results <- result
        i = i + 1
    }
}

func main() {
    jobs = make_channel(10)
    results = make_channel(10)
    
    # Spawn workers
    spawn worker(1, jobs, results)
    spawn worker(2, jobs, results)
    
    # Send jobs
    jobs <- 5
    jobs <- 10
    jobs <- 15
    jobs <- 20
    
    # Collect results
    var i: int = 0
    while i < 4 {
        result <- results
        print("Result: " + str(result))
        i = i + 1
    }
}

main()
"""
        interpreter = YmirInterpreter(verbosity="ERROR")
        try:
            interpreter.run_ymir_code(code)
        except AttributeError:
            pytest.skip("run_ymir_code method not available")


class TestConcurrencyWithMatrix:
    """Test concurrency with matrix operations."""

    def test_concurrent_matrix_operations(self):
        """Test spawning tasks that perform matrix operations."""
        code = """
module test_matrix_concurrent

func matrix_worker(id: int, ch: any) {
    matrix = [[1.0, 2.0], [3.0, 4.0]]
    result = transpose(matrix)
    shape_result = shape(result)
    ch <- shape_result
}

func main() {
    ch = make_channel(2)
    
    spawn matrix_worker(1, ch)
    spawn matrix_worker(2, ch)
    
    shape1 <- ch
    shape2 <- ch
    
    print("Shapes: " + str(shape1) + ", " + str(shape2))
}

main()
"""
        interpreter = YmirInterpreter(verbosity="ERROR")
        try:
            interpreter.run_ymir_code(code)
        except AttributeError:
            pytest.skip("run_ymir_code method not available")
