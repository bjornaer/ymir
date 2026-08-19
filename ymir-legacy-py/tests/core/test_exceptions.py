from ymir.core.lexer import Lexer
from ymir.core.parser import Parser
from ymir.core.semantic_analyzer import SemanticAnalyzer
from ymir.core.type_checker import TypeChecker
from ymir.interpreter import YmirInterpreter


class TestExceptionHandling:
    def test_simple_try_except(self):
        """Test a simple try/except block."""
        source = """
        func test() {
            var result: string = ""
            try {
                result = "try"
                throw "Error occurred"
            } except {
                result = result + " caught"
                return result
            }
            return "not reached"
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        # Semantic analysis should not raise errors
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        # Type checking should pass
        checker = TypeChecker()
        checker.check(ast)

        # Execute the code
        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        # Call the test function
        result = interpreter.evaluate_function_call("test", [])
        assert result == "try caught"

    def test_exception_binding(self):
        """Test exception binding with 'as' keyword."""
        source = """
        func test() {
            try {
                throw "Error message"
            } except as e {
                return e
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "Error message"

    def test_exception_type_matching(self):
        """Test exception type matching in except clauses."""
        source = """
        exception MyError {}

        func test() {
            try {
                throw MyError("Custom error")
            } except MyError as e {
                return "Caught MyError: " + e.message
            } except {
                return "Caught other exception"
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "Caught MyError: Custom error"

    def test_finally_block(self):
        """Test finally block execution."""
        source = """
        func test() {
            var result: string = ""
            try {
                result = result + "try"
                throw "Error"
            } except {
                result = result + "-except"
            } finally {
                result = result + "-finally"
            }
            return result
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "try-except-finally"

    def test_finally_with_no_exception(self):
        """Test finally block execution when no exception occurs."""
        source = """
        func test() {
            var result: string = ""
            try {
                result = result + "try"
            } finally {
                result = result + "-finally"
            }
            return result
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "try-finally"

    def test_nested_try_except(self):
        """Test nested try/except blocks."""
        source = """
        func test() {
            try {
                try {
                    throw "Inner exception"
                } except {
                    throw "Outer exception"
                }
            } except {
                return "Caught outer exception"
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "Caught outer exception"

    def test_exception_inheritance(self):
        """Test exception inheritance."""
        source = """
        exception BaseError {}
        exception ChildError: BaseError {}

        func test() {
            try {
                throw ChildError("Child error message")
            } except BaseError as e {
                return "Caught base error: " + e.message
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "Caught base error: Child error message"

    def test_reraising_exceptions(self):
        """Test re-raising exceptions."""
        source = """
        func test() {
            try {
                try {
                    throw "Original error"
                } except as e {
                    throw e  # Re-raise the same exception
                }
            } except as e {
                return "Caught re-raised exception: " + e
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "Caught re-raised exception: Original error"

    def test_no_matching_except(self):
        """Test when no except clause matches the raised exception."""
        source = """
        exception MyError {}
        exception OtherError {}

        func test() {
            var result: string = "start"
            try {
                try {
                    throw MyError("Error message")
                } except OtherError {
                    result = result + "-caught other"
                } finally {
                    result = result + "-inner finally"
                }
            } except MyError {
                result = result + "-caught my"
            } finally {
                result = result + "-outer finally"
            }
            return result
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "start-inner finally-caught my-outer finally"

    def test_return_in_try_finally(self):
        """Test return statements in try and finally blocks."""
        source = """
        func test() {
            try {
                return "try return"
            } finally {
                # This should run, but not affect the return value
                var x: int = 10
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "try return"

    def test_standard_exceptions(self):
        """Test using the standard exception hierarchy."""
        source = """
        import exceptions

        func test() {
            try {
                throw ValueError("Invalid value")
            } except ValueError as e {
                return "Caught ValueError: " + e.__str__()
            } except Exception {
                return "Caught generic exception"
            }
        }
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        checker = TypeChecker()
        checker.check(ast)

        interpreter = YmirInterpreter()
        interpreter.load_standard_library()  # Make sure stdlib is loaded
        for node in ast:
            interpreter.evaluate(node)

        result = interpreter.evaluate_function_call("test", [])
        assert result == "Caught ValueError: ValueError: Invalid value"
