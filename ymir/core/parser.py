from typing import List, Optional, Tuple

from ymir.core.ast import (
    ArrayAccess,
    ArrayLiteral,
    Assignment,
    ASTNode,
    AsyncFunctionDef,
    AwaitExpression,
    BinaryOp,
    Break,
    ChannelSend,
    ClassDef,
    Continue,
    ExceptClause,
    ExceptionDef,
    ExportDef,
    Expression,
    FinallyClause,
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
    SpawnStatement,
    StringLiteral,
    ThrowStatement,
    TryExceptStatement,
    TupleLiteral,
    UnaryOp,
    WhileStatement,
)
from ymir.core.lexer import Token, TokenType
from ymir.core.types import (
    AnyType,
    ArrayType,
    BoolType,
    ChannelType,
    FloatType,
    IntType,
    MapType,
    MatrixType,
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
        self.logger.debug(f"parse_statement: Current token: {token}")

        if token.type == TokenType.EOF:
            return None  # Gracefully handle EOF

        # Handle closing braces - they should be handled by the parse_block method
        if token.type == TokenType.BRACE_CLOSE:
            return None  # Let the calling parse_block method handle this

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
                self.logger.debug("parse_statement: Detected while keyword")
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
            elif token.value == "try":
                return self.parse_try_except_statement()
            elif token.value == "throw":
                return self.parse_throw_statement()
            elif token.value == "exception":
                return self.parse_exception_def()
            elif token.value == "spawn":
                return self.parse_spawn_statement()
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

    def parse_while_statement(self) -> WhileStatement:
        self.logger.debug("Entering parse_while_statement")
        self.advance()  # skip 'while'
        self.skip_whitespace()
        self.logger.debug(f"Current token after 'while': {self.current_token()}")

        # Parentheses are optional around the condition (like Go/Rust)
        has_parens = self.current_token().type == TokenType.PAREN_OPEN
        if has_parens:
            self.advance()  # skip '('

        condition = self.parse_expression()
        self.logger.debug(f"Parsed while condition: {condition}")

        if has_parens:
            self.expect_token(TokenType.PAREN_CLOSE)

        body = self.parse_block()
        self.logger.debug(f"Parsed while body: {body}")
        return WhileStatement(condition, body)

    def parse_module_def(self) -> ModuleDef:
        """Parse a module definition."""
        self.advance()  # Skip 'module'
        self.skip_whitespace()

        if self.current_token().type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected module name, got {self.current_token()}")

        name = self.current_token().value
        self.advance()  # Skip identifier

        # Handle dotted module names (e.g., module a.b.c)
        while self.current_token().type == TokenType.DOT:
            self.advance()  # Skip the dot
            # Allow both identifiers and keywords as module name components
            if self.current_token().type not in [TokenType.IDENTIFIER, TokenType.KEYWORD]:
                raise SyntaxError(
                    f"Expected identifier or keyword after dot in module name, got {self.current_token()}"
                )
            name += "." + self.current_token().value
            self.advance()  # Skip identifier/keyword

        # Make sure we consume the newline after the module declaration
        if self.current_token().type == TokenType.NEWLINE:
            self.advance()

        # Parse the module body
        body = []
        while self.current_token().type != TokenType.EOF:
            if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "module":
                # Stop when we reach another module definition
                break

            statement = self.parse_statement()
            if statement:
                body.append(statement)
                self.logger.debug(f"Added statement to module body: {type(statement).__name__}")

        self.logger.debug(f"Final module body count: {len(body)}")
        return ModuleDef(name, body)

    def parse_import_def(self) -> ImportDef:
        self.advance()  # Skip 'import'

        # Check if the import is a string literal or an identifier
        if self.current_token().type == TokenType.STRING:
            module_name = self.current_token().value.strip('"')
            self.advance()  # Skip string literal
        elif self.current_token().type == TokenType.IDENTIFIER:
            module_name = self.current_token().value
            self.advance()  # Skip identifier

            # Handle dotted import names (e.g., import a.b.c)
            while self.current_token().type == TokenType.DOT:
                self.advance()  # Skip the dot
                if self.current_token().type != TokenType.IDENTIFIER:
                    raise SyntaxError(f"Expected identifier after dot in import name, got {self.current_token()}")
                module_name += "." + self.current_token().value
                self.advance()  # Skip identifier
        else:
            raise SyntaxError(f"Expected string or identifier for import, got {self.current_token()}")

        return ImportDef(module_name)

    def parse_export_def(self) -> ExportDef:
        """Parse an export definition."""
        self.advance()  # Skip 'export'

        # Check if we're exporting a function
        if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "func":
            function_def = self.parse_function_def()
            function_def.is_export = True
            return ExportDef(function_def.name, function_def)

        # Otherwise, it's a simple export assignment
        name = self.current_token().value
        self.expect_token(TokenType.IDENTIFIER)
        self.expect_token(TokenType.OPERATOR, "=")
        value = self.parse_expression()

        # Consume the newline if present
        if self.current_token().type == TokenType.NEWLINE:
            self.advance()

        return ExportDef(name, value)

    def parse_for_loop(self) -> ASTNode:
        """Parse a for loop, which can be a for-in loop or a C-style for loop."""
        self.advance()  # Skip 'for'
        self.skip_whitespace()

        # Check for C-style for loop (with parentheses)
        if self.current_token().type == TokenType.PAREN_OPEN:
            return self.parse_cstyle_for_loop()

        # It's a for-in loop
        var = self.current_token().value
        self.advance()  # Skip variable name

        self.skip_whitespace()
        self.expect_token(TokenType.KEYWORD, "in")
        self.skip_whitespace()

        iterable = self.parse_expression()
        body = self.parse_block()

        return ForInLoop(var, iterable, body)

    def parse_cstyle_for_loop(self) -> ForCStyleLoop:
        """Parse a C-style for loop."""
        self.advance()  # Skip opening parenthesis

        # Parse initialization - might be an assignment or an expression
        # Try to handle both syntax forms "for (i = 0; ...)" and "for (var i = 0; ...)"
        if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "var":
            init = self.parse_variable_declaration()
        else:
            init = self.parse_assignment_or_expression()

        self.expect_token(TokenType.SEMICOLON)

        # Parse condition
        condition = self.parse_expression()
        self.expect_token(TokenType.SEMICOLON)

        # Parse increment - handle special case for i++ and i--
        if (
            self.current_token().type == TokenType.IDENTIFIER
            and self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].type == TokenType.OPERATOR
            and self.tokens[self.pos + 1].value in ("++", "--")
        ):
            identifier = self.current_token().value
            self.advance()  # Skip identifier
            op = self.current_token().value
            self.advance()  # Skip operator
            increment = UnaryOp(op, Expression(identifier), postfix=True)
        else:
            increment = self.parse_assignment_or_expression()

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

    def parse_function_def(self) -> FunctionDef:
        """Parse a function definition."""
        self.logger.debug("Entering parse_function_def")
        self.advance()  # Skip 'func'

        # Parse function name
        if self.current_token().type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected function name, got {self.current_token()}")

        function_name = self.current_token().value
        self.logger.debug(f"Function name: {function_name}")
        self.advance()  # Skip function name

        # Parse parameters
        params, param_types = self.parse_parameters()
        self.logger.debug(f"Parsed parameters: {params}")
        self.logger.debug(f"Parsed parameter types: {param_types}")

        # Parse return type if present
        # TODO(multiple-returns): Implement support for multiple return values (func() -> int, error)
        # Currently only supports single return type
        return_type = None
        if self.current_token().type == TokenType.OPERATOR and self.current_token().value == "->":
            self.advance()  # Skip '->'
            return_type = self.parse_type_annotation()
            self.logger.debug(f"Parsed return type: {return_type}")

        # Parse function body
        body = self.parse_block()
        self.logger.debug(f"Parsed function body: {body}")

        # Create and return the function definition - fix parameter order!
        function_def = FunctionDef(
            name=function_name, params=params, param_types=param_types, return_type=return_type, body=body
        )
        self.logger.debug(f"Created function definition: {function_def}")
        return function_def

    def parse_async_function_def(self) -> AsyncFunctionDef:
        self.expect_token(TokenType.KEYWORD, "async")
        self.skip_whitespace()

        # Parse as a regular function but then convert to async
        func_def = self.parse_function_def()

        # Convert to AsyncFunctionDef
        async_func = AsyncFunctionDef(
            name=func_def.name,
            params=func_def.params,
            param_types=func_def.param_types,
            return_type=func_def.return_type,
            body=func_def.body,
        )

        return async_func

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

        # Parentheses are optional around the condition
        has_parens = self.current_token().type == TokenType.PAREN_OPEN
        if has_parens:
            self.expect_token(TokenType.PAREN_OPEN)

        condition = self.parse_expression()

        if has_parens:
            self.expect_token(TokenType.PAREN_CLOSE)

        self.skip_whitespace()
        then_body = self.parse_block()  # parse_block handles the braces

        self.skip_whitespace()
        else_body = None
        if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "else":
            self.advance()
            self.skip_whitespace()
            # Support chained else if
            if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "if":
                else_body = [self.parse_if_statement()]
            else:
                else_body = self.parse_block()  # parse_block handles the braces

        return IfStatement(condition, then_body, else_body)

    def parse_assignment_or_expression(self) -> ASTNode:
        """Parse an assignment or expression statement."""
        start_pos = self.pos
        token = self.current_token()
        self.logger.debug(f"parse_assignment_or_expression: Starting with token: {token}")

        # Handle special increment/decrement operators like a++ and a--
        if (
            token.type == TokenType.IDENTIFIER
            and self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].type == TokenType.OPERATOR
            and self.tokens[self.pos + 1].value in ("++", "--")
        ):
            identifier = token.value
            self.advance()  # Skip identifier
            op = self.current_token().value
            self.advance()  # Skip operator
            return UnaryOp(op, Expression(identifier), postfix=True)

        # Reset position and try normal assignment
        self.pos = start_pos

        # Try to parse as an assignment (identifier or property access)
        lhs = self.parse_expression()
        self.logger.debug(f"parse_assignment_or_expression: Parsed LHS: {lhs}")

        # Check if this is an assignment (simple or compound)
        if self.current_token().type == TokenType.OPERATOR and self.current_token().value in (
            "=",
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "**=",
            "//=",
        ):
            operator = self.current_token().value
            self.advance()  # Skip the operator

            # Check if lhs is a valid assignment target
            if isinstance(lhs, Expression) and isinstance(lhs.expression, str):
                if "." not in lhs.expression:  # Simple identifier assignment
                    target = lhs.expression  # Use the string identifier
                    value = self.parse_expression()

                    # Handle compound assignment operators by desugaring
                    if operator != "=":
                        # Convert += to +, -= to -, etc.
                        base_operator = operator[:-1]  # Remove the '=' from '+=', '-=', etc.
                        value = BinaryOp(operator=base_operator, left=lhs, right=value)

                    return Assignment(target, value)
                else:  # Property access assignment (e.g., self.message = value)
                    target = lhs  # Use the Expression object
                    value = self.parse_expression()

                    # Handle compound assignment operators by desugaring
                    if operator != "=":
                        # Convert += to +, -= to -, etc.
                        base_operator = operator[:-1]  # Remove the '=' from '+=', '-=', etc.
                        value = BinaryOp(operator=base_operator, left=lhs, right=value)

                    return Assignment(target, value)
            elif isinstance(lhs, MethodCall):  # Property access via MethodCall
                target = lhs  # Use the MethodCall object
                value = self.parse_expression()

                # Handle compound assignment operators by desugaring
                if operator != "=":
                    # Convert += to +, -= to -, etc.
                    base_operator = operator[:-1]  # Remove the '=' from '+=', '-=', etc.
                    value = BinaryOp(operator=base_operator, left=lhs, right=value)

                return Assignment(target, value)
            elif isinstance(lhs, Expression) and isinstance(
                lhs.expression, MethodCall
            ):  # Expression containing MethodCall
                target = lhs  # Use the Expression object containing MethodCall
                value = self.parse_expression()

                # Handle compound assignment operators by desugaring
                if operator != "=":
                    # Convert += to +, -= to -, etc.
                    base_operator = operator[:-1]  # Remove the '=' from '+=', '-=', etc.
                    value = BinaryOp(operator=base_operator, left=lhs, right=value)

                return Assignment(target, value)
            elif isinstance(lhs, ArrayAccess):  # Array element assignment (e.g., arr[0] = value)
                target = lhs  # Use the ArrayAccess object as target
                value = self.parse_expression()

                # Handle compound assignment operators by desugaring
                if operator != "=":
                    # Convert += to +, -= to -, etc.
                    base_operator = operator[:-1]  # Remove the '=' from '+=', '-=', etc.
                    value = BinaryOp(operator=base_operator, left=lhs, right=value)

                return Assignment(target, value)
            else:
                # Not a valid assignment target, treat as expression
                pass

        # If not an assignment, backtrack and parse as an expression
        self.logger.debug("parse_assignment_or_expression: Not an assignment, parsing as expression")
        self.pos = start_pos
        return self.parse_expression()

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

                # Check if there's a type annotation (colon)
                if self.current_token().type == TokenType.COLON:
                    self.advance()  # Skip ':'
                    self.skip_whitespace()
                    param_type = self.parse_type_annotation()
                    self.logger.debug(f"Parsed parameter type: {param_type}")
                else:
                    # No type annotation (e.g., for 'self')
                    param_type = None
                    self.logger.debug(f"Parameter {param_name} has no type annotation")

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
        """Parse function call arguments."""
        args = []

        # Parse arguments if any
        if self.current_token().type != TokenType.PAREN_CLOSE:
            args.append(self.parse_expression())
            while self.current_token().type == TokenType.COMMA:
                self.advance()  # Skip comma
                args.append(self.parse_expression())

        return args

    def parse_block(self) -> List[ASTNode]:
        """Parse a block of statements enclosed in braces."""
        self.expect_token(TokenType.BRACE_OPEN)

        statements = []
        nesting_level = 1  # Track braces nesting

        # Skip any initial newlines after the opening brace
        while self.current_token().type == TokenType.NEWLINE:
            self.advance()

        while self.current_token().type != TokenType.EOF:
            # Track nesting depth of braces
            if self.current_token().type == TokenType.BRACE_OPEN:
                # If we're already inside a block, we need to parse nested blocks as part of statements
                if nesting_level > 1:
                    statement = self.parse_statement()
                    if statement:
                        statements.append(statement)
                else:
                    nesting_level += 1
                    self.advance()

            elif self.current_token().type == TokenType.BRACE_CLOSE:
                nesting_level -= 1
                if nesting_level == 0:
                    self.advance()  # Consume closing brace
                    break
                else:
                    # This closing brace belongs to a nested block
                    self.advance()

            # Skip newlines
            elif self.current_token().type == TokenType.NEWLINE:
                self.advance()

            # Parse regular statements
            else:
                statement = self.parse_statement()
                if statement:
                    statements.append(statement)

        return statements

    def parse_expression(self, min_precedence=0) -> Expression:
        """Parse an expression using precedence climbing."""
        self.logger.debug(f"Entering parse_expression with min_precedence: {min_precedence}")

        # Parse the leftmost term first
        left = self.parse_primary()
        self.logger.debug(f"After parse_primary, left: {left}")

        # Then handle any operators that follow
        while (
            self.pos < len(self.tokens)
            and self.current_token().type == TokenType.OPERATOR
            and self.get_operator_precedence(self.current_token().value) >= min_precedence
            and self.get_operator_precedence(self.current_token().value) > 0  # Skip assignment operators
        ):
            current_token = self.current_token()
            op = current_token.value

            # Get operator precedence
            precedence = self.get_operator_precedence(op)
            self.logger.debug(f"Operator: {op}, Precedence: {precedence}")

            if precedence < min_precedence:
                break  # This operator has lower precedence than the current min

            self.advance()  # Move past the operator

            # Parse the right operand with higher precedence to ensure correct associativity
            right = self.parse_expression(precedence + 1)
            self.logger.debug(f"After parse_expression, right: {right}")

            # Handle channel operations specially
            if op == "<-":
                # channel <- value (send)
                left = ChannelSend(channel=left, value=right)
            else:
                # Create a binary operation node with the left operand, operator, and right operand
                # Use named parameters to ensure correct order
                left = BinaryOp(operator=op, left=left, right=right)
            self.logger.debug(f"After operator handling, left: {left}")

        self.logger.debug(f"Returning expression: {left}")
        return left

    def get_operator_precedence(self, operator: str) -> int:
        # Assignment operators should have lowest precedence (0) so they're not handled by precedence climbing
        if operator in ("=", "+=", "-=", "*=", "/=", "%=", "**=", "//="):
            return 0

        precedences = {
            "<-": 1,  # Channel operations
            "||": 2,
            "&&": 3,
            "not": 4,
            "in": 5,
            "not in": 5,
            "is": 5,
            "is not": 5,
            "<": 5,
            "<=": 5,
            ">": 5,
            ">=": 5,
            "!=": 5,
            "==": 5,
            "|": 6,
            "^": 7,
            "&": 8,
            "<<": 9,
            ">>": 9,
            "+": 10,
            "-": 10,
            "*": 11,
            "@": 11,
            "/": 11,
            "//": 11,
            "%": 11,
            "~": 12,
            "**": 13,
        }
        return precedences.get(operator, 0)

    def parse_primary(self) -> Expression:
        """Parse a primary expression (an atom)."""
        self.skip_whitespace()
        token = self.current_token()

        # Handle unary operators
        if token.type == TokenType.OPERATOR and token.value in ["-", "+"]:
            op = token.value
            self.advance()  # Skip the unary operator
            operand = self.parse_primary()  # Parse the operand
            return UnaryOp(operator=op, operand=operand)

        if token.type == TokenType.LITERAL:
            self.advance()
            expr = Expression(token.value)
        elif token.type == TokenType.KEYWORD and token.value == "await":
            self.advance()  # Skip 'await'
            expr = AwaitExpression(self.parse_expression())
        elif token.type == TokenType.KEYWORD and token.value in {"true", "false"}:
            self.advance()
            expr = Expression(True if token.value == "true" else False)
        elif token.type == TokenType.STRING:
            self.advance()
            expr = StringLiteral(token.value)
        elif token.type == TokenType.BRACKET_OPEN:
            return self.parse_array_literal()
        elif token.type == TokenType.BRACE_OPEN:
            return self.parse_map_literal()
        elif token.type == TokenType.PAREN_OPEN:
            return self.parse_tuple_literal()
        elif token.type == TokenType.IDENTIFIER:
            identifier = token.value
            self.advance()
            self.skip_whitespace()
            if self.current_token().type == TokenType.PAREN_OPEN:
                self.advance()  # skip '('
                args = self.parse_arguments()
                self.expect_token(TokenType.PAREN_CLOSE)
                expr = FunctionCall(identifier, args)
            elif self.current_token().type == TokenType.DOT:
                left = Expression(identifier)
                expr = self.parse_property_access(left)
            else:
                expr = Expression(identifier)
        elif token.type == TokenType.KEYWORD:
            identifier = token.value
            self.advance()
            self.skip_whitespace()
            if self.current_token().type == TokenType.PAREN_OPEN:
                self.advance()  # skip '('
                args = self.parse_arguments()
                self.expect_token(TokenType.PAREN_CLOSE)
                expr = FunctionCall(identifier, args)
            else:
                expr = Expression(identifier)
        else:
            raise SyntaxError(f"Unexpected token: {token} value: '{token.value}' after identifier")

        # Handle array access (chaining allowed)
        while self.current_token().type == TokenType.BRACKET_OPEN:
            self.advance()  # skip '['
            index_expr = self.parse_expression()
            self.expect_token(TokenType.BRACKET_CLOSE)
            expr = ArrayAccess(expr, index_expr)

        return expr

    def parse_property_access(self, left: Expression) -> Expression:
        """Parse property access using dot notation."""
        while self.current_token().type == TokenType.DOT:
            self.advance()  # Skip the dot

            if self.current_token().type != TokenType.IDENTIFIER:
                raise SyntaxError(f"Expected property name after '.', got {self.current_token()}")

            property_name = self.current_token().value
            self.advance()  # Skip property name

            # Check if this is a method call or function call
            if self.current_token().type == TokenType.PAREN_OPEN:
                self.advance()  # Skip opening parenthesis
                args = self.parse_arguments()
                self.expect_token(TokenType.PAREN_CLOSE)
                left = MethodCall(left, property_name, args)
            else:
                # It's a property access
                left = MethodCall(left, property_name, [])

        return left

    def _build_dotted_name_from_expression(self, expr: Expression) -> str:
        """Build a dotted name from an Expression that may contain MethodCalls."""
        if isinstance(expr.expression, str):
            return expr.expression
        elif isinstance(expr.expression, MethodCall):
            return self._build_dotted_name(expr.expression)
        else:
            return str(expr.expression)

    def _build_dotted_name(self, method_call: MethodCall) -> str:
        """Recursively build a dotted name from a chain of MethodCalls."""
        if isinstance(method_call.instance, Expression):
            if isinstance(method_call.instance.expression, str):
                return method_call.instance.expression + "." + method_call.method_name
            elif isinstance(method_call.instance.expression, MethodCall):
                return self._build_dotted_name(method_call.instance.expression) + "." + method_call.method_name
        return method_call.method_name

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
        if self.current_token().type == TokenType.KEYWORD or self.current_token().type == TokenType.IDENTIFIER:
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
            elif type_name == "any":
                return AnyType()
            elif type_name == "matrix":
                self.expect_token(TokenType.BRACKET_OPEN, "[")
                element_type = self.parse_type_annotation()
                self.expect_token(TokenType.BRACKET_CLOSE, "]")
                return MatrixType(element_type)
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
                    if self.current_token().type == TokenType.COMMA:
                        self.advance()  # Skip comma
                self.expect_token(TokenType.BRACKET_CLOSE, "]")
                return TupleType(element_types)
            elif type_name == "chan":
                self.expect_token(TokenType.BRACKET_OPEN, "[")
                element_type = self.parse_type_annotation()
                self.expect_token(TokenType.BRACKET_CLOSE, "]")
                return ChannelType(element_type)
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

        # Initialization is optional
        if self.current_token().type == TokenType.OPERATOR and self.current_token().value == "=":
            self.advance()  # Skip '='
            value = self.parse_expression()
        else:
            # No initialization - use nil as default value
            from ymir.core.types import NilType

            value = Expression(NilType())

        return Assignment(name_token.value, value, var_type)

    def parse_try_except_statement(self) -> TryExceptStatement:
        self.logger.debug("Entering parse_try_except_statement")
        self.advance()  # Skip 'try'
        self.skip_whitespace()

        try_block = self.parse_block()
        except_clauses = []

        # Parse except clauses
        while self.current_token().type == TokenType.KEYWORD and self.current_token().value == "except":
            self.advance()  # Skip 'except'
            self.skip_whitespace()

            exception_type = None
            exception_var = None

            # Check if there's an exception type specified
            if self.current_token().type != TokenType.BRACE_OPEN and self.current_token().type != TokenType.KEYWORD:
                exception_type = self.parse_expression()
                self.skip_whitespace()

            # Check for 'as' keyword to bind exception to a variable
            if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "as":
                self.advance()  # Skip 'as'
                self.skip_whitespace()

                # Ensure we have an identifier for the exception variable
                if self.current_token().type != TokenType.IDENTIFIER:
                    raise SyntaxError(f"Expected identifier after 'as', got {self.current_token()}")

                exception_var = self.current_token().value
                self.advance()  # Skip identifier
                self.skip_whitespace()

            # Now expect the opening brace for the except block
            except_block = self.parse_block()
            except_clauses.append(ExceptClause(except_block, exception_type, exception_var))

        # Parse optional finally clause
        finally_clause = None
        if self.current_token().type == TokenType.KEYWORD and self.current_token().value == "finally":
            self.advance()  # Skip 'finally'
            self.skip_whitespace()
            finally_block = self.parse_block()
            finally_clause = FinallyClause(finally_block)

        return TryExceptStatement(try_block, except_clauses, finally_clause)

    def parse_throw_statement(self) -> ThrowStatement:
        self.logger.debug("Entering parse_throw_statement")
        self.advance()  # Skip 'throw'
        self.skip_whitespace()

        expression = self.parse_expression()

        # Consume newline after throw statement
        if self.current_token().type == TokenType.NEWLINE:
            self.advance()

        return ThrowStatement(expression)

    def parse_exception_def(self) -> ExceptionDef:
        self.logger.debug("Entering parse_exception_def")
        self.advance()  # Skip 'exception'
        self.skip_whitespace()

        name = self.current_token().value
        self.expect_token(TokenType.IDENTIFIER)
        self.skip_whitespace()

        base_class = None
        if self.current_token().type == TokenType.COLON:
            self.advance()  # Skip ':'
            self.skip_whitespace()

            base_class = self.current_token().value
            self.expect_token(TokenType.IDENTIFIER)
            self.skip_whitespace()

        self.expect_token(TokenType.BRACE_OPEN)
        methods, members = self.parse_class_members()
        self.expect_token(TokenType.BRACE_CLOSE)

        return ExceptionDef(name, methods, members, base_class)

    def parse_function_call(self, function_name: str) -> FunctionCall:
        """Parse a function call expression."""
        self.advance()  # Skip opening parenthesis
        args = []

        # Parse arguments if any
        if self.current_token().type != TokenType.PAREN_CLOSE:
            args.append(self.parse_expression())
            while self.current_token().type == TokenType.COMMA:
                self.advance()  # Skip comma
                args.append(self.parse_expression())

        self.expect_token(TokenType.PAREN_CLOSE)
        return FunctionCall(function_name, args)

    def parse_binary_operators(self, token):
        """Parse binary operators with precedence."""
        self.skip_whitespace()

        # Handle type annotations which might look like binary operators
        if token.type == TokenType.COLON:
            self.advance()  # Skip colon
            return self.parse_type_annotation()

        # Handle normal binary operators
        if token.type == TokenType.OPERATOR:
            # Get operator precedence
            precedence = self.get_operator_precedence(token.value)
            # Continue with binary operator parsing
            return precedence

        return None  # Not a binary operator

    def peek_token(self) -> Token:
        if self.pos + 1 >= len(self.tokens):
            return Token(TokenType.EOF, "", line=-1, column=-1)
        return self.tokens[self.pos + 1]

    def parse_spawn_statement(self) -> SpawnStatement:
        """Parse a spawn statement: spawn functionCall()"""
        self.logger.debug("Entering parse_spawn_statement")
        self.advance()  # Skip 'spawn'
        self.skip_whitespace()

        # Parse the function call
        if self.current_token().type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected function call after 'spawn', got {self.current_token()}")

        func_name = self.current_token().value
        self.advance()

        if self.current_token().type != TokenType.PAREN_OPEN:
            raise SyntaxError(f"Expected '(' after function name in spawn, got {self.current_token()}")

        call = self.parse_function_call(func_name)
        return SpawnStatement(call)
