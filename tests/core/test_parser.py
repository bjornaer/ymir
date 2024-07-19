# import pytest

from ymir.core.ast import (  # StringLiteral,
    ArrayLiteral,
    Assignment,
    AsyncFunctionDef,
    AwaitExpression,
    BinaryOp,
    Break,
    ClassDef,
    Continue,
    ExportDef,
    Expression,
    ForCStyleLoop,
    ForInLoop,
    FunctionCall,
    FunctionDef,
    IfStatement,
    ImportDef,
    MapLiteral,
    ModuleDef,
    ReturnStatement,
    TupleLiteral,
    WhileStatement,
)
from ymir.core.lexer import Lexer  # , Token, TokenType
from ymir.core.parser import Parser
from ymir.core.types import IntType, NilType


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
    assert return_stmt.expression.left.expression == "a"
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


def test_parse_class_def():
    source_code = "class Calculator { func add(a: int, b: int) -> int { return a + b } }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], ClassDef)
    assert ast[0].name == "Calculator"
    assert len(ast[0].methods) == 1
    assert isinstance(ast[0].methods[0], FunctionDef)


def test_parse_if_statement():
    source_code = "if (a > b) { return a } else { return b }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    print(tokens)
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], IfStatement)
    assert isinstance(ast[0].condition, BinaryOp)
    assert len(ast[0].then_body) == 1
    assert len(ast[0].else_body) == 1


def test_parse_multiline_if_statement():
    source_code = """
    if (a > b) {
        return a
    } else {
        return b
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], IfStatement)
    assert isinstance(ast[0].condition, BinaryOp)
    assert len(ast[0].then_body) == 1
    assert isinstance(ast[0].then_body[0], ReturnStatement)
    assert len(ast[0].else_body) == 1
    assert isinstance(ast[0].else_body[0], ReturnStatement)


def test_parse_while_statement():
    source_code = "while (a > b) { a = a - 1 }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], WhileStatement)
    assert isinstance(ast[0].condition, BinaryOp)
    assert len(ast[0].body) == 1


def test_parse_multiline_while_statement():
    source_code = """
    while (a > b) {
        a = a - 1
        b = b + 1
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], WhileStatement)
    assert isinstance(ast[0].condition, BinaryOp)
    assert len(ast[0].body) == 2
    assert isinstance(ast[0].body[0], Assignment)
    assert isinstance(ast[0].body[1], Assignment)


def test_parse_for_in_loop():
    source_code = "for i in [1, 2, 3] { print(i) }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], ForInLoop)
    assert ast[0].var == "i"
    assert isinstance(ast[0].iterable, ArrayLiteral)
    assert len(ast[0].body) == 1


# TODO add multiline for in loop test
def test_parse_multiline_for_in_loop():
    source_code = """
    for i in [1, 2, 3] {
        print(i)
        i = i + 1
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], ForInLoop)
    assert ast[0].var == "i"
    assert isinstance(ast[0].iterable, ArrayLiteral)
    assert len(ast[0].body) == 2
    assert isinstance(ast[0].body[0], FunctionCall)
    assert isinstance(ast[0].body[1], Assignment)


def test_parse_cstyle_for_loop():
    source_code = "for (i = 0; i < 10; i = i + 1) { print(i) }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], ForCStyleLoop)
    assert isinstance(ast[0].init, Assignment)
    assert isinstance(ast[0].condition, BinaryOp)
    assert isinstance(ast[0].increment, Assignment)
    assert len(ast[0].body) == 1


def test_parse_multiline_cstyle_for_loop():
    source_code = """
    for (i = 0; i < 10; i = i + 1) {
        print(i)
        i = i + 1
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], ForCStyleLoop)
    assert isinstance(ast[0].init, Assignment)
    assert isinstance(ast[0].condition, BinaryOp)
    assert isinstance(ast[0].increment, Assignment)
    assert len(ast[0].body) == 2
    assert isinstance(ast[0].body[0], FunctionCall)
    assert isinstance(ast[0].body[1], Assignment)


def test_parse_assignment():
    source_code = "x = 5"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], Assignment)
    assert ast[0].target == "x"
    assert isinstance(ast[0].value, Expression)


def test_parse_continue():
    source_code = "continue"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], Continue)


def test_parse_break():
    source_code = "break"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], Break)


def test_parse_nil():
    source_code = "nil"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], NilType)


