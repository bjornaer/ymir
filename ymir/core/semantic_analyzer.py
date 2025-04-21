from typing import List, Union

from ymir.core.ast import (
    ArrayLiteral,
    Assignment,
    ASTNode,
    BinaryOp,
    ClassDef,
    ExceptClause,
    ExceptionDef,
    Expression,
    FinallyClause,
    FunctionCall,
    FunctionDef,
    IfStatement,
    MapLiteral,
    StringLiteral,
    ThrowStatement,
    TryExceptStatement,
    TupleLiteral,
    WhileStatement,
)
from ymir.core.symbol_table import SymbolTable
from ymir.logging import get_logger


class SemanticAnalyzer:
    def __init__(self, verbosity: str = "INFO"):
        self.symbol_table = SymbolTable()
        self.logger = get_logger("ymir.core", verbosity)

    def analyze(self, ast: List[ASTNode]) -> None:
        for node in ast:
            self.visit(node)

    def visit(self, node: ASTNode) -> None:
        if isinstance(node, FunctionDef):
            self.visit_function_def(node)
        elif isinstance(node, ClassDef):
            self.visit_class_def(node)
        elif isinstance(node, IfStatement):
            self.visit_if_statement(node)
        elif isinstance(node, WhileStatement):
            self.visit_while_statement(node)
        elif isinstance(node, Assignment):
            self.visit_assignment(node)
        elif isinstance(node, Expression):
            self.visit_expression(node)
        elif isinstance(node, ArrayLiteral):
            self.visit_array_literal(node)
        elif isinstance(node, StringLiteral):
            self.visit_string_literal(node)
        elif isinstance(node, TupleLiteral):
            self.visit_tuple_literal(node)
        elif isinstance(node, MapLiteral):
            self.visit_dictionary_literal(node)
        elif isinstance(node, TryExceptStatement):
            self.visit_try_except_statement(node)
        elif isinstance(node, ThrowStatement):
            self.visit_throw_statement(node)
        elif isinstance(node, ExceptionDef):
            self.visit_exception_def(node)
        elif isinstance(node, FinallyClause):
            self.visit_finally_clause(node)
        elif isinstance(node, ExceptClause):
            self.visit_except_clause(node)
        else:
            raise TypeError(f"Unknown AST node type: {type(node)}")

    def visit_function_def(self, node: FunctionDef) -> None:
        self.symbol_table.define(node.name, "function")
        self.symbol_table.enter_scope()
        for param in node.params:
            self.symbol_table.define(param, "variable")
        for statement in node.body:
            self.visit(statement)
        self.symbol_table.exit_scope()

    def visit_class_def(self, node: ClassDef) -> None:
        self.symbol_table.define(node.name, "class")
        self.symbol_table.enter_scope()
        for method in node.methods:
            self.visit(method)
        self.symbol_table.exit_scope()

    def visit_if_statement(self, node: IfStatement) -> None:
        self.visit_expression(node.condition)
        self.symbol_table.enter_scope()
        for statement in node.then_body:
            self.visit(statement)
        self.symbol_table.exit_scope()
        if node.else_body:
            self.symbol_table.enter_scope()
            for statement in node.else_body:
                self.visit(statement)
            self.symbol_table.exit_scope()

    def visit_while_statement(self, node: WhileStatement) -> None:
        self.visit_expression(node.condition)
        self.symbol_table.enter_scope()
        for statement in node.body:
            self.visit(statement)
        self.symbol_table.exit_scope()

    def visit_assignment(self, node: Assignment) -> None:
        value_type = self.visit_expression(node.value)
        self.symbol_table.define(node.target, value_type)

    def visit_expression(self, node: Expression) -> Union[str, None]:
        if isinstance(node.expression, str):
            if not self.symbol_table.lookup(node.expression):
                raise NameError(f"Undefined variable: {node.expression}")
            return self.symbol_table.lookup(node.expression)
        elif isinstance(node, BinaryOp):
            left_type = self.visit_expression(node.left)
            right_type = self.visit_expression(node.right)
            if left_type != right_type:
                raise TypeError("Type mismatch in binary operation")
            return left_type
        elif isinstance(node, FunctionCall):
            func = self.symbol_table.lookup(node.func_name)
            if not func:
                raise NameError(f"Undefined function: {node.func_name}")
            for arg in node.args:
                self.visit_expression(arg)
            return func
        return None

    def visit_array_literal(self, node: ArrayLiteral) -> List[str]:
        return [self.visit_expression(element) for element in node.elements]

    def visit_string_literal(self, node: StringLiteral) -> str:
        return "string"

    def visit_tuple_literal(self, node: TupleLiteral) -> tuple:
        return tuple(self.visit_expression(element) for element in node.elements)

    def visit_dictionary_literal(self, node: MapLiteral) -> dict:
        return {self.visit_expression(key): self.visit_expression(value) for key, value in node.pairs.items()}

    def visit_try_except_statement(self, node: TryExceptStatement) -> None:
        self.symbol_table.enter_scope()
        for statement in node.try_block:
            self.visit(statement)
        self.symbol_table.exit_scope()

        for except_clause in node.except_clauses:
            if except_clause.exception_type:
                self.visit_expression(except_clause.exception_type)

            self.symbol_table.enter_scope()
            if except_clause.exception_var:
                self.symbol_table.define(except_clause.exception_var, "exception")

            for statement in except_clause.except_block:
                self.visit(statement)
            self.symbol_table.exit_scope()

        if node.finally_clause:
            self.symbol_table.enter_scope()
            for statement in node.finally_clause.finally_block:
                self.visit(statement)
            self.symbol_table.exit_scope()

    def visit_throw_statement(self, node: ThrowStatement) -> None:
        self.visit_expression(node.expression)

    def visit_exception_def(self, node: ExceptionDef) -> None:
        self.symbol_table.define(node.name, "exception")

        self.symbol_table.enter_scope()

        for method in node.methods:
            self.visit(method)

        self.symbol_table.exit_scope()

    def visit_finally_clause(self, node: FinallyClause) -> None:
        for statement in node.finally_block:
            self.visit(statement)

    def visit_except_clause(self, node: ExceptClause) -> None:
        for statement in node.except_block:
            self.visit(statement)
