import pytest

from ymir.core.lexer import Lexer, Token, TokenType


def test_tokenize_newline():
    source_code = "first_line\nsecond_line"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.IDENTIFIER, "first_line", 1, 0),
        Token(TokenType.NEWLINE, "\n", 1, 10),
        Token(TokenType.IDENTIFIER, "second_line", 2, 0),
        Token(TokenType.EOF, "", 2, 11),
    ]
    assert tokens == expected_tokens


def test_tokenize_mixed():
    source_code = "func add(a: int, b: int) -> int { return a + b }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "func", 1, 0),
        Token(TokenType.IDENTIFIER, "add", 1, 5),
        Token(TokenType.PAREN_OPEN, "(", 1, 8),
        Token(TokenType.IDENTIFIER, "a", 1, 9),
        Token(TokenType.COLON, ":", 1, 10),
        Token(TokenType.KEYWORD, "int", 1, 12),
        Token(TokenType.COMMA, ",", 1, 15),
        Token(TokenType.IDENTIFIER, "b", 1, 17),
        Token(TokenType.COLON, ":", 1, 18),
        Token(TokenType.KEYWORD, "int", 1, 20),
        Token(TokenType.PAREN_CLOSE, ")", 1, 23),
        Token(TokenType.OPERATOR, "->", 1, 25),
        Token(TokenType.KEYWORD, "int", 1, 28),
        Token(TokenType.BRACE_OPEN, "{", 1, 32),
        Token(TokenType.KEYWORD, "return", 1, 34),
        Token(TokenType.IDENTIFIER, "a", 1, 41),
        Token(TokenType.OPERATOR, "+", 1, 43),
        Token(TokenType.IDENTIFIER, "b", 1, 45),
        Token(TokenType.BRACE_CLOSE, "}", 1, 47),
        Token(TokenType.EOF, "", 1, 48),
    ]
    assert tokens == expected_tokens


def test_tokenize_keywords():
    source_code = (
        "func class if else while return import export for in continue break error nil true false async await module"
    )
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "func", 1, 0),
        Token(TokenType.KEYWORD, "class", 1, 5),
        Token(TokenType.KEYWORD, "if", 1, 11),
        Token(TokenType.KEYWORD, "else", 1, 14),
        Token(TokenType.KEYWORD, "while", 1, 19),
        Token(TokenType.KEYWORD, "return", 1, 25),
        Token(TokenType.KEYWORD, "import", 1, 32),
        Token(TokenType.KEYWORD, "export", 1, 39),
        Token(TokenType.KEYWORD, "for", 1, 46),
        Token(TokenType.KEYWORD, "in", 1, 50),
        Token(TokenType.KEYWORD, "continue", 1, 53),
        Token(TokenType.KEYWORD, "break", 1, 62),
        Token(TokenType.KEYWORD, "error", 1, 68),
        Token(TokenType.KEYWORD, "nil", 1, 74),
        Token(TokenType.KEYWORD, "true", 1, 78),
        Token(TokenType.KEYWORD, "false", 1, 83),
        Token(TokenType.KEYWORD, "async", 1, 89),
        Token(TokenType.KEYWORD, "await", 1, 95),
        Token(TokenType.KEYWORD, "module", 1, 101),
        Token(TokenType.EOF, "", 1, 107),
    ]
    assert tokens == expected_tokens


def test_tokenize_type_hints():
    source_code = "array[str] map[str]str tuple[str, str, str]"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "array", 1, 0),
        Token(TokenType.BRACKET_OPEN, "[", 1, 5),
        Token(TokenType.KEYWORD, "str", 1, 6),
        Token(TokenType.BRACKET_CLOSE, "]", 1, 9),
        Token(TokenType.KEYWORD, "map", 1, 11),
        Token(TokenType.BRACKET_OPEN, "[", 1, 14),
        Token(TokenType.KEYWORD, "str", 1, 15),
        Token(TokenType.BRACKET_CLOSE, "]", 1, 18),
        Token(TokenType.KEYWORD, "str", 1, 19),
        Token(TokenType.KEYWORD, "tuple", 1, 23),
        Token(TokenType.BRACKET_OPEN, "[", 1, 28),
        Token(TokenType.KEYWORD, "str", 1, 29),
        Token(TokenType.COMMA, ",", 1, 32),
        Token(TokenType.KEYWORD, "str", 1, 34),
        Token(TokenType.COMMA, ",", 1, 37),
        Token(TokenType.KEYWORD, "str", 1, 39),
        Token(TokenType.BRACKET_CLOSE, "]", 1, 42),
        Token(TokenType.EOF, "", 1, 43),
    ]
    assert tokens == expected_tokens


