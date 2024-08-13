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
    MethodCall,
    ModuleDef,
    ReturnStatement,
    TupleLiteral,
    WhileStatement,
)
from ymir.core.lexer import Lexer  # , Token, TokenType
from ymir.core.parser import Parser
from ymir.core.types import ArrayType, BoolType, IntType, NilType, StringType


def test_parse_module_def():
    source_code = "module test\nexport x = 5\nfunc add(a: int, b: int) -> int { return a + b }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], ImportDef)
    assert ast[0].module_name == "example.ymr"


def test_parse_export_def():
    source_code = "module test\nexport x = 5"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], ModuleDef)
    assert isinstance(ast[0].body[0], ExportDef)
    assert ast[0].body[0].name == "x"
    assert isinstance(ast[0].body[0].value, Expression)


def test_parse_function_def():
    source_code = "func add(a: int, b: int) -> int { return a + b }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert len(ast) == 1, "Expected one top-level AST node"
    assert isinstance(ast[0], FunctionDef), "Expected a FunctionDef node"
    func_def = ast[0]

    assert func_def.name == "add", f"Expected function name 'add', got '{func_def.name}'"
    assert len(func_def.params) == 2, f"Expected 2 parameters, got {len(func_def.params)}"
    assert func_def.params == ["a", "b"], f"Expected parameters ['a', 'b'], got {func_def.params}"
    assert len(func_def.param_types) == 2, f"Expected 2 parameter types, got {len(func_def.param_types)}"
    assert all(isinstance(pt, IntType) for pt in func_def.param_types), "Expected all parameter types to be IntType"
    assert isinstance(func_def.return_type, IntType), f"Expected return type IntType, got {type(func_def.return_type)}"

    assert len(func_def.body) == 1, f"Expected 1 statement in function body, got {len(func_def.body)}"
    assert isinstance(func_def.body[0], ReturnStatement), "Expected a ReturnStatement in function body"

    return_stmt = func_def.body[0]
    assert isinstance(return_stmt.expression, BinaryOp), "Expected a BinaryOp in return statement"
    assert return_stmt.expression.operator == "+", f"Expected '+' operator, got '{return_stmt.expression.operator}'"
    assert (
        isinstance(return_stmt.expression.left, Expression) and return_stmt.expression.left.expression == "a"
    ), "Expected 'a' as left operand"
    assert (
        isinstance(return_stmt.expression.right, Expression) and return_stmt.expression.right.expression == "b"
    ), "Expected 'b' as right operand"


def test_parse_class_def():
    source_code = "class Calculator { func add(a: int, b: int) -> int { return a + b } }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], Assignment)
    assert ast[0].target == "x"
    assert isinstance(ast[0].value, Expression)


def test_parse_continue():
    source_code = "continue"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], Continue)


def test_parse_break():
    source_code = "break"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], Break)


def test_parse_nil():
    source_code = "nil"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], NilType)


def test_parse_async_function_def():
    source_code = "async func fetch() { await get_data() }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], ArrayLiteral)
    assert len(ast[0].elements) == 3


def test_parse_map_literal():
    source_code = "{a: 1, b: 2}"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], MapLiteral)
    assert len(ast[0].pairs) == 2


def test_parse_tuple_literal():
    source_code = "(1, 2)"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], TupleLiteral)
    assert len(ast[0].elements) == 2


def test_parse_expression():
    source_code = "a + b * c"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
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
    parser = Parser(tokens, verbosity="DEBUG")
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


