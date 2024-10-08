from typing import List, Optional, Tuple

from ymir.core.ast import (
    ArrayLiteral,
    Assignment,
    ASTNode,
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
    StringLiteral,
    TupleLiteral,
    WhileStatement,
)
from ymir.core.lexer import Token, TokenType
from ymir.core.types import (
    ArrayType,
    BoolType,
    FloatType,
    IntType,
    MapType,
    NilType,
    StringType,
    TupleType,
    Type,
)
from ymir.logging import get_logger


class Parser:
    def __init__(self, tokens, verbosity="INFO"):
        self.tokens = tokens
        self.pos = 0
        self.logger = get_logger("ymir.core", verbosity)

    def parse(self) -> List[ASTNode]:
        statements = []
        while self.current_token().type != TokenType.EOF:
            while self.current_token().type == TokenType.NEWLINE:
                self.advance()
            self.logger.debug(f"Parsing statement: {self.current_token()}")
            statements.append(self.parse_statement())

        return [s for s in statements if s is not None]

    def current_token(self) -> Token:
        if self.pos >= len(self.tokens):
            return Token(TokenType.EOF, "", line=-1, column=-1)
        return self.tokens[self.pos]

    def advance(self):
        self.logger.debug(f"Advancing from {self.current_token()}")
        self.pos += 1

    def parse_statement(self) -> ASTNode:
        # Continuously skip newlines and comments
        while self.current_token().type in {TokenType.NEWLINE, TokenType.COMMENT}:
            self.advance()
        token = self.current_token()
        if token.type == TokenType.EOF:
            return None  # Gracefully handle EOF
        if token.type == TokenType.KEYWORD:
            if token.value == "module":
                return self.parse_module_def()
            elif token.value == "import":
                return self.parse_import_def()
            elif token.value == "export":
                return self.parse_export_def()
            elif token.value == "for":
                return self.parse_for_loop()
            elif token.value == "continue":
                return self.parse_continue()
            elif token.value == "break":
                return self.parse_break()
            elif token.value == "func":
                return self.parse_function_def()
            elif token.value == "class":
                return self.parse_class_def()
            elif token.value == "if":
                return self.parse_if_statement()
            elif token.value == "while":
                return self.parse_while_statement()
            elif token.value == "nil":
                return self.parse_nil()
            elif token.value == "async":
                return self.parse_async_function_def()
            elif token.value == "await":
                return self.parse_await_expression()
            elif token.value == "return":
                return self.parse_return_statement()
            elif token.value == "var":
                return self.parse_variable_declaration()
        elif token.type == TokenType.IDENTIFIER:
            self.logger.debug(f"Parsing statement starting with identifier: {token.value}")
            return self.parse_assignment_or_expression()
        elif token.type == TokenType.BRACE_OPEN:
            if self.lookahead_is_map_literal():
                return self.parse_map_literal()
            else:
                return self.parse_block()
        elif token.type == TokenType.BRACKET_OPEN:
            return self.parse_expression()
        elif token.type == TokenType.PAREN_OPEN:
            return self.parse_expression()
        raise SyntaxError(f"Unexpected token: {token} value: '{token.value}' after identifier")

    def parse_module_def(self) -> ModuleDef:
        self.expect_token(TokenType.KEYWORD, "module")
        name_token = self.current_token()
        module_name = name_token.value
        self.expect_token(TokenType.IDENTIFIER)
        # Handle dotted module names
        self.logger.debug(f">> current token: {self.current_token()}")
        while self.current_token().type == TokenType.DOT:
            self.advance()
            if self.current_token().type != TokenType.IDENTIFIER:
                raise SyntaxError(f"Expected identifier after dot in module name, got {self.current_token()}")
            module_name += "." + self.current_token().value
            self.logger.debug(f">> module_name: {module_name}")
            self.expect_token(TokenType.IDENTIFIER)

        self.expect_token(TokenType.NEWLINE)
        body = []
        while self.current_token().type != TokenType.EOF:
            if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "module":
                break
            self.logger.debug(f"Parsing module statement: {self.current_token()}")
            try:
                statement = self.parse_statement()
                if statement is not None:
                    body.append(statement)
                    self.logger.debug(f"Successfully parsed statement: {type(statement).__name__}")
            except SyntaxError as e:
                self.logger.error(f"Error parsing statement: {e}")
                # Attempt to recover by skipping to the next newline
                while self.current_token().type not in {TokenType.NEWLINE, TokenType.EOF}:
                    self.advance()
                if self.current_token().type == TokenType.NEWLINE:
                    self.advance()
        return ModuleDef(module_name, body)

    def parse_import_def(self) -> ImportDef:
        self.advance()  # Skip 'import'
        module_name = self.current_token().value.strip('"')
        self.expect_token(TokenType.STRING)
        return ImportDef(module_name)

    def parse_export_def(self) -> ExportDef:
        self.advance()  # Skip 'export'
        if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "func":
            function_def = self.parse_function_def()
            function_def.is_export = True
            return ExportDef(function_def.name, function_def)
        else:
            name_token = self.current_token()
            self.expect_token(TokenType.IDENTIFIER)
            self.expect_token(TokenType.OPERATOR, "=")
            value = self.parse_expression()
            self.expect_token(TokenType.NEWLINE)
            return ExportDef(name_token.value, value)

    def parse_for_loop(self) -> ASTNode:
        self.advance()  # Skip 'for'
        if self.current_token().type == TokenType.PAREN_OPEN:
            return self.parse_cstyle_for_loop()
        else:
            var_token = self.current_token()
            self.expect_token(TokenType.IDENTIFIER)
            return self.parse_python_style_for_loop(var_token)

    def parse_cstyle_for_loop(self) -> ForCStyleLoop:
        self.expect_token(TokenType.PAREN_OPEN)
        init = self.parse_statement()
        self.expect_token(TokenType.SEMICOLON)
        condition = self.parse_expression()
        self.expect_token(TokenType.SEMICOLON)
        increment = self.parse_statement()
        self.expect_token(TokenType.PAREN_CLOSE)
        body = self.parse_block()
        return ForCStyleLoop(init, condition, increment, body)

    def parse_python_style_for_loop(self, var_token: Token) -> ForInLoop:
        self.expect_token(TokenType.KEYWORD, "in")
        iterable = self.parse_expression()
        body = self.parse_block()
        return ForInLoop(var_token.value, iterable, body)

    def parse_continue(self) -> Continue:
        self.advance()  # Skip 'continue'
        return Continue()

    def parse_break(self) -> Break:
        self.advance()  # Skip 'break'
        return Break()

    def parse_nil(self) -> NilType:
        self.advance()  # Skip 'nil'
        return NilType()

    def parse_function_def(self, as_async=False) -> FunctionDef:
        self.logger.debug("Entering parse_function_def")
        self.expect_token(TokenType.KEYWORD, "func")
        self.skip_whitespace()
        name = self.current_token().value
        self.logger.debug(f"Function name: {name}")
        self.advance()  # skip function name
        self.skip_whitespace()
        params, param_types = self.parse_parameters()
        self.logger.debug(f"Parsed parameters: {params}")
        self.logger.debug(f"Parsed parameter types: {param_types}")
        self.skip_whitespace()
        return_type = None
        if self.current_token().type == TokenType.OPERATOR and self.current_token().value == "->":
            self.advance()  # skip '->'
            return_type = self.parse_type_annotation()
            self.logger.debug(f"Parsed return type: {return_type}")
        body = self.parse_block()  # consumes both {}
        self.logger.debug(f"Parsed function body: {body}")
        func_def = (
            AsyncFunctionDef(name, params, param_types, return_type, body)
            if as_async
            else FunctionDef(name, params, param_types, return_type, body)
        )
        self.logger.debug(f"Created function definition: {func_def}")
        return func_def

    def parse_async_function_def(self) -> AsyncFunctionDef:
        self.expect_token(TokenType.KEYWORD, "async")
        self.skip_whitespace()
        return self.parse_function_def(as_async=True)

    def parse_await_expression(self) -> AwaitExpression:
        self.advance()  # Skip 'await'
        expr = self.parse_expression()
        return AwaitExpression(expr)

    def parse_return_statement(self) -> ASTNode:
        self.advance()  # Consume 'return' keyword
        expr = self.parse_expression()
        return ReturnStatement(expr)

    def parse_class_def(self) -> ClassDef:
        self.advance()  # skip 'class'
        self.skip_whitespace()
        name = self.current_token().value
        self.advance()  # skip class name
        self.skip_whitespace()
        base_class = None
        if self.current_token().type == TokenType.COLON:
            self.advance()  # skip ':'
            base_class = self.current_token().value
            self.advance()  # skip base class name
        self.expect_token(TokenType.BRACE_OPEN)
        methods, members = self.parse_class_members()
        self.expect_token(TokenType.BRACE_CLOSE)
        return ClassDef(name, base_class, methods, members)

    def parse_class_members(self) -> Tuple[List[FunctionDef], List[ASTNode]]:
        methods = []
        members = []
        while self.current_token().type != TokenType.BRACE_CLOSE:
            self.skip_whitespace()
            if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "func":
                methods.append(self.parse_function_def())
            else:
                # Handle other class members if necessary
                members.append(self.parse_statement())
            self.skip_whitespace()
        return methods, members

    def parse_if_statement(self) -> IfStatement:
        self.expect_token(TokenType.KEYWORD, "if")
        self.expect_token(TokenType.PAREN_OPEN)
        condition = self.parse_expression()
        self.expect_token(TokenType.PAREN_CLOSE)

        self.skip_whitespace()
        then_body = self.parse_block()  # parse_block handles the braces

        self.skip_whitespace()
        else_body = None
        if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "else":
            self.advance()
            self.skip_whitespace()
            else_body = self.parse_block()  # parse_block handles the braces

        return IfStatement(condition, then_body, else_body)

    def parse_while_statement(self) -> WhileStatement:
        self.advance()  # skip 'while'
        self.skip_whitespace()
        self.expect_token(TokenType.PAREN_OPEN)
        condition = self.parse_expression()
        self.expect_token(TokenType.PAREN_CLOSE)
        self.skip_whitespace()
        body = self.parse_block()
        return WhileStatement(condition, body)

    def parse_assignment_or_expression(self) -> ASTNode:
        name = self.current_token().value
        self.advance()  # skip identifier
        if self.current_token().type == TokenType.DOT:
            self.advance()  # skip '.'
            return self.parse_expression_with_prefix(name)
        if self.current_token().type == TokenType.OPERATOR:
            if self.current_token().value == "=":
                self.advance()  # skip '='
                value = self.parse_expression()
                var_type = self.parse_type_annotation()
                return Assignment(name, value, var_type)
            elif self.current_token().value == "++":
                self.advance()  # skip '++'
                return Assignment(name, BinaryOp(Expression(name), "+", Expression(1)))
            elif self.current_token().value == "--":
                self.advance()  # skip '--'
                return Assignment(name, BinaryOp(Expression(name), "-", Expression(1)))
            elif self.current_token().value in {"+=", "-=", "*=", "/="}:
                operator = self.current_token().value[0]  # get the operator part of '+=', '-=', etc.
                self.advance()  # skip operator
                value = self.parse_expression()
                return Assignment(name, BinaryOp(Expression(name), operator, value))
            else:
                # Handle binary operations
                left = Expression(name)
                return self.parse_binary_expression(left)
        elif self.current_token().type == TokenType.PAREN_OPEN:
            self.advance()  # skip '('
            args = self.parse_arguments()
            self.expect_token(TokenType.PAREN_CLOSE)
            return FunctionCall(name, args)
        elif self.current_token().type == TokenType.BRACE_OPEN:
            # Check if it's a map literal or a block
            if self.lookahead_is_map_literal():
                return self.parse_map_literal()
            else:
                return self.parse_block()
        elif self.current_token().type == TokenType.NEWLINE:
            self.advance()  # skip newline
            return Expression(name)
        raise SyntaxError(
            f"Unexpected token: {self.current_token()} value: '{self.current_token().value}' after identifier"
        )

    def parse_binary_expression(self, left: ASTNode) -> ASTNode:
        operator = self.current_token().value
        self.advance()  # skip operator
        right = self.parse_expression()
        return BinaryOp(left, operator, right)

    def parse_expression_with_prefix(self, prefix: str) -> ASTNode:
        if self.current_token().type == TokenType.IDENTIFIER:
            suffix = self.current_token().value
            self.advance()
            if self.current_token().type == TokenType.PAREN_OPEN:
                self.advance()
                args = self.parse_arguments()
                self.expect_token(TokenType.PAREN_CLOSE)
                return MethodCall(prefix, suffix, args)
            return BinaryOp(prefix, ".", suffix)
        # Handle case where no identifier follows the dot
        if self.current_token().type == TokenType.BRACE_CLOSE:
            return Expression(prefix)
        raise SyntaxError(f"Expected identifier after '.', got {self.current_token()}")

    def parse_parameters(self) -> Tuple[List[str], List[Type]]:
        self.logger.debug("Entering parse_parameters")
        params = []
        param_types = []
        self.skip_whitespace()
        if self.current_token().type == TokenType.PAREN_OPEN:
            self.advance()  # Skip '('
            while self.current_token().type != TokenType.PAREN_CLOSE:
                self.skip_whitespace()
                param_name = self.current_token().value
                self.logger.debug(f"Parsed parameter name: {param_name}")
                self.advance()  # Skip parameter name
                self.skip_whitespace()
                self.expect_token(TokenType.COLON)
                self.skip_whitespace()
                param_type = self.parse_type_annotation()
                self.logger.debug(f"Parsed parameter type: {param_type}")
                params.append(param_name)
                param_types.append(param_type)
                self.skip_whitespace()
                if self.current_token().type == TokenType.COMMA:
                    self.advance()  # Skip ','
                    self.skip_whitespace()
            self.advance()  # Skip ')'
        else:
            raise SyntaxError(f"Expected TokenType.PAREN_OPEN, got {self.current_token()}")
        self.logger.debug(f"Parsed parameters: {params}")
        self.logger.debug(f"Parsed parameter types: {param_types}")
        return params, param_types

    def parse_arguments(self) -> List[ASTNode]:
        args = []
        while self.current_token().type != TokenType.PAREN_CLOSE:
            args.append(self.parse_expression())
            if self.current_token().type == TokenType.COMMA:
                self.advance()
        return args

    def parse_block(self) -> List[ASTNode]:
        statements = []
        self.expect_token(TokenType.BRACE_OPEN)
        while self.current_token().type != TokenType.BRACE_CLOSE:
            if self.current_token().type == TokenType.EOF:
                break
            statements.append(self.parse_statement())
            while self.current_token().type == TokenType.NEWLINE:
                self.advance()
            self.skip_whitespace()
        self.expect_token(TokenType.BRACE_CLOSE)
        return statements

    def parse_expression(self, min_precedence=0) -> ASTNode:
        self.logger.debug(f"parse_expression.Entering parse_expression with min_precedence: {min_precedence}")
        left = self.parse_primary()
        self.logger.debug(f"parse_expression.After parse_primary, left: {left}")

        while self.current_token().type == TokenType.OPERATOR:
            operator = self.current_token().value
            precedence = self.get_operator_precedence(operator)
            self.logger.debug(f"parse_expression.Operator: {operator}, Precedence: {precedence}")

            if precedence < min_precedence:
                self.logger.debug(f"parse_expression.Exiting parse_expression with left: {left}")
                break

            self.advance()  # Consume the operator
            right = self.parse_expression(precedence + 1)
            self.logger.debug(f"parse_expression.After parse_expression, right: {right}")
            left = BinaryOp(left, operator, right)
            self.logger.debug(f"parse_expression.After BinaryOp, left: {left}")

        return left

    def get_operator_precedence(self, operator: str) -> int:
        precedences = {
            "||": 1,
            "&&": 2,
            "not": 3,
            "in": 4,
            "not in": 4,
            "is": 4,
            "is not": 4,
            "<": 4,
            "<=": 4,
            ">": 4,
            ">=": 4,
            "!=": 4,
            "==": 4,
            "|": 5,
            "^": 6,
            "&": 7,
            "<<": 8,
            ">>": 8,
            "+": 9,
            "-": 9,
            "*": 10,
            "@": 10,
            "/": 10,
            "//": 10,
            "%": 10,
            "~": 11,
            "**": 12,
        }
        return precedences.get(operator, 0)

    def parse_primary(self) -> ASTNode:
        self.skip_whitespace()
        token = self.current_token()
        if token.type == TokenType.LITERAL:
            self.advance()
            return Expression(token.value)
        if token.type == TokenType.KEYWORD and token.value == "await":
            self.advance()  # Skip 'await'
            expr = self.parse_expression()
            return AwaitExpression(expr)
        elif token.type == TokenType.KEYWORD and token.value in {"true", "false"}:
            self.advance()
            return Expression(True if token.value == "true" else False)
        elif token.type == TokenType.STRING:
            self.advance()
            return StringLiteral(token.value)
        elif token.type == TokenType.BRACKET_OPEN:
            return self.parse_array_literal()
        elif token.type == TokenType.BRACE_OPEN:
            return self.parse_map_literal()
        elif token.type == TokenType.PAREN_OPEN:
            return (
                self.parse_tuple_literal()
            )  # this should return tuple literal OR whatever was originally in the parenthesis if not a tuple
        elif token.type == TokenType.IDENTIFIER:
            identifier = token.value
            self.advance()
            self.skip_whitespace()
            if self.current_token().type == TokenType.PAREN_OPEN:
                self.advance()  # skip '('
                args = self.parse_arguments()
                self.expect_token(TokenType.PAREN_CLOSE)
                return FunctionCall(identifier, args)
            return Expression(identifier)
        elif token.type == TokenType.KEYWORD:
            identifier = token.value
            self.advance()
            self.skip_whitespace()
            if self.current_token().type == TokenType.PAREN_OPEN:
                self.advance()  # skip '('
                args = self.parse_arguments()
                self.expect_token(TokenType.PAREN_CLOSE)
                return FunctionCall(identifier, args)
            return Expression(identifier)
        else:
            raise SyntaxError(f"Unexpected token: {token} value: '{token.value}' after identifier")

    def parse_array_literal(self) -> ArrayLiteral:
        self.advance()  # skip '['
        elements = []
        while self.current_token().type != TokenType.BRACKET_CLOSE:
            elements.append(self.parse_expression())
            if self.current_token().type == TokenType.COMMA:
                self.advance()
        self.expect_token(TokenType.BRACKET_CLOSE)
        return ArrayLiteral(elements)

    def parse_map_literal(self) -> MapLiteral:
        self.advance()  # skip '{'
        pairs = {}
        while self.current_token().type != TokenType.BRACE_CLOSE:
            key = self.parse_expression()
            self.expect_token(TokenType.COLON)
            value = self.parse_expression()
            pairs[key] = value
            if self.current_token().type == TokenType.COMMA:
                self.advance()
        self.expect_token(TokenType.BRACE_CLOSE)
        return MapLiteral(pairs)

    def parse_tuple_literal(self) -> TupleLiteral:
        self.advance()  # skip '('
        elements = []
        while self.current_token().type != TokenType.PAREN_CLOSE:
            elements.append(self.parse_expression())
            if self.current_token().type == TokenType.COMMA:
                self.advance()
            else:
                break  # If there's no comma, it's not a tuple
        self.expect_token(TokenType.PAREN_CLOSE)
        return (
            TupleLiteral(elements) if len(elements) > 1 or self.current_token().type == TokenType.COMMA else elements[0]
        )

    def parse_type_annotation(self) -> Optional[Type]:
        if self.current_token().type == TokenType.KEYWORD:
            type_name = self.current_token().value
            self.advance()
            if type_name == "int":
                return IntType()
            elif type_name == "float":
                return FloatType()
            elif type_name == "string" or type_name == "str":
                return StringType()
            elif type_name == "bool":
                return BoolType()
            elif type_name == "array":
                self.expect_token(TokenType.BRACKET_OPEN, "[")
                element_type = self.parse_type_annotation()
                self.expect_token(TokenType.BRACKET_CLOSE, "]")
                return ArrayType(element_type)
            elif type_name == "map":
                self.expect_token(TokenType.BRACKET_OPEN, "[")
                key_type = self.parse_type_annotation()
                self.expect_token(TokenType.BRACKET_CLOSE, "]")
                value_type = self.parse_type_annotation()
                return MapType(key_type, value_type)
            elif type_name == "tuple":
                self.expect_token(TokenType.BRACKET_OPEN, "[")
                element_types = []
                while self.current_token().type != TokenType.BRACKET_CLOSE:
                    element_types.append(self.parse_type_annotation())
                    if self.current_token().type == TokenType.DELIMITER:
                        self.advance()  # Skip comma
                self.expect_token(TokenType.BRACKET_CLOSE, "]")
                return TupleType(element_types)
        return None

    def expect_token(self, type: str, value: Optional[str] = None):
        token = self.current_token()
        if token.type == TokenType.EOF and type == TokenType.NEWLINE:
            return  # Gracefully handle EOF when a newline is expected
        if token.type != type or (value and token.value != value):
            raise SyntaxError(f"Expected {type}({value}), got {token}")
        self.advance()

    def skip_whitespace(self):
        while (
            isinstance(self.current_token().value, str)
            and self.current_token().type != TokenType.EOF
            and self.current_token().value.isspace()
            or self.current_token().type == TokenType.NEWLINE
        ):
            self.advance()

    def lookahead_is_map_literal(self) -> bool:
        # Look ahead to determine if the brace indicates a map literal
        pos = self.pos
        token = self.current_token()
        if token.type == TokenType.BRACE_OPEN:
            self.advance()
            if self.current_token().type == TokenType.IDENTIFIER:
                self.advance()
                if self.current_token().type == TokenType.COLON:
                    self.pos = pos  # Reset position
                    return True
        self.pos = pos  # Reset position
        return False

    def parse_variable_declaration(self) -> Assignment:
        self.advance()  # Skip 'var'
        name_token = self.current_token()
        self.expect_token(TokenType.IDENTIFIER)
        self.expect_token(TokenType.COLON, ":")
        var_type = self.parse_type_annotation()
        self.expect_token(TokenType.OPERATOR, "=")
        value = self.parse_expression()
        return Assignment(name_token.value, value, var_type)