def test_parse_async_function_def():
    source_code = "async func fetch() { await get_data() }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], AsyncFunctionDef)
    assert ast[0].name == "fetch"
    assert isinstance(ast[0].body[0], AwaitExpression)


def test_parse_multiline_async_function_def():
    source_code = """
    async func fetch() {
        data = await get_data()
        process(data)
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], AsyncFunctionDef)
    assert ast[0].name == "fetch"
    assert len(ast[0].body) == 2
    assert isinstance(ast[0].body[0], Assignment)
    assert isinstance(ast[0].body[0].value, AwaitExpression)
    assert isinstance(ast[0].body[0].value.expression, FunctionCall)
    assert isinstance(ast[0].body[1], FunctionCall)


def test_parse_array_literal():
    source_code = "[1, 2, 3]"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], ArrayLiteral)
    assert len(ast[0].elements) == 3


def test_parse_map_literal():
    source_code = "{a: 1, b: 2}"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], MapLiteral)
    assert len(ast[0].pairs) == 2


def test_parse_tuple_literal():
    source_code = "(1, 2)"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], TupleLiteral)
    assert len(ast[0].elements) == 2


def test_parse_expression():
    source_code = "a + b * c"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], BinaryOp)
    assert ast[0].operator == "+"
    assert isinstance(ast[0].right, BinaryOp)
    assert ast[0].right.operator == "*"


def test_parse_comments():
    source_code = """
    var a: int = 1  # This is a comment
    var b: int = 2  # Another comment
    # Full line comment
    var c: int = a + b  # Inline comment
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    assert isinstance(ast[0], Assignment)
    assert ast[0].target == "a"
    assert isinstance(ast[0].value, Expression)
    assert ast[0].value.expression == 1
    assert isinstance(ast[0].var_type, IntType)

    assert isinstance(ast[1], Assignment)
    assert ast[1].target == "b"
    assert isinstance(ast[1].value, Expression)
    assert ast[1].value.expression == 2
    assert isinstance(ast[1].var_type, IntType)
    assert isinstance(ast[2], Assignment)
    assert ast[2].target == "c"
    assert isinstance(ast[2].var_type, IntType)
    assert isinstance(ast[2].value, BinaryOp)
    assert ast[2].value.operator == "+"
    assert isinstance(ast[2].value.left, Expression)
    assert ast[2].value.left.expression == "a"
    assert isinstance(ast[2].value.right, Expression)
    assert ast[2].value.right.expression == "b"


# def test_parse_binary_operators():
#     source_code = """
#     var a: int = 1
#     var b: int = 2
#     var c: int = a + b
#     var d: int = a - b
#     var e: int = a * b
#     var f: int = a / b
#     var g: int = a // b
#     var h: int = a ** b
#     var i: int = a % b
#     var j: int = a == b
#     var k: int = a != b
#     var l: int = a += b
#     var m: int = a -= b
#     var n: int = a *= b
#     var o: int = a /= b
#     var p: int = a //= b
#     var q: int = a **= b
#     var r: int = a %= b
#     var s: int = a++
#     var t: int = a--
#     """
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens)
#     ast = parser.parse()

#     assert isinstance(ast[0], Assignment)
#     assert ast[0].name == "a"
#     assert ast[0].var_type == IntType()
#     assert isinstance(ast[0].value, Expression)
#     assert ast[0].value.value == 1

#     assert isinstance(ast[1], Assignment)
#     assert ast[1].name == "b"
#     assert ast[1].var_type == IntType()
#     assert isinstance(ast[1].value, Expression)
#     assert ast[1].value.value == 2

#     assert isinstance(ast[2], Assignment)
#     assert ast[2].name == "c"
#     assert ast[2].var_type == IntType()
#     assert isinstance(ast[2].value, BinaryOp)
#     assert ast[2].value.operator == "+"
#     assert ast[2].value.left.value == "a"
#     assert ast[2].value.right.value == "b"

#     assert isinstance(ast[3], Assignment)
#     assert ast[3].name == "d"
#     assert ast[3].var_type == IntType()
#     assert isinstance(ast[3].value, BinaryOp)
#     assert ast[3].value.operator == "-"
#     assert ast[3].value.left.value == "a"
#     assert ast[3].value.right.value == "b"

#     assert isinstance(ast[4], Assignment)
#     assert ast[4].name == "e"
#     assert ast[4].var_type == IntType()
#     assert isinstance(ast[4].value, BinaryOp)
#     assert ast[4].value.operator == "*"
#     assert ast[4].value.left.value == "a"
#     assert ast[4].value.right.value == "b"

