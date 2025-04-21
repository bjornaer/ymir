from ymir.core.ast import (
    ArrayLiteral,
    Assignment,
    BinaryOp,
    ClassDef,
    ClassInstance,
    ExceptionDef,
    Expression,
    FunctionCall,
    FunctionDef,
    IfStatement,
    MapLiteral,
    MethodCall,
    ReturnStatement,
    StringLiteral,
    ThrowStatement,
    TryExceptStatement,
    TupleLiteral,
    WhileStatement,
)
from ymir.core.types import (
    ArrayType,
    BoolType,
    FloatType,
    FunctionType,
    IntType,
    MapType,
    StringType,
    TupleType,
    Type,
)
from ymir.logging import get_logger


class TypeChecker:
    def __init__(self, verbosity: str = "INFO"):
        self.symbol_table = {}
        self.logger = get_logger("ymir.core", verbosity)

    def check(self, ast):
        for node in ast:
            self.visit(node)

    def visit(self, node):
        if isinstance(node, FunctionDef):
            self.visit_function_def(node)
        elif isinstance(node, ClassDef):
            self.visit_class_def(node)
        elif isinstance(node, IfStatement):
            self.visit_if_statement(node)
        elif isinstance(node, WhileStatement):
            self.visit_while_statement(node)
        elif isinstance(node, Expression):
            return self.visit_expression(node)
        elif isinstance(node, BinaryOp):
            return self.visit_binary_op(node)
        elif isinstance(node, Assignment):
            return self.visit_assignment(node)
        elif isinstance(node, FunctionCall):
            return self.visit_function_call(node)
        elif isinstance(node, ArrayLiteral):
            return self.visit_array_literal(node)
        elif isinstance(node, StringLiteral):
            return self.visit_string_literal(node)
        elif isinstance(node, ClassInstance):
            return self.visit_class_instance(node)
        elif isinstance(node, MethodCall):
            return self.visit_method_call(node)
        elif isinstance(node, TupleLiteral):
            return self.visit_tuple_literal(node)
        elif isinstance(node, MapLiteral):
            return self.visit_dictionary_literal(node)
        elif isinstance(node, TryExceptStatement):
            return self.visit_try_except_statement(node)
        elif isinstance(node, ThrowStatement):
            return self.visit_throw_statement(node)
        elif isinstance(node, ExceptionDef):
            return self.visit_exception_def(node)
        elif isinstance(node, ReturnStatement):
            return self.visit_return_statement(node)
        else:
            raise TypeError(f"Unknown AST node type: {type(node)}")

    def visit_function_def(self, node: FunctionDef):
        param_types = [self.visit_type_annotation(t) for t in node.param_types]
        return_type = self.visit_type_annotation(node.return_type)
        self.symbol_table[node.name] = FunctionType(param_types, return_type)
        for statement in node.body:
            self.visit(statement)

    def visit_class_def(self, node: ClassDef):
        self.symbol_table[node.name] = node
        if node.base_class:
            base_class = self.symbol_table.get(node.base_class)
            if not base_class:
                raise NameError(f"Undefined base class: {node.base_class}")
            if not isinstance(base_class, ClassDef):
                raise TypeError(f"{node.base_class} is not a class")

    def visit_if_statement(self, node: IfStatement):
        condition_type = self.visit_expression(node.condition)
        if condition_type != BoolType():
            raise TypeError(f"Condition must be a boolean, got {condition_type}")
        for statement in node.then_body:
            self.visit(statement)
        if node.else_body:
            for statement in node.else_body:
                self.visit(statement)

    def visit_while_statement(self, node: WhileStatement):
        condition_type = self.visit_expression(node.condition)
        if condition_type != BoolType():
            raise TypeError(f"Condition must be a boolean, got {condition_type}")
        for statement in node.body:
            self.visit(statement)

    def visit_expression(self, node: Expression):
        if isinstance(node.expression, int):
            return IntType()
        elif isinstance(node.expression, str):
            if node.expression in self.symbol_table:
                return self.symbol_table[node.expression]
            raise NameError(f"Undefined variable: {node.expression}")
        return None

    def visit_binary_op(self, node: BinaryOp):
        left_type = self.visit_expression(node.left)
        right_type = self.visit_expression(node.right)
        if left_type != right_type:
            raise TypeError(f"Type mismatch: {left_type} {node.operator} {right_type}")
        return left_type

    def visit_assignment(self, node: Assignment):
        value_type = self.visit_expression(node.value)
        if node.type and value_type != node.type:
            raise TypeError(f"Type mismatch: expected {node.type}, got {value_type}")
        self.symbol_table[node.target] = value_type

    def visit_function_call(self, node: FunctionCall):
        func = self.symbol_table.get(node.func_name)
        if not func:
            raise NameError(f"Undefined function: {node.func_name}")
        if not isinstance(func, FunctionType):
            raise TypeError(f"{node.func_name} is not a function")
        if len(func.param_types) != len(node.args):
            raise TypeError(f"Argument count mismatch: expected {len(func.param_types)}, got {len(node.args)}")
        for arg, param_type in zip(node.args, func.param_types):
            arg_type = self.visit_expression(arg)
            if arg_type != param_type:
                raise TypeError(f"Argument type mismatch: expected {param_type}, got {arg_type}")
        return func.return_type

    def visit_array_literal(self, node: ArrayLiteral):
        element_types = [self.visit_expression(element) for element in node.elements]
        if len(set(element_types)) != 1:
            raise TypeError("Array elements must have the same type")
        return ArrayType(element_types[0])

    def visit_string_literal(self, node: StringLiteral):
        return StringType()

    def visit_tuple_literal(self, node: TupleLiteral):
        element_types = [self.visit_expression(element) for element in node.elements]
        return TupleType(element_types)

    def visit_dictionary_literal(self, node: MapLiteral):
        key_types = set(self.visit_expression(key) for key in node.pairs.keys())
        value_types = set(self.visit_expression(value) for value in node.pairs.values())
        if len(key_types) != 1 or len(value_types) != 1:
            raise TypeError("Dictionary keys and values must have the same type")
        return MapType(list(key_types)[0], list(value_types)[0])

    def visit_class_instance(self, node: ClassInstance):
        class_def = self.symbol_table.get(node.class_name)
        if not class_def:
            raise NameError(f"Undefined class: {node.class_name}")
        return class_def

    def visit_method_call(self, node: MethodCall):
        instance = self.symbol_table.get(node.instance)
        if not instance:
            raise NameError(f"Undefined instance: {node.instance}")
        method = instance.get(node.method_name)
        if not method:
            raise NameError(f"Undefined method: {node.method_name}")
        if not isinstance(method, FunctionType):
            raise TypeError(f"{node.method_name} is not a method")
        if len(method.param_types) != len(node.args):
            raise TypeError(f"Argument count mismatch: expected {len(method.param_types)}, got {len(node.args)}")
        for arg, param_type in zip(node.args, method.param_types):
            arg_type = self.visit_expression(arg)
            if arg_type != param_type:
                raise TypeError(f"Argument type mismatch: expected {param_type}, got {arg_type}")
        return method.return_type

    def visit_type_annotation(self, node: Type):
        if isinstance(node, IntType):
            return IntType()
        elif isinstance(node, FloatType):
            return FloatType()
        elif isinstance(node, StringType):
            return StringType()
        elif isinstance(node, BoolType):
            return BoolType()
        elif isinstance(node, ArrayType):
            return ArrayType(self.visit_type_annotation(node.element_type))
        elif isinstance(node, MapType):
            return MapType(self.visit_type_annotation(node.key_type), self.visit_type_annotation(node.value_type))
        elif isinstance(node, TupleType):
            return TupleType([self.visit_type_annotation(t) for t in node.element_types])
        elif isinstance(node, FunctionType):
            param_types = [self.visit_type_annotation(t) for t in node.param_types]
            return FunctionType(param_types, self.visit_type_annotation(node.return_type))
        return None

    def visit_try_except_statement(self, node: TryExceptStatement):
        # Type check the try block
        for statement in node.try_block:
            self.visit(statement)

        # Type check each except clause
        for except_clause in node.except_clauses:
            if except_clause.exception_type:
                exception_type = self.visit_expression(except_clause.exception_type)

                # Verify the exception type is a valid exception class
                if exception_type not in self.symbol_table or not self.is_exception_type(exception_type):
                    raise TypeError(f"Invalid exception type: {exception_type}")

            # Type check the except block
            for statement in except_clause.except_block:
                self.visit(statement)

        # Type check the finally clause if present
        if node.finally_clause:
            for statement in node.finally_clause.finally_block:
                self.visit(statement)

    def visit_throw_statement(self, node: ThrowStatement):
        # Type check the expression being thrown
        expr_type = self.visit_expression(node.expression)

        # Verify the expression is an exception or can be converted to one
        if not self.is_exception_type(expr_type) and not self.can_convert_to_exception(expr_type):
            raise TypeError(f"Cannot throw non-exception type: {expr_type}")

    def visit_exception_def(self, node: ExceptionDef):
        # Register exception in the symbol table
        self.symbol_table[node.name] = node

        # If there's a base class, verify it's a valid exception
        if node.base_class:
            base_class = self.symbol_table.get(node.base_class)
            if not base_class:
                raise NameError(f"Undefined base exception: {node.base_class}")
            if not self.is_exception_type(base_class):
                raise TypeError(f"{node.base_class} is not an exception class")

        # Type check methods and member initializations
        for method in node.methods:
            self.visit(method)

    def is_exception_type(self, type_obj):
        """Check if a type is an exception or inherits from Exception."""
        if isinstance(type_obj, ExceptionDef):
            return True

        # Check inheritance chain
        current = type_obj
        while hasattr(current, "base_class") and current.base_class:
            base_name = current.base_class
            base = self.symbol_table.get(base_name)
            if not base:
                return False
            if isinstance(base, ExceptionDef):
                return True
            current = base

        return False

    def can_convert_to_exception(self, type_obj):
        """Check if a type can be converted to an exception (e.g., string)."""
        # For now, let's just allow strings to be automatically wrapped in exceptions
        # This could be extended to support more types in the future
        return type_obj == StringType()

    def visit_return_statement(self, node: ReturnStatement):
        """Type check a return statement."""
        if node.expression:
            return_type = self.visit_expression(node.expression)
            # Here you would check if return type matches function's return type
            return return_type
        return None