def test_tokenize_type_combinations():
    source_code = "array[float] map[int]bool tuple[str, int, bool, float]"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "array", 1, 0),
        Token(TokenType.BRACKET_OPEN, "[", 1, 5),
        Token(TokenType.KEYWORD, "float", 1, 6),
        Token(TokenType.BRACKET_CLOSE, "]", 1, 11),
        Token(TokenType.KEYWORD, "map", 1, 13),
        Token(TokenType.BRACKET_OPEN, "[", 1, 16),
        Token(TokenType.KEYWORD, "int", 1, 17),
        Token(TokenType.BRACKET_CLOSE, "]", 1, 20),
        Token(TokenType.KEYWORD, "bool", 1, 21),
        Token(TokenType.KEYWORD, "tuple", 1, 26),
        Token(TokenType.BRACKET_OPEN, "[", 1, 31),
        Token(TokenType.KEYWORD, "str", 1, 32),
        Token(TokenType.COMMA, ",", 1, 35),
        Token(TokenType.KEYWORD, "int", 1, 37),
        Token(TokenType.COMMA, ",", 1, 40),
        Token(TokenType.KEYWORD, "bool", 1, 42),
        Token(TokenType.COMMA, ",", 1, 46),
        Token(TokenType.KEYWORD, "float", 1, 48),
        Token(TokenType.BRACKET_CLOSE, "]", 1, 53),
        Token(TokenType.EOF, "", 1, 54),
    ]
    assert tokens == expected_tokens


def test_tokenize_comments():
    source_code = "# This is a comment"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [Token(TokenType.COMMENT, "# This is a comment", 1, 0), Token(TokenType.EOF, "", 1, 19)]
    assert tokens == expected_tokens


def test_tokenize_identifiers():
    source_code = "var1 var2 myVar"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.IDENTIFIER, "var1", 1, 0),
        Token(TokenType.IDENTIFIER, "var2", 1, 5),
        Token(TokenType.IDENTIFIER, "myVar", 1, 10),
        Token(TokenType.EOF, "", 1, 15),
    ]
    assert tokens == expected_tokens


def test_tokenize_literals():
    source_code = '123 45.67 "string"'
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.LITERAL, 123, 1, 0),
        Token(TokenType.LITERAL, 45.67, 1, 4),
        Token(TokenType.STRING, '"string"', 1, 10),
        Token(TokenType.EOF, "", 1, 18),
    ]
    assert tokens == expected_tokens


def test_tokenize_operators():
    source_code = "+ - * / = == != > < >= <="
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.OPERATOR, "+", 1, 0),
        Token(TokenType.OPERATOR, "-", 1, 2),
        Token(TokenType.OPERATOR, "*", 1, 4),
        Token(TokenType.OPERATOR, "/", 1, 6),
        Token(TokenType.OPERATOR, "=", 1, 8),
        Token(TokenType.OPERATOR, "==", 1, 10),
        Token(TokenType.OPERATOR, "!=", 1, 13),
        Token(TokenType.OPERATOR, ">", 1, 16),
        Token(TokenType.OPERATOR, "<", 1, 18),
        Token(TokenType.OPERATOR, ">=", 1, 20),
        Token(TokenType.OPERATOR, "<=", 1, 23),
        Token(TokenType.EOF, "", 1, 25),
    ]
    assert tokens == expected_tokens