def test_parse_binary_operators():
    source_code = """
    var a: int = 1
    var b: int = 2
    var c: int = a + b
    var d: int = a - b
    var e: int = a * b
    var f: int = a / b
    var g: int = a // b
    var h: int = a ** b
    var i: int = a % b
    var j: int = a == b
    var k: int = a != b
    var l: int = a += b
    var m: int = a -= b
    var n: int = a *= b
    var o: int = a /= b
    var p: int = a //= b
    var q: int = a **= b
    var r: int = a %= b
    a++
    var s: int = a
    a--
    var t: int = a
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], Assignment)
    assert ast[0].target == "a"
    assert isinstance(ast[0].var_type, IntType)
    assert isinstance(ast[0].value, Expression)
    assert ast[0].value.expression == 1

    assert isinstance(ast[1], Assignment)
    assert ast[1].target == "b"
    assert isinstance(ast[1].var_type, IntType)
    assert isinstance(ast[1].value, Expression)
    assert ast[1].value.expression == 2

    assert isinstance(ast[2], Assignment)
    assert ast[2].target == "c"
    assert isinstance(ast[2].var_type, IntType)
    assert isinstance(ast[2].value, BinaryOp)
    assert ast[2].value.operator == "+"
    assert ast[2].value.left.expression == "a"
    assert ast[2].value.right.expression == "b"

    assert isinstance(ast[3], Assignment)
    assert ast[3].target == "d"
    assert isinstance(ast[3].var_type, IntType)
    assert isinstance(ast[3].value, BinaryOp)
    assert ast[3].value.operator == "-"
    assert ast[3].value.left.expression == "a"
    assert ast[3].value.right.expression == "b"

    assert isinstance(ast[4], Assignment)
    assert ast[4].target == "e"
    assert isinstance(ast[4].var_type, IntType)
    assert isinstance(ast[4].value, BinaryOp)
    assert ast[4].value.operator == "*"
    assert ast[4].value.left.expression == "a"
    assert ast[4].value.right.expression == "b"

    assert isinstance(ast[5], Assignment)
    assert ast[5].target == "f"
    assert isinstance(ast[5].var_type, IntType)
    assert isinstance(ast[5].value, BinaryOp)
    assert ast[5].value.operator == "/"
    assert ast[5].value.left.expression == "a"
    assert ast[5].value.right.expression == "b"

    assert isinstance(ast[6], Assignment)
    assert ast[6].target == "g"
    assert isinstance(ast[6].var_type, IntType)
    assert isinstance(ast[6].value, BinaryOp)
    assert ast[6].value.operator == "//"
    assert ast[6].value.left.expression == "a"
    assert ast[6].value.right.expression == "b"

    assert isinstance(ast[7], Assignment)
    assert ast[7].target == "h"
    assert isinstance(ast[7].var_type, IntType)
    assert isinstance(ast[7].value, BinaryOp)
    assert ast[7].value.operator == "**"
    assert ast[7].value.left.expression == "a"
    assert ast[7].value.right.expression == "b"

    assert isinstance(ast[8], Assignment)
    assert ast[8].target == "i"
    assert isinstance(ast[8].var_type, IntType)
    assert isinstance(ast[8].value, BinaryOp)
    assert ast[8].value.operator == "%"
    assert ast[8].value.left.expression == "a"
    assert ast[8].value.right.expression == "b"

    assert isinstance(ast[9], Assignment)
    assert ast[9].target == "j"
    assert isinstance(ast[9].var_type, IntType)
    assert isinstance(ast[9].value, BinaryOp)
    assert ast[9].value.operator == "=="
    assert ast[9].value.left.expression == "a"
    assert ast[9].value.right.expression == "b"

    assert isinstance(ast[10], Assignment)
    assert ast[10].target == "k"
    assert isinstance(ast[10].var_type, IntType)
    assert isinstance(ast[10].value, BinaryOp)
    assert ast[10].value.operator == "!="
    assert ast[10].value.left.expression == "a"
    assert ast[10].value.right.expression == "b"

    assert isinstance(ast[11], Assignment)
    assert ast[11].target == "l"
    assert isinstance(ast[11].var_type, IntType)
    assert isinstance(ast[11].value, BinaryOp)
    assert ast[11].value.operator == "+="
    assert ast[11].value.left.expression == "a"
    assert ast[11].value.right.expression == "b"

    assert isinstance(ast[12], Assignment)
    assert ast[12].target == "m"
    assert isinstance(ast[12].var_type, IntType)
    assert isinstance(ast[12].value, BinaryOp)
    assert ast[12].value.operator == "-="
    assert ast[12].value.left.expression == "a"
    assert ast[12].value.right.expression == "b"

    assert isinstance(ast[13], Assignment)
    assert ast[13].target == "n"
    assert isinstance(ast[13].var_type, IntType)
    assert isinstance(ast[13].value, BinaryOp)
    assert ast[13].value.operator == "*="
    assert ast[13].value.left.expression == "a"
    assert ast[13].value.right.expression == "b"

    assert isinstance(ast[14], Assignment)
    assert ast[14].target == "o"
    assert isinstance(ast[14].var_type, IntType)
    assert isinstance(ast[14].value, BinaryOp)
    assert ast[14].value.operator == "/="
    assert ast[14].value.left.expression == "a"
    assert ast[14].value.right.expression == "b"

    assert isinstance(ast[15], Assignment)
    assert ast[15].target == "p"
    assert isinstance(ast[15].var_type, IntType)
    assert isinstance(ast[15].value, BinaryOp)
    assert ast[15].value.operator == "//="
    assert ast[15].value.left.expression == "a"
    assert ast[15].value.right.expression == "b"

    assert isinstance(ast[16], Assignment)
    assert ast[16].target == "q"
    assert isinstance(ast[16].var_type, IntType)
    assert isinstance(ast[16].value, BinaryOp)
    assert ast[16].value.operator == "**="
    assert ast[16].value.left.expression == "a"
    assert ast[16].value.right.expression == "b"

    assert isinstance(ast[17], Assignment)
    assert ast[17].target == "r"
    assert isinstance(ast[17].var_type, IntType)
    assert isinstance(ast[17].value, BinaryOp)
    assert ast[17].value.operator == "%="
    assert ast[17].value.left.expression == "a"
    assert ast[17].value.right.expression == "b"

    assert isinstance(ast[18], Assignment)
    assert ast[18].target == "a"
    assert ast[18].var_type is None  # ++ sets no explicit type
    assert isinstance(ast[18].value, BinaryOp)
    assert ast[18].value.operator == "+"  # ++ becomes a = a + 1
    assert ast[18].value.left.expression == "a"
    assert ast[18].value.right.expression == 1

    assert isinstance(ast[19], Assignment)
    assert ast[19].target == "s"
    assert isinstance(ast[19].var_type, IntType)
    assert ast[19].value.expression == "a"

    assert isinstance(ast[20], Assignment)
    assert ast[20].target == "a"
    assert ast[20].var_type is None  # -- sets no explicit type
    assert isinstance(ast[20].value, BinaryOp)
    assert ast[20].value.operator == "-"  # -- becomes a = a - 1
    assert ast[20].value.left.expression == "a"
    assert ast[20].value.right.expression == 1

    assert isinstance(ast[21], Assignment)
    assert ast[21].target == "t"
    assert isinstance(ast[21].var_type, IntType)
    assert ast[21].value.expression == "a"


def test_parse_nested_for_loops():
    source_code = """
    var a: int = 0
    var b: int = 0
    for (var i: int = 0; i < 5; i++) {
        for (var j: int = 0; j < 5; j++) {
            a += i
            b += j
        }
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], Assignment)
    assert ast[0].target == "a"
    assert isinstance(ast[0].var_type, IntType)
    assert isinstance(ast[0].value, Expression)
    assert ast[0].value.expression == 0

    assert isinstance(ast[1], Assignment)
    assert ast[1].target == "b"
    assert isinstance(ast[1].var_type, IntType)
    assert isinstance(ast[1].value, Expression)
    assert ast[1].value.expression == 0

    assert isinstance(ast[2], ForCStyleLoop)
    assert isinstance(ast[2].init, Assignment)
    assert ast[2].init.target == "i"
    assert isinstance(ast[2].init.var_type, IntType)
    assert isinstance(ast[2].init.value, Expression)
    assert ast[2].init.value.expression == 0

    assert isinstance(ast[2].condition, BinaryOp)
    assert ast[2].condition.operator == "<"
    assert ast[2].condition.left.expression == "i"
    assert ast[2].condition.right.expression == 5

    assert isinstance(ast[2].increment, Assignment)
    assert ast[2].increment.target == "i"
    assert isinstance(ast[2].increment.value, BinaryOp)
    assert ast[2].increment.value.operator == "+"
    assert ast[2].increment.value.left.expression == "i"
    assert ast[2].increment.value.right.expression == 1

    body = ast[2].body
    assert isinstance(body[0], ForCStyleLoop)
    assert isinstance(body[0].init, Assignment)
    assert body[0].init.target == "j"
    assert isinstance(body[0].init.var_type, IntType)
    assert isinstance(body[0].init.value, Expression)
    assert body[0].init.value.expression == 0

    assert isinstance(body[0].condition, BinaryOp)
    assert body[0].condition.operator == "<"
    assert body[0].condition.left.expression == "j"
    assert body[0].condition.right.expression == 5

    assert isinstance(body[0].increment, Assignment)
    assert body[0].increment.target == "j"
    assert isinstance(body[0].increment.value, BinaryOp)
    assert body[0].increment.value.operator == "+"
    assert body[0].increment.value.left.expression == "j"
    assert body[0].increment.value.right.expression == 1

    inner_body = body[0].body
    assert isinstance(inner_body[0], Assignment)
    assert inner_body[0].target == "a"
    assert isinstance(inner_body[0].value, BinaryOp)
    assert inner_body[0].value.operator == "+"
    assert inner_body[0].value.left.expression == "a"
    assert inner_body[0].value.right.expression == "i"

    assert isinstance(inner_body[1], Assignment)
    assert inner_body[1].target == "b"
    assert isinstance(inner_body[1].value, BinaryOp)
    assert inner_body[1].value.operator == "+"
    assert inner_body[1].value.left.expression == "b"
    assert inner_body[1].value.right.expression == "j"