#     assert isinstance(ast[5], Assignment)
#     assert ast[5].name == "f"
#     assert ast[5].var_type == IntType()
#     assert isinstance(ast[5].value, BinaryOp)
#     assert ast[5].value.operator == "/"
#     assert ast[5].value.left.value == "a"
#     assert ast[5].value.right.value == "b"

#     assert isinstance(ast[6], Assignment)
#     assert ast[6].name == "g"
#     assert ast[6].var_type == IntType()
#     assert isinstance(ast[6].value, BinaryOp)
#     assert ast[6].value.operator == "//"
#     assert ast[6].value.left.value == "a"
#     assert ast[6].value.right.value == "b"

#     assert isinstance(ast[7], Assignment)
#     assert ast[7].name == "h"
#     assert ast[7].var_type == IntType()
#     assert isinstance(ast[7].value, BinaryOp)
#     assert ast[7].value.operator == "**"
#     assert ast[7].value.left.value == "a"
#     assert ast[7].value.right.value == "b"

#     assert isinstance(ast[8], Assignment)
#     assert ast[8].name == "i"
#     assert ast[8].var_type == IntType()
#     assert isinstance(ast[8].value, BinaryOp)
#     assert ast[8].value.operator == "%"
#     assert ast[8].value.left.value == "a"
#     assert ast[8].value.right.value == "b"

#     assert isinstance(ast[9], Assignment)
#     assert ast[9].name == "j"
#     assert ast[9].var_type == IntType()
#     assert isinstance(ast[9].value, BinaryOp)
#     assert ast[9].value.operator == "=="
#     assert ast[9].value.left.value == "a"
#     assert ast[9].value.right.value == "b"

#     assert isinstance(ast[10], Assignment)
#     assert ast[10].name == "k"
#     assert ast[10].var_type == IntType()
#     assert isinstance(ast[10].value, BinaryOp)
#     assert ast[10].value.operator == "!="
#     assert ast[10].value.left.value == "a"
#     assert ast[10].value.right.value == "b"

#     assert isinstance(ast[11], Assignment)
#     assert ast[11].name == "l"
#     assert ast[11].var_type == IntType()
#     assert isinstance(ast[11].value, BinaryOp)
#     assert ast[11].value.operator == "+="
#     assert ast[11].value.left.value == "a"
#     assert ast[11].value.right.value == "b"

#     assert isinstance(ast[12], Assignment)
#     assert ast[12].name == "m"
#     assert ast[12].var_type == IntType()
#     assert isinstance(ast[12].value, BinaryOp)
#     assert ast[12].value.operator == "-="
#     assert ast[12].value.left.value == "a"
#     assert ast[12].value.right.value == "b"

#     assert isinstance(ast[13], Assignment)
#     assert ast[13].name == "n"
#     assert ast[13].var_type == IntType()
#     assert isinstance(ast[13].value, BinaryOp)
#     assert ast[13].value.operator == "*="
#     assert ast[13].value.left.value == "a"
#     assert ast[13].value.right.value == "b"

#     assert isinstance(ast[14], Assignment)
#     assert ast[14].name == "o"
#     assert ast[14].var_type == IntType()
#     assert isinstance(ast[14].value, BinaryOp)
#     assert ast[14].value.operator == "/="
#     assert ast[14].value.left.value == "a"
#     assert ast[14].value.right.value == "b"

#     assert isinstance(ast[15], Assignment)
#     assert ast[15].name == "p"
#     assert ast[15].var_type == IntType()
#     assert isinstance(ast[15].value, BinaryOp)
#     assert ast[15].value.operator == "//="
#     assert ast[15].value.left.value == "a"
#     assert ast[15].value.right.value == "b"

#     assert isinstance(ast[16], Assignment)
#     assert ast[16].name == "q"
#     assert ast[16].var_type == IntType()
#     assert isinstance(ast[16].value, BinaryOp)
#     assert ast[16].value.operator == "**="
#     assert ast[16].value.left.value == "a"
#     assert ast[16].value.right.value == "b"

#     assert isinstance(ast[17], Assignment)
#     assert ast[17].name == "r"
#     assert ast[17].var_type == IntType()
#     assert isinstance(ast[17].value, BinaryOp)
#     assert ast[17].value.operator == "%="
#     assert ast[17].value.left.value == "a"
#     assert ast[17].value.right.value == "b"

