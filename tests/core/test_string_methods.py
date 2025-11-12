"""
Comprehensive tests for string methods in Ymir.

Tests the Python-like string API including transformations, search,
manipulation, validation, and utility methods.
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


class TestStringTransformations:
    """Test string transformation methods."""

    def test_upper(self):
        """Test upper() method."""
        code = """
s = "hello world"
result = s.upper()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "HELLO WORLD"

    def test_lower(self):
        """Test lower() method."""
        code = """
s = "HELLO WORLD"
result = s.lower()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "hello world"

    def test_capitalize(self):
        """Test capitalize() method."""
        code = """
s = "hello world"
result = s.capitalize()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "Hello world"

    def test_title(self):
        """Test title() method."""
        code = """
s = "hello world"
result = s.title()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "Hello World"

    def test_strip(self):
        """Test strip() method."""
        code = """
s = "  hello world  "
result = s.strip()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "hello world"


class TestStringSearch:
    """Test string search and check methods."""

    def test_startswith(self):
        """Test startswith() method."""
        code = """
s = "hello world"
result1 = s.startswith("hello")
result2 = s.startswith("world")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] is True
        assert interpreter.global_scope["result2"] is False

    def test_endswith(self):
        """Test endswith() method."""
        code = """
s = "hello world"
result1 = s.endswith("world")
result2 = s.endswith("hello")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] is True
        assert interpreter.global_scope["result2"] is False

    def test_find(self):
        """Test find() method."""
        code = """
s = "hello world"
result1 = s.find("world")
result2 = s.find("xyz")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] == 6
        assert interpreter.global_scope["result2"] == -1

    def test_count(self):
        """Test count() method."""
        code = """
s = "hello world hello"
result = s.count("hello")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == 2

    def test_contains(self):
        """Test contains() method."""
        code = """
s = "hello world"
result1 = s.contains("world")
result2 = s.contains("xyz")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] is True
        assert interpreter.global_scope["result2"] is False


class TestStringManipulation:
    """Test string manipulation methods."""

    def test_split(self):
        """Test split() method."""
        code = """
s = "hello,world,test"
result = s.split(",")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == ["hello", "world", "test"]

    def test_split_whitespace(self):
        """Test split() with no argument (whitespace)."""
        code = """
s = "hello world  test"
result = s.split()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == ["hello", "world", "test"]

    def test_replace(self):
        """Test replace() method."""
        code = """
s = "hello world"
result = s.replace("world", "universe")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "hello universe"

    def test_join(self):
        """Test join() method."""
        code = """
sep = ", "
arr = ["hello", "world", "test"]
result = sep.join(arr)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "hello, world, test"


class TestStringValidation:
    """Test string validation methods."""

    def test_isdigit(self):
        """Test isdigit() method."""
        code = """
s1 = "12345"
s2 = "123abc"
result1 = s1.isdigit()
result2 = s2.isdigit()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] is True
        assert interpreter.global_scope["result2"] is False

    def test_isalpha(self):
        """Test isalpha() method."""
        code = """
s1 = "hello"
s2 = "hello123"
result1 = s1.isalpha()
result2 = s2.isalpha()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] is True
        assert interpreter.global_scope["result2"] is False

    def test_isalnum(self):
        """Test isalnum() method."""
        code = """
s1 = "hello123"
s2 = "hello 123"
result1 = s1.isalnum()
result2 = s2.isalnum()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] is True
        assert interpreter.global_scope["result2"] is False


class TestStringUtility:
    """Test string utility methods."""

    def test_repeat(self):
        """Test repeat() method."""
        code = """
s = "abc"
result = s.repeat(3)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "abcabcabc"

    def test_reverse(self):
        """Test reverse() method."""
        code = """
s = "hello"
result = s.reverse()
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "olleh"

    def test_slice(self):
        """Test slice() method."""
        code = """
s = "hello world"
result = s.slice(0, 5)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "hello"


class TestStringOperators:
    """Test string operators."""

    def test_concatenation(self):
        """Test string concatenation with +."""
        code = """
s1 = "hello"
s2 = " world"
result = s1 + s2
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "hello world"

    def test_string_plus_number(self):
        """Test string + number concatenation."""
        code = """
s = "Count: "
n = 42
result = s + n
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "Count: 42"

    def test_number_plus_string(self):
        """Test number + string concatenation."""
        code = """
n = 42
s = " is the answer"
result = n + s
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "42 is the answer"

    def test_string_repetition(self):
        """Test string repetition with *."""
        code = """
s = "abc"
result1 = s * 3
result2 = 2 * s
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] == "abcabcabc"
        assert interpreter.global_scope["result2"] == "abcabc"


class TestStringMethodChaining:
    """Test method chaining on strings."""

    def test_chaining(self):
        """Test chaining multiple string methods."""
        code = """
s = "  hello world  "
result = s.strip().upper().replace("WORLD", "UNIVERSE")
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result"] == "HELLO UNIVERSE"


class TestStringEdgeCases:
    """Test edge cases for string methods."""

    def test_empty_string(self):
        """Test operations on empty strings."""
        code = """
s = ""
result1 = s.upper()
result2 = s.split()
result3 = len(s)
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] == ""
        assert interpreter.global_scope["result2"] == []
        assert interpreter.global_scope["result3"] == 0

    def test_single_character(self):
        """Test operations on single character strings."""
        code = """
s = "a"
result1 = s.upper()
result2 = s * 5
"""
        interpreter = run_code(code)
        assert interpreter.global_scope["result1"] == "A"
        assert interpreter.global_scope["result2"] == "aaaaa"