def test_binary_operator_precedence():
    source_code = """
    var result: int = 2 + 3 * 4 - 6 / 2
    var complex_result: bool = 10 > 5 && 3 < 4 || 7 == 7
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    # Test arithmetic precedence
    assert isinstance(ast[0], Assignment)
    assert ast[0].target == "result"
    assert isinstance(ast[0].var_type, IntType)
    assert isinstance(ast[0].value, BinaryOp)

    # The expression should be parsed as: (2 + (3 * 4)) - (6 / 2)
    assert ast[0].value.operator == "-"
    assert isinstance(ast[0].value.left, BinaryOp)
    assert isinstance(ast[0].value.right, BinaryOp)

    addition = ast[0].value.left
    assert addition.operator == "+"
    assert isinstance(addition.left, Expression)
    assert addition.left.expression == 2
    assert isinstance(addition.right, BinaryOp)

    multiplication = addition.right
    assert multiplication.operator == "*"
    assert isinstance(multiplication.left, Expression)
    assert multiplication.left.expression == 3
    assert isinstance(multiplication.right, Expression)
    assert multiplication.right.expression == 4

    division = ast[0].value.right
    assert division.operator == "/"
    assert isinstance(division.left, Expression)
    assert division.left.expression == 6
    assert isinstance(division.right, Expression)
    assert division.right.expression == 2

    # Test logical operator precedence
    assert isinstance(ast[1], Assignment)
    assert ast[1].target == "complex_result"
    assert isinstance(ast[1].var_type, BoolType)
    assert isinstance(ast[1].value, BinaryOp)

    # The expression should be parsed as: ((10 > 5) && (3 < 4)) || (7 == 7)
    or_op = ast[1].value
    assert or_op.operator == "||"
    assert isinstance(or_op.left, BinaryOp)
    assert isinstance(or_op.right, BinaryOp)

    and_op = or_op.left
    assert and_op.operator == "&&"
    assert isinstance(and_op.left, BinaryOp)
    assert isinstance(and_op.right, BinaryOp)

    greater_than = and_op.left
    assert greater_than.operator == ">"
    assert isinstance(greater_than.left, Expression)
    assert greater_than.left.expression == 10
    assert isinstance(greater_than.right, Expression)
    assert greater_than.right.expression == 5

    less_than = and_op.right
    assert less_than.operator == "<"
    assert isinstance(less_than.left, Expression)
    assert less_than.left.expression == 3
    assert isinstance(less_than.right, Expression)
    assert less_than.right.expression == 4

    equals = or_op.right
    assert equals.operator == "=="
    assert isinstance(equals.left, Expression)
    assert equals.left.expression == 7
    assert isinstance(equals.right, Expression)
    assert equals.right.expression == 7


def test_multiple_op_expression():
    source_code = """
    var number: int = 10
    (number % 2) == 0
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], Assignment)
    assert ast[0].target == "number"
    assert isinstance(ast[0].var_type, IntType)
    assert isinstance(ast[0].value, Expression)
    assert ast[0].value.expression == 10

    assert isinstance(ast[1], BinaryOp)
    assert ast[1].operator == "=="
    assert isinstance(ast[1].left, BinaryOp)
    assert ast[1].left.operator == "%"
    assert isinstance(ast[1].left.left, Expression)
    assert ast[1].left.left.expression == "number"
    assert isinstance(ast[1].left.right, Expression)
    assert ast[1].left.right.expression == 2
    assert isinstance(ast[1].right, Expression)
    assert ast[1].right.expression == 0