#     assert isinstance(ast[18], Assignment)
#     assert ast[18].name == "s"
#     assert ast[18].var_type == IntType()
#     assert isinstance(ast[18].value, BinaryOp)
#     assert ast[18].value.operator == "++"
#     assert ast[18].value.left.value == "a"
#     assert ast[18].value.right.value == "1"

#     assert isinstance(ast[19], Assignment)
#     assert ast[19].name == "t"
#     assert ast[19].var_type == IntType()
#     assert isinstance(ast[19].value, BinaryOp)
#     assert ast[19].value.operator == "--"
#     assert ast[19].value.left.value == "a"
#     assert ast[19].value.right.value == "1"


# # def test_parse_complex_function_def():
# #     source_code = """
# # module ComplexFunctionModule

# # func complex_function(a: int, b: str) -> str {
# #     var c: int = 0
# #     d: int = 1
# #     c = c + d
# #     while (c < a) {
# #         if (c % 2 == 0) {
# #             c++
# #         } else {
# #             c += 2
# #         }
# #     } # this is an inline comment
# #     return b + " result: " + str(c ** 2)
# # }
# # result = complex_function(5, "hello")
# # print(result)
# #         """
# #     lexer = Lexer(source_code)
# #     tokens = lexer.tokenize()
# #     parser = Parser(tokens)
# #     ast = parser.parse()

# #     assert isinstance(ast[0], FunctionDef)
# #     assert ast[0].name == "complex_function"
# #     assert len(ast[0].params) == 2
# #     assert ast[0].params[0].name == "a"
# #     assert ast[0].params[0].type == "int"
# #     assert ast[0].params[1].name == "b"
# #     assert ast[0].params[1].type == "str"
# #     assert ast[0].return_type == "str"

# #     body = ast[0].body
# #     assert isinstance(body[0], Assignment)
# #     assert body[0].name == "c"
# #     assert body[0].type == "int"
# #     assert isinstance(body[0].value, Expression)
# #     assert body[0].value.value == 0

# #     assert isinstance(body[1], Assignment)
# #     assert body[1].name == "d"
# #     assert body[1].type == "int"
# #     assert isinstance(body[1].value, Expression)
# #     assert body[1].value.value == 1

# #     assert isinstance(body[2], Expression)
# #     assert isinstance(body[2], BinaryOp)
# #     assert body[2].operator == "+"
# #     assert body[2].left.name == "c"
# #     assert body[2].right.name == "d"

# #     assert isinstance(body[3], WhileStatement)
# #     assert isinstance(body[1].condition, BinaryOp)
# #     assert body[1].condition.operator == "<"
# #     assert body[1].condition.right.value == "a"

# #     while_body = body[1].body
# #     assert isinstance(while_body[0], IfStatement)
# #     assert isinstance(while_body[0].condition, BinaryOp)
# #     assert while_body[0].condition.operator == "%"
# #     assert while_body[0].condition.right.value == 2

# #     if_body = while_body[0].then_body
# #     assert isinstance(if_body[0], Expression)
# #     assert if_body[0].value == "c++"

# #     else_body = while_body[0].else_body
# #     assert isinstance(else_body[0], BinaryOp)
# #     assert else_body[0].operator == "+="
# #     assert else_body[0].right.value == 2

# #     assert isinstance(body[2], ReturnStatement)
# #     assert isinstance(body[2].value, BinaryOp)
# #     assert body[2].value.operator == "+"
# #     assert isinstance(body[2].value.right, BinaryOp)
# #     assert body[2].value.right.operator == "+"
# #     assert isinstance(body[2].value.right.right, FunctionCall)
# #     assert body[2].value.right.right.name == "toString"
# #     assert isinstance(body[2].value.right.right.args[0], BinaryOp)
# #     assert body[2].value.right.right.args[0].operator == "**"
# #     assert body[2].value.right.right.args[0].right.value == 2

# #     # Additional assertions for result assignment and function call
# #     assert isinstance(ast[1], Assignment)
# #     assert ast[1].name == "result"
# #     assert isinstance(ast[1].value, FunctionCall)
# #     assert ast[1].value.name == "complex_function"
# #     assert len(ast[1].value.args) == 2
# #     assert ast[1].value.args[0].value == 5
# #     assert ast[1].value.args[1].value == "hello"

# #     assert isinstance(ast[2], FunctionCall)
# #     assert ast[2].name == "print"
# #     assert len(ast[2].args) == 1
# #     assert ast[2].args[0].value == "result"
