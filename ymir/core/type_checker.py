from ymir.core.ast import (
    ArrayAccess,
    ArrayLiteral,
    Assignment,
    BinaryOp,
    Break,
    ChannelReceive,
    ChannelSend,
    ClassDef,
    ClassInstance,
    Continue,
    ExceptionDef,
    ExportDef,
    Expression,
    ForCStyleLoop,
    ForInLoop,
    FunctionCall,
    FunctionDef,
    IfStatement,
    MapLiteral,
    MethodCall,
    ModuleDef,
    ReturnStatement,
    SelectCase,
    SelectStatement,
    SpawnStatement,
    StringLiteral,
    ThrowStatement,
    TryExceptStatement,
    TupleLiteral,
    UnaryOp,
    WhileStatement,
)
from ymir.core.types import (
    AnyType,
    ArrayType,
    BoolType,
    FloatType,
    FunctionType,
    IntType,
    MapType,
    MatrixType,
    StringType,
    TupleType,
    Type,
)
from ymir.logging import get_logger


class TypeChecker:
    def __init__(self, verbosity: str = "INFO"):
        self.symbol_table = {}
        self.logger = get_logger("ymir.core", verbosity)

        # Register builtin functions
        self._register_builtin_functions()

    def _register_builtin_functions(self):
        """Register common builtin functions in the symbol table."""
        # Register the built-in Exception class
        # Create a dummy ExceptionDef for the base Exception class
        base_exception = ExceptionDef("Exception", None, [], [])
        self.symbol_table["Exception"] = base_exception

        # print function: takes any number of arguments, returns void
        self.symbol_table["print"] = FunctionType([AnyType()], None)  # special case: 'any' and variadic

        # str function: takes one argument of any type, returns string
        self.symbol_table["str"] = FunctionType([AnyType()], StringType())

        # len function: takes array/string, returns int
        self.symbol_table["len"] = FunctionType([AnyType()], IntType())

        # Common math functions
        self.symbol_table["sqrt"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["sin"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["cos"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["tan"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["pow"] = FunctionType([FloatType(), FloatType()], FloatType())

        # More math functions
        self.symbol_table["abs"] = FunctionType([AnyType()], FloatType())  # Can take int or float
        self.symbol_table["round"] = FunctionType([AnyType()], IntType())  # Can take int or float, returns int
        self.symbol_table["min"] = FunctionType([AnyType()], AnyType())  # Variadic
        self.symbol_table["max"] = FunctionType([AnyType()], AnyType())  # Variadic
        self.symbol_table["ceil"] = FunctionType([FloatType()], IntType())
        self.symbol_table["floor"] = FunctionType([FloatType()], IntType())
        self.symbol_table["fabs"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["factorial"] = FunctionType([IntType()], IntType())
        self.symbol_table["fmod"] = FunctionType([FloatType(), FloatType()], FloatType())
        self.symbol_table["exp"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["log"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["log10"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["log2"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["degrees"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["radians"] = FunctionType([FloatType()], FloatType())
        self.symbol_table["gcd"] = FunctionType([IntType(), IntType()], IntType())

        # String functions
        self.symbol_table["strlen"] = FunctionType([StringType()], IntType())
        self.symbol_table["strcmp"] = FunctionType([StringType(), StringType()], IntType())
        self.symbol_table["strcat"] = FunctionType([StringType(), StringType()], StringType())

        # Networking functions
        self.symbol_table["socket"] = FunctionType([IntType(), IntType(), IntType()], AnyType())
        self.symbol_table["connect"] = FunctionType([AnyType(), StringType(), IntType()], IntType())
        self.symbol_table["send"] = FunctionType([AnyType(), StringType(), IntType()], IntType())
        self.symbol_table["recv"] = FunctionType([AnyType(), IntType()], AnyType())
        self.symbol_table["close"] = FunctionType([AnyType()], IntType())

        # Networking constants
        self.symbol_table["AF_INET"] = IntType()
        self.symbol_table["SOCK_STREAM"] = IntType()

        # Memory management functions
        self.symbol_table["allocate"] = FunctionType([IntType()], AnyType())
        self.symbol_table["retain"] = FunctionType([AnyType()], None)
        self.symbol_table["release"] = FunctionType([AnyType()], None)

        # Panic function
        self.symbol_table["panic"] = FunctionType([AnyType()], None)

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
        elif isinstance(node, ForInLoop):
            self.visit_for_in_loop(node)
        elif isinstance(node, ForCStyleLoop):
            self.visit_for_cstyle_loop(node)
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
        elif isinstance(node, UnaryOp):
            return self.visit_unary_op(node)
        elif isinstance(node, Break):
            pass  # Break statements don't need type checking
        elif isinstance(node, Continue):
            pass  # Continue statements don't need type checking
        elif isinstance(node, SpawnStatement):
            return self.visit_spawn_statement(node)
        elif isinstance(node, ChannelSend):
            return self.visit_channel_send(node)
        elif isinstance(node, ChannelReceive):
            return self.visit_channel_receive(node)
        elif isinstance(node, SelectStatement):
            return self.visit_select_statement(node)
        elif isinstance(node, SelectCase):
            return self.visit_select_case(node)
        elif isinstance(node, ArrayAccess):
            return self.visit_array_access(node)
        else:
            raise TypeError(f"Unknown AST node type: {type(node)}")

    def visit_function_def(self, node: FunctionDef):
        # Register the function in the symbol table first
        param_types = [self.visit_type_annotation(t) for t in node.param_types]
        return_type = self.visit_type_annotation(node.return_type) if node.return_type else None
        self.symbol_table[node.name] = FunctionType(param_types, return_type)

        # Save current symbol table to restore after checking
        prev_symbol_table = self.symbol_table.copy()
        # Add parameters to symbol table
        for param, param_type in zip(node.params, node.param_types):
            self.symbol_table[param] = param_type
        # Type check the body
        for statement in node.body:
            self.visit(statement)
        # Restore previous symbol table
        self.symbol_table = prev_symbol_table

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
        if not isinstance(condition_type, BoolType):
            raise TypeError(f"Condition must be a boolean, got {condition_type}")
        for statement in node.then_body:
            self.visit(statement)
        if node.else_body:
            for statement in node.else_body:
                self.visit(statement)

    def visit_while_statement(self, node: WhileStatement):
        condition_type = self.visit_expression(node.condition)
        if not isinstance(condition_type, BoolType):
            raise TypeError(f"Condition must be a boolean, got {condition_type}")
        for statement in node.body:
            self.visit(statement)

    def visit_for_in_loop(self, node: ForInLoop):
        # Type check the iterable
        iterable_type = self.visit_expression(node.iterable)

        # Add the loop variable to the symbol table
        # For now, assume it's the element type of the array
        if isinstance(iterable_type, ArrayType):
            self.symbol_table[node.var] = iterable_type.element_type
        else:
            # If it's not an array type, just use AnyType
            self.symbol_table[node.var] = AnyType()

        # Type check the body
        for statement in node.body:
            self.visit(statement)

        # Remove the loop variable from the symbol table
        if node.var in self.symbol_table:
            del self.symbol_table[node.var]

    def visit_for_cstyle_loop(self, node: ForCStyleLoop):
        # Type check the initialization
        if node.init:
            self.visit(node.init)

        # Type check the condition
        if node.condition:
            condition_type = self.visit_expression(node.condition)
            if not isinstance(condition_type, BoolType):
                raise TypeError(f"For loop condition must be a boolean, got {condition_type}")

        # Type check the increment (it's typically an assignment or expression)
        if node.increment:
            self.visit(node.increment)

        # Type check the body
        for statement in node.body:
            self.visit(statement)

    def visit_expression(self, node):
        # Handle Expression node
        if isinstance(node, Expression):
            if isinstance(node.expression, int):
                return IntType()
            elif isinstance(node.expression, str):
                # Handle attribute access like e.message or exceptions.ValueError
                if "." in node.expression:
                    var, attr = node.expression.split(".", 1)
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
        # Handle ArrayAccess node
        elif isinstance(node, ArrayAccess):
            array_type = self.visit_expression(node.array)
            if isinstance(array_type, ArrayType):
                return array_type.element_type
            # Optionally handle matrix type
            if hasattr(array_type, "element_type"):
                return array_type.element_type
            return None
        # Handle StringLiteral node
        elif isinstance(node, StringLiteral):
            return StringType()
        elif isinstance(node, BinaryOp):
            print(f"[DEBUG] visit_binary_op: operator={node.operator}, left={node.left}, right={node.right}")
            return self.visit_binary_op(node)
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
        print(f"[DEBUG] visit_binary_op: operator={node.operator}, left={node.left}, right={node.right}")
        # Only type check valid binary operators, not assignment
        if node.operator == "=":
            raise TypeError("Assignment '=' should not be handled as a binary operation. Use visit_assignment instead.")
        left_type = self.visit_expression(node.left)
        right_type = self.visit_expression(node.right)
        print(f"DEBUG: BinaryOp {node.operator} - left: {left_type} ({node.left}), right: {right_type} ({node.right}))")

        # Comparison operators return boolean
        comparison_operators = ["==", "!=", "<", "<=", ">", ">="]
        if node.operator in comparison_operators:
            if type(left_type) is not type(right_type):
                raise TypeError(f"Type mismatch in comparison: {left_type} {node.operator} {right_type}")
            print(f"[DEBUG] visit_binary_op: returning BoolType for operator {node.operator}")
            return BoolType()

        # Arithmetic operators
        arithmetic_operators = ["+", "-", "*", "/"]
        if node.operator in arithmetic_operators:
            # Allow string concatenation for '+'
            if node.operator == "+" and isinstance(left_type, StringType):
                # Allow string + string
                if isinstance(right_type, StringType):
                    return StringType()
                # Allow string + exception object (which can be converted to string)
                if hasattr(right_type, "message") or (
                    hasattr(right_type, "__str__") and callable(getattr(right_type, "__str__"))
                ):
                    return StringType()
            # Allow int/float arithmetic
            if isinstance(left_type, IntType) and isinstance(right_type, IntType):
                return IntType()
            if isinstance(left_type, FloatType) and isinstance(right_type, FloatType):
                return FloatType()
            # Optionally allow int + float or float + int to return float
            if (isinstance(left_type, IntType) and isinstance(right_type, FloatType)) or (
                isinstance(left_type, FloatType) and isinstance(right_type, IntType)
            ):
                return FloatType()
            raise TypeError(
                f"Type mismatch for arithmetic operator '{node.operator}': {left_type} {node.operator} {right_type}"
            )

        # Fallback: require exact type match
        if type(left_type) is not type(right_type):
            raise TypeError(f"Type mismatch: {left_type} {node.operator} {right_type}")
        print(f"[DEBUG] visit_binary_op: returning {left_type} for operator {node.operator}")
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
        elif isinstance(node.target, MethodCall):
            # Attribute assignment (e.g., self.message = value)
            # MethodCall is used for both method calls and attribute access
            # For assignments, we treat it as attribute access
            # Just accept it for now
            pass
        elif isinstance(node.target, ArrayAccess):
            # Array element assignment (e.g., arr[0] = value)
            # Type check the array and index expressions
            self.visit_expression(node.target.array)
            self.visit_expression(node.target.index)
            # For now, we'll just accept it (in a real implementation, you might
            # want to validate that the array type matches the value type)
            pass
        else:
            raise TypeError(f"Unsupported assignment target type: {type(node.target)}")

    def visit_function_call(self, node: FunctionCall):
        func = self.symbol_table.get(node.func_name)
        if not func:
            raise NameError(f"Undefined function: {node.func_name}")
        if not isinstance(func, FunctionType):
            raise TypeError(f"{node.func_name} is not a function")
        # Special handling for variadic/any builtins
        if node.func_name == "print":
            # Accept any number of arguments of any type
            return None
        if node.func_name == "str":
            if len(node.args) != 1:
                raise TypeError(f"str() takes exactly one argument ({len(node.args)} given)")
            return StringType()
        if node.func_name == "len":
            if len(node.args) != 1:
                raise TypeError(f"len() takes exactly one argument ({len(node.args)} given)")
            return IntType()
        if len(func.param_types) != len(node.args):
            raise TypeError(f"Argument count mismatch: expected {len(func.param_types)}, got {len(node.args)}")
        for arg, param_type in zip(node.args, func.param_types):
            arg_type = self.visit_expression(arg)
            if isinstance(param_type, AnyType):
                continue
            if type(arg_type) is not type(param_type):
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

        # If we can't find the instance, it might be a local variable in a function scope
        # For type checking purposes, we'll be lenient and return AnyType
        if not instance:
            # Don't raise an error for variables we can't find - they might be in scope at runtime
            return AnyType()

        # Handle exception objects - they have a message property and __str__ method
        if hasattr(instance, "message") and node.method_name == "message":
            return StringType()
        if hasattr(instance, "__str__") and node.method_name == "__str__":
            return StringType()

        # If instance is a ClassDef or ExceptionDef, look up the method in its methods
        if isinstance(instance, (ClassDef, ExceptionDef)):
            method = None
            for m in getattr(instance, "methods", []):
                if m.name == node.method_name:
                    method = m
                    break
            if method:
                # Return the method's return type
                return self.visit_type_annotation(method.return_type) if method.return_type else None
            # If method not found, return AnyType instead of raising error
            return AnyType()

        # If instance is a dummy with _ymir_type, use that for method lookup
        method_namespace = getattr(instance, "_ymir_type", None)
        if method_namespace and isinstance(method_namespace, dict):
            method = method_namespace.get(node.method_name)
        elif isinstance(instance, dict):
            method = instance.get(node.method_name)
        else:
            method = getattr(instance, node.method_name, None) if hasattr(instance, node.method_name) else None

        if not method:
            # Be lenient - return AnyType instead of raising error
            return AnyType()

        if not isinstance(method, FunctionType):
            # Not a proper method, but return AnyType to be lenient
            return AnyType()

        # Type check arguments if we have a proper method
        if len(method.param_types) != len(node.args):
            # Could raise error, but be lenient
            return method.return_type if method.return_type else AnyType()

        for arg, param_type in zip(node.args, method.param_types):
            arg_type = self.visit_expression(arg)
            if isinstance(param_type, AnyType):
                continue
            # Be lenient with type mismatches
            if type(arg_type) is not type(param_type):
                pass  # Could check more strictly, but being lenient

        return method.return_type if method.return_type else None

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
        elif isinstance(node, MatrixType):
            return MatrixType(self.visit_type_annotation(node.element_type))
        elif isinstance(node, MapType):
            return MapType(self.visit_type_annotation(node.key_type), self.visit_type_annotation(node.value_type))
        elif isinstance(node, TupleType):
            return TupleType([self.visit_type_annotation(t) for t in node.element_types])
        elif isinstance(node, FunctionType):
            param_types = [self.visit_type_annotation(t) for t in node.param_types]
            return FunctionType(param_types, self.visit_type_annotation(node.return_type))
        elif isinstance(node, AnyType):
            return AnyType()
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

    def visit_unary_op(self, node: UnaryOp):
        """Type check a unary operation."""
        operand_type = self.visit(node.operand)
        # Unary minus on int/float returns int/float
        if node.operator == "-":
            if operand_type in [IntType(), FloatType()]:
                return operand_type
        # Unary plus on int/float returns int/float
        elif node.operator == "+":
            if operand_type in [IntType(), FloatType()]:
                return operand_type
        # Logical not on bool returns bool
        elif node.operator == "!":
            return BoolType()
        return AnyType()

    def visit_spawn_statement(self, node: SpawnStatement):
        """Type check a spawn statement."""
        return self.visit(node.call)

    def visit_channel_send(self, node: ChannelSend):
        """Type check a channel send operation."""
        self.visit_expression(node.channel)
        self.visit_expression(node.value)
        return None

    def visit_channel_receive(self, node: ChannelReceive):
        """Type check a channel receive operation."""
        self.visit_expression(node.channel)
        return AnyType()

    def visit_select_statement(self, node: SelectStatement):
        """Type check a select statement."""
        for case in node.cases:
            self.visit(case)
        return None

    def visit_select_case(self, node: SelectCase):
        """Type check a select case."""
        if node.operation:
            self.visit(node.operation)
        for statement in node.body:
            self.visit(statement)
        return None