def test_parse_for_in_loop_with_nested_if_else():
    source_code = """
    var numbers: array[int] = [1, 2, 3, 4, 5]
    var result: array[int] = []
    untyped_result = []
    for number in numbers {
        if ((number % 2) == 0) {
            result.append(number * 2)
        } else {
            result.append(number * 3)
        }
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert isinstance(ast[0], Assignment)
    assert ast[0].target == "numbers"
    assert isinstance(ast[0].var_type, ArrayType)
    assert isinstance(ast[0].value, ArrayLiteral)
    assert len(ast[0].value.elements) == 5

    assert isinstance(ast[1], Assignment)
    assert ast[1].target == "result"
    assert isinstance(ast[1].var_type, ArrayType)
    assert isinstance(ast[1].value, ArrayLiteral)
    assert len(ast[1].value.elements) == 0

    assert isinstance(ast[2], Assignment)
    assert ast[2].target == "untyped_result"
    assert ast[2].var_type is None
    assert isinstance(ast[2].value, ArrayLiteral)
    assert len(ast[2].value.elements) == 0

    assert isinstance(ast[3], ForInLoop)
    assert ast[3].var == "number"
    assert isinstance(ast[3].iterable, Expression)
    assert ast[3].iterable.expression == "numbers"

    body = ast[3].body
    assert isinstance(body[0], IfStatement)
    assert isinstance(body[0].condition, BinaryOp)

    cond = body[0].condition
    assert cond.operator == "=="
    assert isinstance(cond.left, BinaryOp)
    assert cond.left.operator == "%"
    assert isinstance(cond.left.left, Expression)
    assert cond.left.left.expression == "number"
    assert isinstance(cond.left.right, Expression)
    assert cond.left.right.expression == 2
    assert isinstance(cond.right, Expression)
    assert cond.right.expression == 0

    then_body = body[0].then_body
    assert isinstance(then_body[0], MethodCall)
    assert then_body[0].instance == "result"
    assert then_body[0].method_name == "append"
    assert isinstance(then_body[0].args[0], BinaryOp)
    assert then_body[0].args[0].operator == "*"
    assert then_body[0].args[0].left.expression == "number"
    assert then_body[0].args[0].right.expression == 2

    else_body = body[0].else_body
    assert isinstance(else_body[0], MethodCall)
    assert else_body[0].instance == "result"
    assert else_body[0].method_name == "append"
    assert isinstance(else_body[0].args[0], BinaryOp)
    assert else_body[0].args[0].operator == "*"
    assert else_body[0].args[0].left.expression == "number"
    assert else_body[0].args[0].right.expression == 3


def test_parse_complex_function_def():
    source_code = """
    func complex_function(a: int, b: str) -> str {
        var c: int = 0
        var d: int = 1
        c = c + d
        while (c < a) {
            if ((c % 2) == 0) {
                c++
            } else {
                c += 2
            }
        }
        return b + " result: " + str(c ** 2)
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert len(ast) == 1, "Expected one top-level AST node"
    assert isinstance(ast[0], FunctionDef), "Expected a FunctionDef node"
    func_def = ast[0]

    assert func_def.name == "complex_function", f"Expected function name 'complex_function', got '{func_def.name}'"
    assert len(func_def.params) == 2, f"Expected 2 parameters, got {len(func_def.params)}"
    assert func_def.params == ["a", "b"], f"Expected parameters ['a', 'b'], got {func_def.params}"
    assert len(func_def.param_types) == 2, f"Expected 2 parameter types, got {len(func_def.param_types)}"
    assert isinstance(
        func_def.param_types[0], IntType
    ), f"Expected first parameter type IntType, got {type(func_def.param_types[0])}"
    assert isinstance(
        func_def.param_types[1], StringType
    ), f"Expected second parameter type StringType, got {type(func_def.param_types[1])}"
    assert isinstance(
        func_def.return_type, StringType
    ), f"Expected return type StringType, got {type(func_def.return_type)}"

    assert len(func_def.body) > 0, "Expected non-empty function body"
    # Add more specific assertions for the complex function body if needed
    assert isinstance(func_def.body[0], Assignment)
    assert func_def.body[0].target == "c"
    assert isinstance(func_def.body[0].value, Expression)
    assert func_def.body[0].value.expression == 0

    assert isinstance(func_def.body[1], Assignment)
    assert func_def.body[1].target == "d"
    assert isinstance(func_def.body[1].value, Expression)
    assert func_def.body[1].value.expression == 1


def test_parse_module_with_dotted_name():
    source_code = """
    module stdlib.http

    func http_get(url: string) -> string {
        # Placeholder for actual HTTP GET logic
        return ""
    }

    export func http_post(url: string, data: string) -> string {
        # Placeholder for actual HTTP POST logic
        return ""
    }
    """
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens, verbosity="DEBUG")
    ast = parser.parse()

    assert len(ast) == 1, "Expected one top-level AST node"
    assert isinstance(ast[0], ModuleDef), "Expected a ModuleDef node"
    module_def = ast[0]

    assert module_def.name == "stdlib.http", f"Expected module name 'stdlib.http', got '{module_def.name}'"
    assert len(module_def.body) == 2, f"Expected 2 function definitions, got {len(module_def.body)}"
    # Check http_get function
    assert isinstance(module_def.body[0], FunctionDef), "Expected first item to be a FunctionDef"
    http_get = module_def.body[0]
    assert http_get.name == "http_get", f"Expected function name 'http_get', got '{http_get.name}'"
    # assert http_get.is_export == True, "Expected http_get to be exported"
    assert len(http_get.params) == 1, f"Expected 1 parameter, got {len(http_get.params)}"
    assert http_get.params[0] == "url", f"Expected parameter name 'url', got '{http_get.params[0]}'"
    assert isinstance(http_get.param_types[0], StringType), "Expected parameter type to be StringType"
    assert isinstance(http_get.return_type, StringType), "Expected return type to be StringType"

    # Check http_post function
    assert isinstance(module_def.body[1], ExportDef), "Expected second item to be a FunctionDef"
    http_post_export = module_def.body[1]
    assert http_post_export.name == "http_post", f"Expected function name 'http_post', got '{http_post_export.name}'"
    # assert http_post.is_export == True, "Expected http_post to be exported"
    http_post = http_post_export.value
    assert isinstance(http_post, FunctionDef), "Expected http_post to be a FunctionDef"
    assert len(http_post.params) == 2, f"Expected 2 parameters, got {len(http_post.params)}"
    assert http_post.params == ["url", "data"], f"Expected parameters ['url', 'data'], got {http_post.params}"
    assert all(
        isinstance(param_type, StringType) for param_type in http_post.param_types
    ), "Expected all parameter types to be StringType"
    assert isinstance(http_post.return_type, StringType), "Expected return type to be StringType"


