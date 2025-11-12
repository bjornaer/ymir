"""
Comprehensive tests for Ymir language syntax.

Tests all language constructs including:
- Variable declarations with type annotations
- Function definitions
- Class definitions
- Control flow
- Operators
- Module system
"""

import pytest

from ymir.core.ast import (
    Assignment,
    BinaryOp,
    ChannelSend,
    ClassDef,
    Expression,
    ForCStyleLoop,
    ForInLoop,
    FunctionCall,
    FunctionDef,
    IfStatement,
    SpawnStatement,
    WhileStatement,
)
from ymir.core.lexer import Lexer, TokenType
from ymir.core.parser import Parser
from ymir.core.types import ArrayType, ChannelType, IntType, StringType


class TestVariableDeclarations:
    """Test variable declarations and type annotations."""

    def test_simple_assignment(self):
        """Test simple variable assignment."""
        code = "x = 42"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert ast[0].target == "x"

    def test_typed_variable_declaration(self):
        """Test variable declaration with type annotation."""
        code = "var count: int = 10"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].var_type, IntType)

    def test_array_type_annotation(self):
        """Test array type annotation."""
        code = "var numbers: array[int] = [1, 2, 3]"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0].var_type, ArrayType)

    def test_channel_type_annotation(self):
        """Test channel type annotation."""
        code = "var ch: chan[int] = make_channel(10)"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0].var_type, ChannelType)


class TestFunctionDefinitions:
    """Test function definition syntax."""

    def test_simple_function(self):
        """Test simple function definition."""
        code = """
func add(a: int, b: int) -> int {
    return a + b
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], FunctionDef)
        assert ast[0].name == "add"
        assert len(ast[0].params) == 2

    def test_function_no_return_type(self):
        """Test function without return type."""
        code = """
func print_hello() {
    print("Hello")
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], FunctionDef)
        assert ast[0].return_type is None

    def test_function_with_complex_types(self):
        """Test function with complex parameter types."""
        code = """
func process(data: array[int], config: map[string]int) -> array[int] {
    return data
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        func = ast[0]
        assert isinstance(func, FunctionDef)
        assert len(func.params) == 2


class TestControlFlow:
    """Test control flow statements."""

    def test_if_statement(self):
        """Test if statement."""
        code = """
if (x > 0) {
    print("positive")
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], IfStatement)

    def test_if_else_statement(self):
        """Test if-else statement."""
        code = """
if (x > 0) {
    print("positive")
} else {
    print("non-positive")
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        if_stmt = ast[0]
        assert isinstance(if_stmt, IfStatement)
        assert if_stmt.else_body is not None

    def test_while_loop(self):
        """Test while loop."""
        code = """
while (i < 10) {
    i = i + 1
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], WhileStatement)

    def test_for_in_loop(self):
        """Test for-in loop."""
        code = """
for item in items {
    print(str(item))
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], ForInLoop)

    def test_for_cstyle_loop(self):
        """Test C-style for loop."""
        code = """
for (i = 0; i < 10; i++) {
    print(str(i))
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], ForCStyleLoop)


class TestConcurrencySyntax:
    """Test concurrency-related syntax."""

    def test_spawn_statement(self):
        """Test spawn statement parsing."""
        code = "spawn worker(1, 2)"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], SpawnStatement)
        assert isinstance(ast[0].call, FunctionCall)

    def test_channel_send(self):
        """Test channel send operation parsing."""
        code = "ch <- 42"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], ChannelSend)


class TestOperators:
    """Test operators."""

    def test_arithmetic_operators(self):
        """Test arithmetic operators."""
        operators = ["+", "-", "*", "/", "%"]
        for op in operators:
            code = f"result = a {op} b"
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()

            assert len(ast) == 1
            assignment = ast[0]
            assert isinstance(assignment.value, BinaryOp)
            assert assignment.value.operator == op

    def test_comparison_operators(self):
        """Test comparison operators."""
        operators = ["<", "<=", ">", ">=", "==", "!="]
        for op in operators:
            code = f"result = a {op} b"
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()

            assert len(ast) == 1

    def test_logical_operators(self):
        """Test logical operators."""
        operators = ["&&", "||"]
        for op in operators:
            code = f"result = a {op} b"
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()

            assert len(ast) == 1

    def test_matrix_multiplication(self):
        """Test matrix multiplication operator."""
        code = "result = matrix_a @ matrix_b"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assignment = ast[0]
        assert isinstance(assignment.value, BinaryOp)
        assert assignment.value.operator == "@"


class TestClassDefinitions:
    """Test class definition syntax."""

    def test_simple_class(self):
        """Test simple class definition."""
        code = """
class MyClass {
    func __init__(self) {
        self.value = 0
    }
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        assert isinstance(ast[0], ClassDef)
        assert ast[0].name == "MyClass"

    def test_class_with_methods(self):
        """Test class with multiple methods."""
        code = """
class Calculator {
    func __init__(self) {
        self.result = 0
    }
    
    func add(self, a: int, b: int) -> int {
        return a + b
    }
}
"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        assert len(ast) == 1
        cls = ast[0]
        assert isinstance(cls, ClassDef)
        assert len(cls.methods) >= 2


class TestLexer:
    """Test lexer functionality."""

    def test_keywords(self):
        """Test keyword recognition."""
        keywords = ["func", "class", "if", "else", "while", "return", "spawn", "chan"]
        for kw in keywords:
            code = f"{kw}"
            lexer = Lexer(code)
            tokens = lexer.tokenize()

            assert len(tokens) > 0
            assert tokens[0].type == TokenType.KEYWORD
            assert tokens[0].value == kw

    def test_channel_operator(self):
        """Test channel operator lexing."""
        code = "ch <- value"
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        # Find the <- operator
        channel_op_found = False
        for token in tokens:
            if token.type == TokenType.OPERATOR and token.value == "<-":
                channel_op_found = True
                break

        assert channel_op_found, "Channel operator '<-' not found in tokens"

    def test_numbers(self):
        """Test number lexing."""
        code = "42 3.14 1.23e-4"
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        literals = [t for t in tokens if t.type == TokenType.LITERAL]
        assert len(literals) == 3
        assert literals[0].value == 42
        assert literals[1].value == 3.14

    def test_strings(self):
        """Test string lexing."""
        code = '"hello world"'
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        strings = [t for t in tokens if t.type == TokenType.STRING]
        assert len(strings) == 1
