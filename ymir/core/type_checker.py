from ymir.core.ast import (
    ArrayLiteral,
    Assignment,
    BinaryOp,
    ClassDef,
    ClassInstance,
    ExceptionDef,
    ExportDef,
    Expression,
    FunctionCall,
    FunctionDef,
    IfStatement,
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
        elif isinstance(node, ModuleDef):
            return self.visit_module_def(node)
        elif type(node).__name__ == "ImportDef":
            # Handle import of standard library modules
            import_name = getattr(node, "module_name", None)
            if import_name:
                import os

                from ymir.core.lexer import Lexer
                from ymir.core.parser import Parser

                stdlib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stdlib")
                module_path = os.path.join(stdlib_path, *import_name.split(".")) + ".ymr"
                if os.path.exists(module_path):
                    with open(module_path, "r") as f:
                        source = f.read()
                    tokens = Lexer(source).tokenize()
                    ast = Parser(tokens).parse()
                    # Build a namespace dict for the module's exports
                    module_namespace = {}
                    for mod_node in ast:
                        if isinstance(mod_node, ModuleDef):
                            for stmt in mod_node.body:
                                if isinstance(stmt, ExportDef):
                                    export_value = stmt.value if hasattr(stmt, "value") else stmt
                                    # If the export is a class or exception, build a method namespace
                                    if isinstance(export_value, (ClassDef, ExceptionDef)):
                                        method_namespace = {}
                                        for method in getattr(export_value, "methods", []):
                                            # Register the method as a FunctionType
                                            param_types = [
                                                self.visit_type_annotation(t)
                                                for t in getattr(method, "param_types", [])
                                            ]
                                            return_type = self.visit_type_annotation(
                                                getattr(method, "return_type", None)
                                            )
                                            method_namespace[method.name] = FunctionType(param_types, return_type)
                                        module_namespace[stmt.name] = method_namespace
                                    else:
                                        module_namespace[stmt.name] = export_value
                                    # Also visit the export to register types/classes
                                    self.visit(stmt)
                    self.symbol_table[import_name] = module_namespace
            return None
        elif isinstance(node, ExportDef):
            return self.visit_export_def(node)
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

    def visit_expression(self, node):
        # Handle Expression node
        if isinstance(node, Expression):
            print(f"DEBUG: visit_expression - node.expression: {node.expression}, type: {type(node.expression)}")
            if isinstance(node.expression, int):
                return IntType()
            elif isinstance(node.expression, str):
                # Handle attribute access like e.message or exceptions.ValueError
                if "." in node.expression:
                    var, attr = node.expression.split(".", 1)
                    print(f"DEBUG: Attribute access - var: {var}, attr: {attr}")
                    if var in self.symbol_table:
                        obj = self.symbol_table[var]
                        # If obj is a module namespace, look up attr inside it
                        if isinstance(obj, dict) and attr in obj:
                            return obj[attr]
                        if hasattr(obj, attr):
                            return StringType()
                    # If attribute is 'message', assume it's a string for exception classes
                    if attr == "message":
                        return StringType()
                    # If variable is 'self', assume it's an exception object with message attribute
                    if var == "self":
                        return StringType()
                    raise NameError(f"Undefined attribute: {attr} on {var}")
                if node.expression in self.symbol_table:
                    return self.symbol_table[node.expression]
                # If the variable itself is 'message', assume it's a string (for exception class bodies)
                if node.expression == "message":
                    return StringType()
                # If the variable is 'self', return a dummy object type
                if node.expression == "self":

                    class DummySelf:
                        message = ""

                    return DummySelf()
                print(f"DEBUG: Undefined variable: {node.expression}")
                raise NameError(f"Undefined variable: {node.expression}")
            elif isinstance(node.expression, MethodCall):
                # Handle method calls like self.message
                return self.visit_method_call(node.expression)
            # Add more cases as needed for Expression
            return None
        # Handle StringLiteral node
        elif isinstance(node, StringLiteral):
            return StringType()
        # Handle other literal types (add as needed)
        # elif isinstance(node, IntLiteral):
        #     return IntType()
        # elif isinstance(node, FloatLiteral):
        #     return FloatType()
        # elif isinstance(node, BoolLiteral):
        #     return BoolType()
        # Add more literal types as your AST defines them
        return None

    def visit_binary_op(self, node: BinaryOp):
        # Only type check valid binary operators, not assignment
        if node.operator == "=":
            raise TypeError("Assignment '=' should not be handled as a binary operation. Use visit_assignment instead.")
        left_type = self.visit_expression(node.left)
        right_type = self.visit_expression(node.right)
        print(f"DEBUG: BinaryOp {node.operator} - left: {left_type} ({node.left}), right: {right_type} ({node.right})")
        if left_type != right_type:
            raise TypeError(f"Type mismatch: {left_type} {node.operator} {right_type}")
        return left_type

    def visit_assignment(self, node: Assignment):
        value_type = self.visit_expression(node.value)
        node_type = getattr(node, "type", None)
        if node_type and value_type != node_type:
            raise TypeError(f"Type mismatch: expected {node_type}, got {value_type}")

        # Handle different target types
        if isinstance(node.target, str):
            # Simple variable assignment
            self.symbol_table[node.target] = value_type
        elif isinstance(node.target, Expression):
            # Property assignment (e.g., self.message = value)
            # For now, just type check the target expression
            self.visit_expression(node.target)
            # In a real implementation, you might want to validate that the target
            # can be assigned to (e.g., it's a writable property)
            # For now, we'll just accept it
            pass
        else:
            raise TypeError(f"Unsupported assignment target type: {type(node.target)}")

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
        if isinstance(node.instance, Expression):
            instance_name = node.instance.expression
        else:
            instance_name = node.instance

        instance = self.symbol_table.get(instance_name)
        if instance is None and "." in instance_name:
            var, attr = instance_name.split(".", 1)
            if var in self.symbol_table:
                obj = self.symbol_table[var]
                if isinstance(obj, dict) and attr in obj:
                    instance = obj[attr]
        if not instance:
            raise NameError(f"Undefined instance: {instance_name}")

        if instance_name == "self" and node.method_name == "message":
            return StringType()

        # If instance is a dummy with _ymir_type, use that for method lookup
        method_namespace = getattr(instance, "_ymir_type", None)
        if method_namespace and isinstance(method_namespace, dict):
            method = method_namespace.get(node.method_name)
        elif isinstance(instance, dict):
            method = instance.get(node.method_name)
        else:
            method = getattr(instance, node.method_name, None) if hasattr(instance, node.method_name) else None
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
        for stmt in node.try_block:
            self.visit(stmt)
        for except_clause in node.except_clauses:
            if hasattr(except_clause, "exception_var") and except_clause.exception_var:
                exception_type = None
                if except_clause.exception_type is not None:
                    et = except_clause.exception_type
                    # Handle FunctionCall, Expression, or string
                    if hasattr(et, "expression"):
                        expr = et.expression
                        if isinstance(expr, str):
                            type_expr = expr
                        elif hasattr(expr, "func_name"):
                            type_expr = expr.func_name
                        else:
                            type_expr = str(expr)
                    elif hasattr(et, "func_name"):
                        type_expr = et.func_name
                    elif isinstance(et, str):
                        type_expr = et
                    else:
                        type_expr = str(et)
                    if "." in type_expr:
                        var, attr = type_expr.split(".", 1)
                        if var in self.symbol_table:
                            mod = self.symbol_table[var]
                            if isinstance(mod, dict) and attr in mod:
                                exception_type = mod[attr]
                    else:
                        exception_type = self.symbol_table.get(type_expr)
                if isinstance(exception_type, dict):

                    class DummyInstance:
                        def __init__(self):
                            self._ymir_type = exception_type

                        message = ""

                        def __str__(self):
                            return self.message

                    self.symbol_table[except_clause.exception_var] = DummyInstance()
                else:

                    class DummyException:
                        message = ""

                        def __str__(self):
                            return self.message

                    self.symbol_table[except_clause.exception_var] = DummyException()
                for stmt in except_clause.except_block:
                    self.visit(stmt)
                del self.symbol_table[except_clause.exception_var]
            else:
                for stmt in except_clause.except_block:
                    self.visit(stmt)
        if node.finally_clause:
            for stmt in node.finally_clause.finally_block:
                self.visit(stmt)

    def visit_throw_statement(self, node: ThrowStatement):
        # Type check the expression being thrown
        expr_type = self.visit_expression(node.expression)
        # Allow throwing strings, any object/class with a 'message' attribute, or None (for now)
        if expr_type is None:
            return expr_type
        if not self.is_exception_type(expr_type) and not self.can_convert_to_exception(expr_type):
            if not isinstance(expr_type, StringType):
                # If expr_type is a class or object with a 'message' attribute, allow it
                if hasattr(expr_type, "message"):
                    return expr_type
                raise TypeError(f"Cannot throw non-exception type: {expr_type}")
        return expr_type

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
            # Add 'self' to symbol table for method body
            class DummySelf:
                message = ""

                def __init__(self):
                    self.message = ""

            self.symbol_table["self"] = DummySelf()
            self.visit(method)
            del self.symbol_table["self"]

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

    def visit_module_def(self, node):
        for stmt in node.body:
            self.visit(stmt)
        return None

    def visit_export_def(self, node):
        if hasattr(node, "body") and node.body:
            for stmt in node.body:
                self.visit(stmt)
        return None