# def test_parse_complex_module_function_def():
#     source_code = """
# module ComplexFunctionModule

# func complex_function(a: int, b: str) -> str {
#     var c: int = 0
#     var d: int = 1
#     c = c + d
#     while (c < a) {
#         if ((c % 2) == 0) {
#             c++
#         } else {
#             c += 2
#         }
#     } # this is an inline comment
#     return b + " result: " + str(c ** 2)
# }
# result = complex_function(5, "hello")
# print(result)
#     """
#     lexer = Lexer(source_code)
#     tokens = lexer.tokenize()
#     parser = Parser(tokens, verbosity="DEBUG")
#     ast = parser.parse()

#     assert isinstance(ast[0], ModuleDef)
#     assert ast[0].name == "ComplexFunctionModule"

#     assert isinstance(ast[0].body[0], FunctionDef)
#     func_def = ast[0].body[0]
#     assert func_def.name == "complex_function"
#     assert len(func_def.params) == 2
#     assert func_def.params[0] == "a"
#     assert isinstance(func_def.param_types[0], IntType)
#     assert func_def.params[1] == "b"
#     assert isinstance(func_def.param_types[1], StringType)
#     assert isinstance(func_def.return_type, StringType)

#     body = func_def.body
#     assert isinstance(body[0], Assignment)
#     assert body[0].target == "c"
#     assert isinstance(body[0].var_type, IntType)
#     assert isinstance(body[0].value, Expression)
#     assert body[0].value.expression == 0

