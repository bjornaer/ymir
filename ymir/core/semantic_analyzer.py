from typing import List, Union

from ymir.core.ast import (
    ArrayLiteral,
    Assignment,
    ASTNode,
    BinaryOp,
    ClassDef,
    ExceptClause,
    ExceptionDef,
    ExportDef,
    Expression,
    FinallyClause,
    FunctionCall,
    FunctionDef,
    IfStatement,
    ImportDef,
    MapLiteral,
    MethodCall,
    ModuleDef,
    ReturnStatement,
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
        elif isinstance(node, BinaryOp):
            self.visit_binary_op(node)
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
        elif isinstance(node, ReturnStatement):
            self.visit_return_statement(node)
        elif isinstance(node, ImportDef):
            self.visit_import_def(node)
        elif isinstance(node, FunctionCall):
            self.visit_function_call(node)
        elif isinstance(node, ModuleDef):
            self.visit_module_def(node)
        elif isinstance(node, ExportDef):
            self.visit_export_def(node)
        elif isinstance(node, MethodCall):
            self.visit_method_call(node)
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
        if isinstance(node, Expression):
            if isinstance(node.expression, str):
                if not self.symbol_table.lookup(node.expression):
                    self.symbol_table.define(node.expression, "variable")
                return self.symbol_table.lookup(node.expression)
        elif isinstance(node, StringLiteral):
            return "string"
        elif isinstance(node, BinaryOp):
            left_type = self.visit_expression(node.left)
            self.visit_expression(node.right)
            return left_type
        elif isinstance(node, FunctionCall):
            for arg in node.args:
                self.visit_expression(arg)
            return "any"
        return None

    def visit_binary_op(self, node: BinaryOp) -> None:
        self.visit(node.left)
        self.visit(node.right)

    def visit_import_def(self, node: ImportDef) -> None:
        self.symbol_table.define(node.module_name, "module")

    def visit_function_call(self, node: FunctionCall) -> None:
        if not self.symbol_table.lookup(node.func_name):
            self.symbol_table.define(node.func_name, "function")

        for arg in node.args:
            self.visit(arg)

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
        if isinstance(node.expression, Expression):
            self.visit_expression(node.expression)
        elif isinstance(node.expression, StringLiteral):
            self.visit_string_literal(node.expression)
        elif isinstance(node.expression, FunctionCall):
            self.visit_function_call(node.expression)
        else:
            self.visit(node.expression)

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

    def visit_return_statement(self, node: ReturnStatement) -> None:
        if node.expression:
            self.visit(node.expression)

    def visit_module_def(self, node: ModuleDef) -> None:
        for stmt in node.body:
            self.visit(stmt)

    def visit_export_def(self, node: ExportDef) -> None:
        if hasattr(node, "body") and node.body:
            for stmt in node.body:
                self.visit(stmt)

    def visit_method_call(self, node: MethodCall) -> None:
        # Implementation of visit_method_call method
        pass
