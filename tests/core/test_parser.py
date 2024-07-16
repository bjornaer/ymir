# import pytest

from ymir.core.ast import (  # StringLiteral,
    BinaryOp,
    ExportDef,
    Expression,
    FunctionDef,
    ImportDef,
    ModuleDef,
    ReturnStatement,
)
from ymir.core.lexer import Lexer  # , Token, TokenType
from ymir.core.parser import Parser
from ymir.core.types import IntType


def test_parse_module_def():
    source_code = "module test\nexport x = 5\nfunc add(a: int, b: int) -> int { return a + b }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert len(ast) == 1
    module_def = ast[0]
    assert isinstance(module_def, ModuleDef)
    assert module_def.name == "test"
    assert len(module_def.body) == 2

    export_def = module_def.body[0]
    assert isinstance(export_def, ExportDef)
    assert export_def.name == "x"
    assert isinstance(export_def.value, Expression)
    assert export_def.value.expression == 5

    function_def = module_def.body[1]
    assert isinstance(function_def, FunctionDef)
    assert function_def.name == "add"
    assert len(function_def.params) == 2
    assert function_def.params[0] == "a"
    assert isinstance(function_def.param_types[0], IntType)
    assert function_def.params[1] == "b"
    assert isinstance(function_def.param_types[1], IntType)
    assert isinstance(function_def.return_type, IntType)
    assert len(function_def.body) == 1
    return_stmt = function_def.body[0]
    assert isinstance(return_stmt, ReturnStatement)
    assert isinstance(return_stmt.expression, BinaryOp)
    assert return_stmt.expression.operator == "+"
    assert return_stmt.expression.left == "a"
    assert return_stmt.expression.right.expression == "b"


def test_parse_import_def():
    source_code = 'import "example.ymr"'
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], ImportDef)
    assert ast[0].module_name == "example.ymr"


def test_parse_export_def():
    source_code = "module test\nexport x = 5"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], ModuleDef)
    assert isinstance(ast[0].body[0], ExportDef)
    assert ast[0].body[0].name == "x"
    assert isinstance(ast[0].body[0].value, Expression)


def test_parse_function_def():
    source_code = "func add(a: int, b: int) -> int { return a + b }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], FunctionDef)
    assert ast[0].name == "add"
    assert len(ast[0].params) == 2
    assert ast[0].return_type.__class__.__name__ == "IntType"
    assert isinstance(ast[0].body[0], ReturnStatement)


# def test_parse_class_def():
#     source_code = "class Calculator { func add(a: int, b: int) -> int { return a + b } }"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], ClassDef)
#     assert ast[0].name == "Calculator"
#     assert len(ast[0].methods) == 1
#     assert isinstance(ast[0].methods[0], FunctionDef)


# def test_parse_if_statement():
#     source_code = "if a > b { return a } else { return b }"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], IfStatement)
#     assert isinstance(ast[0].condition, BinaryOp)
#     assert len(ast[0].then_body) == 1
#     assert len(ast[0].else_body) == 1


# def test_parse_while_statement():
#     source_code = "while a > b { a = a - 1 }"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], WhileStatement)
#     assert isinstance(ast[0].condition, BinaryOp)
#     assert len(ast[0].body) == 1


# def test_parse_for_in_loop():
#     source_code = "for i in [1, 2, 3] { print(i) }"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], ForInLoop)
#     assert ast[0].var == "i"
#     assert isinstance(ast[0].iterable, ArrayLiteral)
#     assert len(ast[0].body) == 1


# def test_parse_cstyle_for_loop():
#     source_code = "for (i = 0; i < 10; i = i + 1) { print(i) }"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], ForCStyleLoop)
#     assert isinstance(ast[0].init, Assignment)
#     assert isinstance(ast[0].condition, BinaryOp)
#     assert isinstance(ast[0].increment, Assignment)
#     assert len(ast[0].body) == 1


# def test_parse_assignment():
#     source_code = "x = 5"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], Assignment)
#     assert ast[0].target == "x"
#     assert isinstance(ast[0].value, Expression)


# def test_parse_continue():
#     source_code = "continue"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], Continue)


# def test_parse_break():
#     source_code = "break"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], Break)


# def test_parse_nil():
#     source_code = "nil"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], NilType)


# def test_parse_async_function_def():
#     source_code = "async func fetch() { await get_data() }"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], AsyncFunctionDef)
#     assert ast[0].name == "fetch"
#     assert isinstance(ast[0].body[0], AwaitExpression)


# def test_parse_array_literal():
#     source_code = "[1, 2, 3]"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], ArrayLiteral)
#     assert len(ast[0].elements) == 3


# def test_parse_map_literal():
#     source_code = "{a: 1, b: 2}"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], MapLiteral)
#     assert len(ast[0].pairs) == 2


# def test_parse_tuple_literal():
#     source_code = "(1, 2)"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], TupleLiteral)
#     assert len(ast[0].elements) == 2


# def test_parse_expression():
#     source_code = "a + b * c"
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], BinaryOp)
#     assert ast[0].operator == "+"
#     assert isinstance(ast[0].right, BinaryOp)
#     assert ast[0].right.operator == "*"