#     assert isinstance(body[1], Assignment)
#     assert body[1].target == "d"
#     assert isinstance(body[1].var_type, IntType)
#     assert isinstance(body[1].value, Expression)
#     assert body[1].value.expression == 1

#     assert isinstance(body[2], Assignment)
#     assert body[2].target == "c"
#     assert isinstance(body[2].value, BinaryOp)
#     assert body[2].value.operator == "+"
#     assert body[2].value.left.expression == "c"
#     assert body[2].value.right.expression == "d"

#     assert isinstance(body[3], WhileStatement)
#     assert isinstance(body[3].condition, BinaryOp)
#     assert body[3].condition.operator == "<"
#     assert body[3].condition.left.expression == "c"
#     assert body[3].condition.right.expression == "a"

#     while_body = body[3].body
#     assert isinstance(while_body[0], IfStatement)
#     assert isinstance(while_body[0].condition, BinaryOp)
#     assert while_body[0].condition.operator == "=="
#     assert isinstance(while_body[0].condition.left, BinaryOp)
#     assert while_body[0].condition.left.operator == "%"
#     assert while_body[0].condition.left.left.expression == "c"
#     assert while_body[0].condition.left.right.expression == 2
#     assert while_body[0].condition.right.expression == 0

#     if_body = while_body[0].then_body
#     assert isinstance(if_body[0], Expression)
#     assert if_body[0].expression == "c++"

