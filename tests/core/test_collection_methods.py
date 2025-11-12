"""
Comprehensive tests for collection (array) methods in Ymir.

Tests aggregation, functional programming, and utility methods on arrays.
"""

import pytest

from ymir.core.lexer import Lexer
from ymir.core.parser import Parser
from ymir.interpreter import YmirInterpreter


def run_code(code: str):
    """Helper to run Ymir code and return interpreter."""
    interpreter = YmirInterpreter(verbosity="ERROR")
    lexer = Lexer(code, verbosity="ERROR")
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="ERROR")
    ast = parser.parse()
    for node in ast:
        interpreter.evaluate(node)
    return interpreter


class TestAggregationMethods:
    """Test collection aggregation methods."""

    def test_sum(self):
        """Test sum() method."""
        code = """
arr = [1, 2, 3, 4, 5]
result = arr.sum()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == 15

    def test_min(self):
        """Test min() method."""
        code = """
arr = [5, 2, 8, 1, 9]
result = arr.min()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == 1

    def test_max(self):
        """Test max() method."""
        code = """
arr = [5, 2, 8, 1, 9]
result = arr.max()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == 9

    def test_avg(self):
        """Test avg() method."""
        code = """
arr = [2, 4, 6, 8]
result = arr.avg()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == 5.0

    def test_mean_alias(self):
        """Test mean() as alias for avg()."""
        code = """
arr = [2, 4, 6, 8]
result = arr.mean()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == 5.0


class TestUtilityMethods:
    """Test collection utility methods."""

    def test_sort(self):
        """Test sort() method."""
        code = """
arr = [5, 2, 8, 1, 9]
result = arr.sort()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [1, 2, 5, 8, 9]

    def test_sortDesc(self):
        """Test sortDesc() method."""
        code = """
arr = [5, 2, 8, 1, 9]
result = arr.sortDesc()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [9, 8, 5, 2, 1]

    def test_reverse(self):
        """Test reverse() method."""
        code = """
arr = [1, 2, 3, 4, 5]
result = arr.reverse()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [5, 4, 3, 2, 1]

    def test_slice(self):
        """Test slice() method."""
        code = """
arr = [1, 2, 3, 4, 5]
result = arr.slice(1, 4)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [2, 3, 4]

    def test_indexOf(self):
        """Test indexOf() method."""
        code = """
arr = [10, 20, 30, 40]
result1 = arr.indexOf(30)
result2 = arr.indexOf(99)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] == 2
        assert interpreter.global_scope["result2"] == -1

    def test_lastIndexOf(self):
        """Test lastIndexOf() method."""
        code = """
arr = [1, 2, 3, 2, 1]
result = arr.lastIndexOf(2)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == 3

    def test_contains(self):
        """Test contains() method."""
        code = """
arr = [1, 2, 3, 4, 5]
result1 = arr.contains(3)
result2 = arr.contains(99)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] is True
        assert interpreter.global_scope["result2"] is False

    def test_unique(self):
        """Test unique() method."""
        code = """
arr = [1, 2, 2, 3, 1, 4, 3, 5]
result = arr.unique()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [1, 2, 3, 4, 5]

    def test_flatten(self):
        """Test flatten() method."""
        code = """
arr = [[1, 2], [3, 4], [5, 6]]
result = arr.flatten()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [1, 2, 3, 4, 5, 6]

    def test_join(self):
        """Test join() method."""
        code = """
arr = [1, 2, 3, 4, 5]
result = arr.join(", ")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "1, 2, 3, 4, 5"


class TestExistingMethods:
    """Test existing array methods."""

    def test_append(self):
        """Test append() method returns new array."""
        code = """
arr = [1, 2, 3]
result = arr.append(4)
original = arr
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [1, 2, 3, 4]
        assert interpreter.global_scope["original"] == [1, 2, 3]  # Original unchanged

    def test_extend(self):
        """Test extend() method."""
        code = """
arr1 = [1, 2, 3]
arr2 = [4, 5, 6]
result = arr1.extend(arr2)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [1, 2, 3, 4, 5, 6]


class TestArrayOperators:
    """Test array operators."""

    def test_concatenation(self):
        """Test array concatenation with +."""
        code = """
arr1 = [1, 2, 3]
arr2 = [4, 5, 6]
result = arr1 + arr2
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [1, 2, 3, 4, 5, 6]

    def test_multiple_concatenation(self):
        """Test multiple array concatenations."""
        code = """
arr1 = [1, 2]
arr2 = [3, 4]
arr3 = [5, 6]
result = arr1 + arr2 + arr3
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [1, 2, 3, 4, 5, 6]


class TestMethodChaining:
    """Test method chaining on arrays."""

    def test_chaining(self):
        """Test chaining multiple array methods."""
        code = """
arr = [5, 2, 8, 1, 9, 2, 5]
result = arr.unique().sort()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [1, 2, 5, 8, 9]

    def test_complex_chaining(self):
        """Test complex method chaining."""
        code = """
arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result = arr.slice(0, 7).reverse().slice(0, 5)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == [7, 6, 5, 4, 3]


class TestEdgeCases:
    """Test edge cases for collection methods."""

    def test_empty_array(self):
        """Test operations on empty arrays."""
        code = """
arr = []
result1 = arr.reverse()
result2 = arr.unique()
result3 = len(arr)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] == []
        assert interpreter.global_scope["result2"] == []
        assert interpreter.global_scope["result3"] == 0

    def test_single_element(self):
        """Test operations on single-element arrays."""
        code = """
arr = [42]
result1 = arr.sum()
result2 = arr.reverse()
result3 = arr.unique()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] == 42
        assert interpreter.global_scope["result2"] == [42]
        assert interpreter.global_scope["result3"] == [42]

    def test_mixed_types_join(self):
        """Test join() with mixed types."""
        code = """
arr = [1, "hello", 3.14, True]
result = arr.join("-")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "1-hello-3.14-True"


class TestImmutability:
    """Test that collection methods return new arrays."""

    def test_sort_immutable(self):
        """Test sort() doesn't modify original."""
        code = """
arr = [3, 1, 2]
sorted_arr = arr.sort()
original = arr
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["original"] == [3, 1, 2]
        assert interpreter.global_scope["sorted_arr"] == [1, 2, 3]

    def test_reverse_immutable(self):
        """Test reverse() doesn't modify original."""
        code = """
arr = [1, 2, 3]
reversed_arr = arr.reverse()
original = arr
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["original"] == [1, 2, 3]
        assert interpreter.global_scope["reversed_arr"] == [3, 2, 1]

    def test_unique_immutable(self):
        """Test unique() doesn't modify original."""
        code = """
arr = [1, 2, 2, 3, 1]
unique_arr = arr.unique()
original = arr
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["original"] == [1, 2, 2, 3, 1]
        assert interpreter.global_scope["unique_arr"] == [1, 2, 3]


class TestErrorHandling:
    """Test error handling in collection methods."""

    def test_sum_non_numeric(self):
        """Test sum() with non-numeric elements raises error."""
        code = """
arr = [1, 2, "three"]
result = arr.sum()
"""
        with pytest.raises(TypeError):
            run_code(code)

    def test_empty_min(self):
        """Test min() on empty array raises error."""
        code = """
arr = []
result = arr.min()
"""
        with pytest.raises(ValueError):
            run_code(code)

    def test_empty_max(self):
        """Test max() on empty array raises error."""
        code = """
arr = []
result = arr.max()
"""
        with pytest.raises(ValueError):
            run_code(code)