def test_tokenize_delimiters():
    source_code = "{ } [ ] ( ) : , ."
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.BRACE_OPEN, "{", 1, 0),
        Token(TokenType.BRACE_CLOSE, "}", 1, 2),
        Token(TokenType.BRACKET_OPEN, "[", 1, 4),
        Token(TokenType.BRACKET_CLOSE, "]", 1, 6),
        Token(TokenType.PAREN_OPEN, "(", 1, 8),
        Token(TokenType.PAREN_CLOSE, ")", 1, 10),
        Token(TokenType.COLON, ":", 1, 12),
        Token(TokenType.COMMA, ",", 1, 14),
        Token(TokenType.DOT, ".", 1, 16),
        Token(TokenType.EOF, "", 1, 17),
    ]
    assert tokens == expected_tokens


def test_tokenize_multiline():
    source_code = "func test() {\n    return 123\n}"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "func", 1, 0),
        Token(TokenType.IDENTIFIER, "test", 1, 5),
        Token(TokenType.PAREN_OPEN, "(", 1, 9),
        Token(TokenType.PAREN_CLOSE, ")", 1, 10),
        Token(TokenType.BRACE_OPEN, "{", 1, 12),
        Token(TokenType.NEWLINE, "\n", 1, 13),
        Token(TokenType.KEYWORD, "return", 2, 4),
        Token(TokenType.LITERAL, 123, 2, 11),
        Token(TokenType.NEWLINE, "\n", 2, 14),
        Token(TokenType.BRACE_CLOSE, "}", 3, 0),
        Token(TokenType.EOF, "", 3, 1),
    ]
    assert tokens == expected_tokens


def test_unexpected_character():
    source_code = "func test() @"
    lexer = Lexer(source_code)
    with pytest.raises(RuntimeError, match=r"Unexpected character '@' on line 1"):
        lexer.tokenize()


def test_tokenize_if_statement():
    source_code = "if (x > 0) { return x }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "if", 1, 0),
        Token(TokenType.PAREN_OPEN, "(", 1, 3),
        Token(TokenType.IDENTIFIER, "x", 1, 4),
        Token(TokenType.OPERATOR, ">", 1, 6),
        Token(TokenType.LITERAL, 0, 1, 8),
        Token(TokenType.PAREN_CLOSE, ")", 1, 9),
        Token(TokenType.BRACE_OPEN, "{", 1, 11),
        Token(TokenType.KEYWORD, "return", 1, 13),
        Token(TokenType.IDENTIFIER, "x", 1, 20),
        Token(TokenType.BRACE_CLOSE, "}", 1, 22),
        Token(TokenType.EOF, "", 1, 23),
    ]
    assert tokens == expected_tokens


def test_tokenize_while_statement():
    source_code = "while (x < 10) { x = x + 1 }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "while", 1, 0),
        Token(TokenType.PAREN_OPEN, "(", 1, 6),
        Token(TokenType.IDENTIFIER, "x", 1, 7),
        Token(TokenType.OPERATOR, "<", 1, 9),
        Token(TokenType.LITERAL, 10, 1, 11),
        Token(TokenType.PAREN_CLOSE, ")", 1, 13),
        Token(TokenType.BRACE_OPEN, "{", 1, 15),
        Token(TokenType.IDENTIFIER, "x", 1, 17),
        Token(TokenType.OPERATOR, "=", 1, 19),
        Token(TokenType.IDENTIFIER, "x", 1, 21),
        Token(TokenType.OPERATOR, "+", 1, 23),
        Token(TokenType.LITERAL, 1, 1, 25),
        Token(TokenType.BRACE_CLOSE, "}", 1, 27),
        Token(TokenType.EOF, "", 1, 28),
    ]
    assert tokens == expected_tokens