#     else_body = while_body[0].else_body
#     assert isinstance(else_body[0], Assignment)
#     assert else_body[0].target == "c"
#     assert isinstance(else_body[0].value, BinaryOp)
#     assert else_body[0].value.operator == "+="
#     assert else_body[0].value.left.expression == "c"
#     assert else_body[0].value.right.expression == 2

#     assert isinstance(body[4], ReturnStatement)
#     assert isinstance(body[4].value, BinaryOp)
#     assert body[4].value.operator == "+"
#     assert isinstance(body[4].value.left, BinaryOp)
#     assert body[4].value.left.operator == "+"
#     assert body[4].value.left.left.expression == "b"
#     assert body[4].value.left.right.expression == " result: "
#     assert isinstance(body[4].value.right, FunctionCall)
#     assert body[4].value.right.function == "str"
#     assert isinstance(body[4].value.right.args[0], BinaryOp)
#     assert body[4].value.right.args[0].operator == "**"
#     assert body[4].value.right.args[0].left.expression == "c"
#     assert body[4].value.right.args[0].right.expression == 2

#     assert isinstance(ast[0].body[1], Assignment)
#     assert ast[0].body[1].target == "result"
#     assert isinstance(ast[0].body[1].value, FunctionCall)
#     assert ast[0].body[1].value.function == "complex_function"
#     assert len(ast[0].body[1].value.args) == 2
#     assert ast[0].body[1].value.args[0].expression == 5
#     assert ast[0].body[1].value.args[1].expression == "hello"

#     assert isinstance(ast[0].body[2], FunctionCall)
#     assert ast[0].body[2].function == "print"
#     assert len(ast[0].body[2].args) == 1
#     assert ast[0].body[2].args[0].expression == "result"
