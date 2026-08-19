import pytest

# from ymir.core.lexer import Lexer, TokenType, Token


@pytest.fixture
def ymir_source_code():
    return """
    def foo(x) {
        return x * 2;
    }

    class Bar {
        def __init__(self, y) {
            self.y = y;
        }

        def baz() {
            return self.y + 3;
        }
    }
    """