def test_tokenize_for_in_loop():
    source_code = "for x in array { x = x + 1 }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "for", 1, 0),
        Token(TokenType.IDENTIFIER, "x", 1, 4),
        Token(TokenType.KEYWORD, "in", 1, 6),
        Token(TokenType.KEYWORD, "array", 1, 9),
        Token(TokenType.BRACE_OPEN, "{", 1, 15),
        Token(TokenType.IDENTIFIER, "x", 1, 17),
        Token(TokenType.OPERATOR, "=", 1, 19),
        Token(TokenType.IDENTIFIER, "x", 1, 21),
        Token(TokenType.OPERATOR, "+", 1, 23),
        Token(TokenType.LITERAL, 1, 1, 25),
        Token(TokenType.BRACE_CLOSE, "}", 1, 27),
        Token(TokenType.EOF, "", 1, 28),
    ]
    assert tokens == expected_tokens


def test_tokenize_cstyle_for_loop():
    source_code = "for (i = 0; i < 10; i = i + 1) { x = x + 1 }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "for", 1, 0),
        Token(TokenType.PAREN_OPEN, "(", 1, 4),
        Token(TokenType.IDENTIFIER, "i", 1, 5),
        Token(TokenType.OPERATOR, "=", 1, 7),
        Token(TokenType.LITERAL, 0, 1, 9),
        Token(TokenType.SEMICOLON, ";", 1, 10),
        Token(TokenType.IDENTIFIER, "i", 1, 12),
        Token(TokenType.OPERATOR, "<", 1, 14),
        Token(TokenType.LITERAL, 10, 1, 16),
        Token(TokenType.SEMICOLON, ";", 1, 18),
        Token(TokenType.IDENTIFIER, "i", 1, 20),
        Token(TokenType.OPERATOR, "=", 1, 22),
        Token(TokenType.IDENTIFIER, "i", 1, 24),
        Token(TokenType.OPERATOR, "+", 1, 26),
        Token(TokenType.LITERAL, 1, 1, 28),
        Token(TokenType.PAREN_CLOSE, ")", 1, 29),
        Token(TokenType.BRACE_OPEN, "{", 1, 31),
        Token(TokenType.IDENTIFIER, "x", 1, 33),
        Token(TokenType.OPERATOR, "=", 1, 35),
        Token(TokenType.IDENTIFIER, "x", 1, 37),
        Token(TokenType.OPERATOR, "+", 1, 39),
        Token(TokenType.LITERAL, 1, 1, 41),
        Token(TokenType.BRACE_CLOSE, "}", 1, 43),
        Token(TokenType.EOF, "", 1, 44),
    ]
    assert tokens == expected_tokens


def test_tokenize_logical_operators():
    source_code = "if (x > 0 && y < 10) || (z == 5) { return true }"
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    expected_tokens = [
        Token(TokenType.KEYWORD, "if", 1, 0),
        Token(TokenType.PAREN_OPEN, "(", 1, 3),
        Token(TokenType.IDENTIFIER, "x", 1, 4),
        Token(TokenType.OPERATOR, ">", 1, 6),
        Token(TokenType.LITERAL, 0, 1, 8),
        Token(TokenType.OPERATOR, "&&", 1, 10),
        Token(TokenType.IDENTIFIER, "y", 1, 13),
        Token(TokenType.OPERATOR, "<", 1, 15),
        Token(TokenType.LITERAL, 10, 1, 17),
        Token(TokenType.PAREN_CLOSE, ")", 1, 19),
        Token(TokenType.OPERATOR, "||", 1, 21),
        Token(TokenType.PAREN_OPEN, "(", 1, 24),
        Token(TokenType.IDENTIFIER, "z", 1, 25),
        Token(TokenType.OPERATOR, "==", 1, 27),
        Token(TokenType.LITERAL, 5, 1, 30),
        Token(TokenType.PAREN_CLOSE, ")", 1, 31),
        Token(TokenType.BRACE_OPEN, "{", 1, 33),
        Token(TokenType.KEYWORD, "return", 1, 35),
        Token(TokenType.KEYWORD, "true", 1, 42),
        Token(TokenType.BRACE_CLOSE, "}", 1, 47),
        Token(TokenType.EOF, "", 1, 48),
    ]
    assert tokens == expected_tokens
