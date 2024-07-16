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


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> List[ASTNode]:
        statements = []
        while self.current_token().type != TokenType.EOF:
            print(f"Parsing statement: {self.current_token()}")  # Debug print
            statements.append(self.parse_statement())
        return statements

    def current_token(self) -> Token:
        if self.pos >= len(self.tokens):
            return Token(TokenType.EOF, "", line=-1, column=-1)
        return self.tokens[self.pos]

    def advance(self):
        print(f"Advancing from {self.current_token()}")  # Debug print
        self.pos += 1

    def parse_statement(self) -> ASTNode:
        token = self.current_token()
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
            elif token.value == "return":
                return self.parse_return_statement()
        elif token.type == TokenType.IDENTIFIER:
            return self.parse_assignment_or_expression()
        raise SyntaxError(f"Unexpected token: {token}")

    def parse_module_def(self) -> ModuleDef:
        self.advance()  # Skip 'module'
        name_token = self.current_token()
        self.expect_token(TokenType.IDENTIFIER)
        self.advance()  # Skip module name
        self.expect_token(TokenType.NEWLINE)
        self.advance()  # Skip newline
        body = []
        while self.current_token().type != TokenType.EOF:
            if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "module":
                break
            body.append(self.parse_statement())
        return ModuleDef(name_token.value, body)

    def parse_import_def(self) -> ImportDef:
        self.advance()  # Skip 'import'
        module_name = self.current_token().value.strip('"')
        self.expect_token(TokenType.STRING)
        self.advance()  # Skip the string token
        return ImportDef(module_name)

    def parse_export_def(self) -> ExportDef:
        self.advance()  # Skip 'export'
        name_token = self.current_token()
        self.expect_token(TokenType.IDENTIFIER)
        self.advance()  # Skip the identifier
        self.expect_token(TokenType.OPERATOR, "=")
        self.advance()  # Skip '='
        value = self.parse_expression()
        self.expect_token(TokenType.NEWLINE)
        self.advance()  # Skip newline
        return ExportDef(name_token.value, value)

    def parse_for_loop(self) -> ASTNode:
        self.advance()  # Skip 'for'
        var_token = self.current_token()
        self.expect_token(TokenType.IDENTIFIER)
        self.advance()
        if self.current_token().type == TokenType.BRACKET_OPEN:
            return self.parse_cstyle_for_loop()
        if self.current_token().value == "in":
            return self.parse_for_in_loop(var_token)
        raise SyntaxError(f"Unexpected token in for loop: {self.current_token()}")

    def parse_for_in_loop(self, var_token: Token) -> ForInLoop:
        self.advance()  # Skip 'in'
        iterable = self.parse_expression()
        self.expect_token(TokenType.BRACE_OPEN)
        body = self.parse_block()
        self.expect_token(TokenType.BRACE_CLOSE)
        return ForInLoop(var_token.value, iterable, body)

    def parse_cstyle_for_loop(self) -> ForCStyleLoop:
        self.advance()  # Skip '('
        init = self.parse_expression()
        self.expect_token(TokenType.DELIMITER)  # Expect ';'
        condition = self.parse_expression()
        self.expect_token(TokenType.DELIMITER)  # Expect ';'
        increment = self.parse_expression()
        self.expect_token(TokenType.BRACKET_CLOSE)  # Expect ')'
        self.expect_token(TokenType.BRACE_OPEN)
        body = self.parse_block()
        self.expect_token(TokenType.BRACE_CLOSE)
        return ForCStyleLoop(init, condition, increment, body)

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
        self.advance()  # skip 'func'
        name = self.current_token().value
        self.advance()  # skip function name
        params, param_types = self.parse_parameters()
        if self.current_token().type == TokenType.OPERATOR and self.current_token().value == "->":
            self.advance()  # skip '->'
            return_type = self.parse_type_annotation()
        else:
            return_type = None
        self.expect_token(TokenType.BRACE_OPEN)
        self.advance()  # Skip '{'
        body = self.parse_block()
        self.expect_token(TokenType.BRACE_CLOSE)
        self.advance()  # Skip '}'
        return (
            AsyncFunctionDef(name, params, param_types, return_type, body)
            if as_async
            else FunctionDef(name, params, param_types, return_type, body)
        )

    def parse_async_function_def(self) -> AsyncFunctionDef:
        return self.parse_function_def(as_async=True)

    def parse_return_statement(self) -> ASTNode:
        self.advance()  # Consume 'return' keyword
        expr = self.parse_expression()
        return ReturnStatement(expr)

    def parse_class_def(self) -> ClassDef:
        self.advance()  # skip 'class'
        name = self.current_token().value
        self.advance()  # skip class name
        base_class = None
        if self.current_token().type == TokenType.COLON:
            self.advance()  # skip ':'
            base_class = self.current_token().value
            self.advance()  # skip base class name
        self.expect_token(TokenType.BRACE_OPEN)
        methods = self.parse_methods()
        self.expect_token(TokenType.BRACE_CLOSE)
        return ClassDef(name, base_class, methods)

    def parse_methods(self) -> List[FunctionDef]:
        methods = []
        while self.current_token().type != TokenType.BRACE_CLOSE:
            methods.append(self.parse_function_def())
        return methods

    def parse_if_statement(self) -> IfStatement:
        self.advance()  # skip 'if'
        condition = self.parse_expression()
        self.expect_token(TokenType.BRACE_OPEN)
        then_body = self.parse_block()
        self.expect_token(TokenType.BRACE_CLOSE)
        else_body = None
        if self.current_token().value == "else":
            self.advance()  # skip 'else'
            self.expect_token(TokenType.BRACE_OPEN)
            else_body = self.parse_block()
            self.expect_token(TokenType.BRACE_CLOSE)
        return IfStatement(condition, then_body, else_body)

    def parse_while_statement(self) -> WhileStatement:
        self.advance()  # skip 'while'
        condition = self.parse_expression()
        self.expect_token(TokenType.BRACE_OPEN)
        body = self.parse_block()
        self.expect_token(TokenType.BRACE_CLOSE)
        return WhileStatement(condition, body)

    def parse_assignment_or_expression(self) -> ASTNode:
        name = self.current_token().value
        self.advance()  # skip identifier
        if self.current_token().type == TokenType.OPERATOR and self.current_token().value == "=":
            self.advance()  # skip '='
            value = self.parse_expression()
            var_type = self.parse_type_annotation()
            return Assignment(name, value, var_type)
        elif self.current_token().type == TokenType.PAREN_OPEN:
            self.advance()  # skip '('
            args = self.parse_arguments()
            self.expect_token(TokenType.PAREN_CLOSE)
            return FunctionCall(name, args)
        elif self.current_token().type == TokenType.OPERATOR and self.current_token().value == ".":
            self.advance()  # skip '.'
            return self.parse_expression_with_prefix(name)
        elif self.current_token().type == TokenType.NEWLINE:
            self.advance()  # skip newline
            return Expression(name)
        raise SyntaxError(f"Unexpected token: {self.current_token()} after identifier")

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
        params = []
        param_types = []
        if self.current_token().type == TokenType.PAREN_OPEN:
            self.advance()  # Skip '('
        else:
            raise SyntaxError(f"Expected TokenType.PAREN_OPEN, got {self.current_token()}")
        while self.current_token().type != TokenType.PAREN_CLOSE:
            print(f"Current token (param name): {self.current_token()}")  # Debug print
            param_name = self.current_token().value
            self.advance()
            print(f"Current token (expect colon): {self.current_token()}")  # Debug print
            self.expect_token(TokenType.COLON)  # Ensure there's a colon after the parameter name
            self.advance()  # Skip ':'
            param_type = self.parse_type_annotation()
            params.append(param_name)
            param_types.append(param_type)
            if self.current_token().type == TokenType.COMMA:
                self.advance()
        self.expect_token(TokenType.PAREN_CLOSE)  # Ensure there's a closing parenthesis
        self.advance()  # Skip ')'
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
        while self.current_token().type != TokenType.BRACE_CLOSE:
            statements.append(self.parse_statement())
        return statements

    def parse_expression(self) -> ASTNode:
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
            return self.parse_tuple_literal()
        elif token.type == TokenType.IDENTIFIER:
            identifier = token.value
            self.advance()
            if self.current_token().type == TokenType.OPERATOR:
                operator = self.current_token().value
                self.advance()
                right = self.parse_expression()
                return BinaryOp(identifier, operator, right)
            return self.parse_expression_with_prefix(identifier)
        else:
            left = self.current_token().value
            self.advance()
            if self.current_token().type == TokenType.OPERATOR:
                operator = self.current_token().value
                self.advance()
                right = self.parse_expression()
                return BinaryOp(left, operator, right)
            return Expression(left)

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
        self.expect_token(TokenType.PAREN_CLOSE)
        return TupleLiteral(elements)

    def parse_type_annotation(self) -> Optional[Type]:
        if self.current_token().type == TokenType.KEYWORD:
            if self.current_token().value == "int":
                self.advance()
                return IntType()
            elif self.current_token().value == "float":
                self.advance()
                return FloatType()
            elif self.current_token().value == "string":
                self.advance()
                return StringType()
            elif self.current_token().value == "bool":
                self.advance()
                return BoolType()
            elif self.current_token().value == "array":
                self.advance()
                self.expect_token(TokenType.BRACKET_OPEN, "[")
                element_type = self.parse_type_annotation()
                self.expect_token(TokenType.BRACKET_CLOSE, "]")
                return ArrayType(element_type)
            elif self.current_token().value == "map":
                self.advance()
                self.expect_token(TokenType.BRACKET_OPEN, "[")
                key_type = self.parse_type_annotation()
                self.expect_token(TokenType.BRACKET_CLOSE, "]")
                value_type = self.parse_type_annotation()
                return MapType(key_type, value_type)
            elif self.current_token().value == "tuple":
                self.advance()
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
