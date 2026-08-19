from ymir.core.lexer import Lexer
from ymir.core.parser import Parser
from ymir.core.types import FloatType, MatrixType
from ymir.interpreter import YmirInterpreter


def test_matrix_type_parsing():
    code = """
    module main
    var A: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
    """
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    # Find the variable declaration
    var_decl = None
    for node in ast:
        if hasattr(node, "body"):
            for stmt in node.body:
                if hasattr(stmt, "target") and stmt.target == "A":
                    var_decl = stmt
    assert var_decl is not None
    assert isinstance(var_decl.var_type, MatrixType)
    assert isinstance(var_decl.var_type.element_type, FloatType)


def test_interpreter_matrix_operations():
    interpreter = YmirInterpreter()
    matrix1 = [[1.0, 2.0], [3.0, 4.0]]
    matrix2 = [[5.0, 6.0], [7.0, 8.0]]
    # Addition
    result = interpreter.matrix_operation(matrix1, matrix2, "+")
    assert result == [[6.0, 8.0], [10.0, 12.0]]
    # Multiplication
    result = interpreter.matrix_operation(matrix1, matrix2, "@")
    assert result == [[19.0, 22.0], [43.0, 50.0]]
    # Transpose
    transpose_func = interpreter.global_scope["transpose"]
    result = transpose_func(matrix1)
    assert result == [[1.0, 3.0], [2.0, 4.0]]
    # Determinant
    det_func = interpreter.global_scope["det"]
    det = det_func(matrix1)
    assert abs(det + 2.0) < 1e-8
    # Inverse
    inverse_func = interpreter.global_scope["inverse"]
    inv = inverse_func(matrix1)
    # Check inverse by multiplying with original (should be identity)
    prod = interpreter.matrix_operation(matrix1, inv, "@")
    assert abs(prod[0][0] - 1.0) < 1e-8
    assert abs(prod[1][1] - 1.0) < 1e-8
    # Shape
    shape_func = interpreter.global_scope["shape"]
    shape = shape_func(matrix1)
    assert shape == [2, 2]
