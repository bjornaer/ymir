import re
from enum import Enum, auto
from typing import List


class TokenType(Enum):
    KEYWORD = auto()
    IDENTIFIER = auto()
    LITERAL = auto()
    OPERATOR = auto()
    DELIMITER = auto()
    COMMENT = auto()
    STRING = auto()
    NEWLINE = auto()
    EOF = auto()
    BRACE_OPEN = auto()
    BRACE_CLOSE = auto()
    BRACKET_OPEN = auto()
    BRACKET_CLOSE = auto()
    PAREN_OPEN = auto()
    PAREN_CLOSE = auto()
    COLON = auto()
    COMMA = auto()
    SEMICOLON = auto()
    DOT = auto()


class Token:
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {self.value}, Line: {self.line}, Column: {self.column})"

    def __eq__(self, other):
        if isinstance(other, Token):
            return (self.type, self.value, self.line, self.column) == (
                other.type,
                other.value,
                other.line,
                other.column,
            )
        return False


class Lexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.tokens: List[Token] = []
        self.keywords = {
            "func",
            "class",
            "if",
            "else",
            "while",
            "return",
            "import",
            "export",
            "for",
            "in",
            "continue",
            "break",
            "error",
            "nil",
            "true",
            "false",
            "async",
            "await",
            "module",
            "int",  # Type hint keywords
            "float",  # Type hint keywords
            "str",  # Type hint keywords
            "bool",  # Type hint keywords
            "array",  # Type hint keywords
            "map",  # Type hint keywords
            "tuple",  # Type hint keywords
            "var",
        }
        self.token_specification = [
            ("NUMBER", r"\d+(\.\d*)?"),
            ("ID", r"[A-Za-z_]\w*"),
            ("STRING", r"\".*?\""),
            ("OP", r"(\+\+|\+=|[+\-*/%=<>!]+)"),  # Updated to include ++ and +=
            ("DOT", r"\."),  # Added to handle dot operator
            ("BRACE_OPEN", r"\{"),
            ("BRACE_CLOSE", r"\}"),
            ("BRACKET_OPEN", r"\["),
            ("BRACKET_CLOSE", r"\]"),
            ("PAREN_OPEN", r"\("),
            ("PAREN_CLOSE", r"\)"),
            ("COLON", r":"),
            ("COMMA", r","),
            ("SEMICOLON", r";"),
            ("NEWLINE", r"\n"),
            ("SKIP", r"[ \t]+"),
            ("COMMENT", r"#.*"),
            ("MISMATCH", r"."),
        ]
        self.tok_regex = "|".join(f"(?P<{pair[0]}>{pair[1]})" for pair in self.token_specification)

    def tokenize(self) -> List[Token]:
        get_token = re.compile(self.tok_regex).match
        line_number = 1
        line_start = 0
        pos = 0
        while pos < len(self.source_code):
            match = get_token(self.source_code, pos)
            if not match:
                raise RuntimeError(f"Unexpected character at line {line_number}, column {pos - line_start}")
            type = match.lastgroup
            value = match.group(type)
            column = match.start() - line_start
            # print(f"Matched {type} with value {value} at line {line_number}, column {column}")  # Debug print
            if type == "NUMBER":
                value = float(value) if "." in value else int(value)
                token = Token(TokenType.LITERAL, value, line_number, column)
            elif type == "ID":
                if value in self.keywords:
                    token = Token(TokenType.KEYWORD, value, line_number, column)
                else:
                    token = Token(TokenType.IDENTIFIER, value, line_number, column)
            elif type == "STRING":
                token = Token(TokenType.STRING, value, line_number, column)
            elif type == "OP":
                token = Token(TokenType.OPERATOR, value, line_number, column)
            elif type in {
                "BRACE_OPEN",
                "BRACE_CLOSE",
                "BRACKET_OPEN",
                "BRACKET_CLOSE",
                "PAREN_OPEN",
                "PAREN_CLOSE",
                "COLON",
                "COMMA",
                "SEMICOLON",
            }:
                token = Token(getattr(TokenType, type), value, line_number, column)
            elif type == "NEWLINE":
                token = Token(TokenType.NEWLINE, value, line_number, column)
                line_start = match.end()
                line_number += 1
            elif type == "SKIP":
                pos = match.end()
                continue
            elif type == "COMMENT":
                token = Token(TokenType.COMMENT, value, line_number, column)
                pos = match.end()
                self.tokens.append(token)
                continue
            elif type == "MISMATCH":
                raise RuntimeError(f"Unexpected character {value!r} on line {line_number}, column {column}")
            pos = match.end()
            self.tokens.append(token)
        column = len(self.source_code) - line_start
        self.tokens.append(Token(TokenType.EOF, "", line_number, column))
        return self.tokens
