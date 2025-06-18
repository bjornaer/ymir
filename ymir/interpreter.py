import ctypes
import logging
import os
import platform
import subprocess
from typing import Any, Dict, List, Optional

from llvmlite import binding, ir

from ymir.core.ast import (
    Assignment,
    ASTNode,
    Break,
    ClassDef,
    Continue,
    ExceptionDef,
    ExportDef,
    Expression,
    ForCStyleLoop,
    ForInLoop,
    FunctionDef,
    IfStatement,
    ImportDef,
    ModuleDef,
    ReturnStatement,
    ThrowStatement,
    TryExceptStatement,
    WhileStatement,
)
from ymir.core.lexer import Lexer
from ymir.core.parser import Parser
from ymir.core.semantic_analyzer import SemanticAnalyzer
from ymir.core.type_checker import TypeChecker
from ymir.logging import get_logger
from ymir.tools.codegen import CodeGenerator


class YmirInterpreter:
    def __init__(self, verbosity: str = "INFO"):
        self.verbosity = verbosity
        self.logger = get_logger("ymir", verbosity)
        self.logger.setLevel(getattr(logging, verbosity))
        self.global_scope = {}
        self.local_scope = {}
        self.module_cache: Dict[str, ModuleDef] = {}
        self.standard_library_path = os.path.join(os.path.dirname(__file__), "stdlib")

        # Register builtin functions
        self._register_builtin_functions()

        self.load_standard_library()

    def _register_builtin_functions(self):
        """Register common Python builtin functions in the global scope."""
        # print function: takes any number of arguments, prints them
        self.global_scope["print"] = print

        # str function: converts any value to string
        self.global_scope["str"] = str

        # len function: returns length of sequence
        self.global_scope["len"] = len

        # Common math functions
        import math

        self.global_scope["sqrt"] = math.sqrt
        self.global_scope["sin"] = math.sin
        self.global_scope["cos"] = math.cos
        self.global_scope["tan"] = math.tan
        self.global_scope["abs"] = abs
        self.global_scope["round"] = round
        self.global_scope["min"] = min
        self.global_scope["max"] = max

    def execute(self, llvm_ir: str) -> None:
        """Execute LLVM IR code by JIT compiling and running it.

        This function takes LLVM IR as a string, initializes the LLVM execution engine,
        compiles the code, and executes the main function.

        Args:
            llvm_ir (str): The LLVM IR code to execute as a string

        Returns:
            None

        The function performs the following steps:
        1. Initializes LLVM and native target
        2. Parses and verifies the LLVM IR module
        3. Creates a JIT compiler and execution engine
        4. Retrieves and executes the main function
        """
        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()

        llvm_module = binding.parse_assembly(llvm_ir)
        llvm_module.verify()

        target_machine = binding.Target.from_default_triple().create_target_machine()
        with binding.create_mcjit_compiler(llvm_module, target_machine) as ee:
            ee.finalize_object()
            ee.run_static_constructors()

            main_func_ptr = ee.get_function_address("main")
            main_func = ctypes.CFUNCTYPE(None)(main_func_ptr)
            main_func()

    def execute_builtin_function(self, func, args):
        """Execute a built-in LLVM function with the given arguments.

        This function takes an LLVM function and its arguments, JIT compiles the function,
        and executes it with the provided arguments.

        Args:
            func: The LLVM function to execute
            args: List of arguments to pass to the function

        Returns:
            The result of executing the function with the given arguments

        The function performs the following steps:
        1. Initializes LLVM and native target
        2. Parses and verifies the LLVM module containing the function
        3. Creates a JIT compiler and execution engine
        4. Converts the function and arguments to appropriate C types
        5. Executes the function and returns the result
        """
        llvm_ir = str(func.module)
        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()

        llvm_module = binding.parse_assembly(llvm_ir)
        llvm_module.verify()

        target_machine = binding.Target.from_default_triple().create_target_machine()
        with binding.create_mcjit_compiler(llvm_module, target_machine) as ee:
            ee.finalize_object()
            ee.run_static_constructors()

            func_ptr = ee.get_function_address(func.name)

            argtypes = [ctypes.c_double if arg.type == ir.DoubleType() else ctypes.c_int for arg in func.args]
            cfunc = (
                ctypes.CFUNCTYPE(ctypes.c_double, *argtypes)(func_ptr)
                if func.return_value.type == ir.DoubleType()
                else ctypes.CFUNCTYPE(ctypes.c_int, *argtypes)(func_ptr)
            )

            cargs = [ctypes.c_double(arg) if isinstance(arg, float) else ctypes.c_int(arg) for arg in args]

            return cfunc(*cargs)

    def run_ymir_script(self, file_path: str) -> None:
        self.logger.debug(f"Running Ymir script: {file_path}")
        self.load_standard_library()
        project_root = os.path.dirname(os.path.abspath(file_path))
        main_module = self.load_module(file_path, project_root, is_entry_point=True)
        self.logger.debug(f"Main module after loading: {main_module}")
        self.logger.debug(f"Main module body: {main_module.body}")

        # Skip LLVM code generation and execution for now since interpretation is working
        # and LLVM execution fails due to missing main function
        self.logger.debug("Script executed successfully via interpretation")

        # TODO: Fix LLVM code generation to create proper main function
        # codegen_body = [node for node in main_module.body if not isinstance(node, ModuleDef)]
        # self.logger.debug(f"Filtered codegen body: {codegen_body}")
        # code_generator = CodeGenerator()
        # self.logger.debug("Starting code generation...")
        # llvm_ir = code_generator.generate_code(codegen_body)
        # self.logger.debug(f"Generated LLVM IR:\n{llvm_ir}")
        # self.logger.debug("Starting execution...")
        # self.execute(llvm_ir)
        # self.logger.debug("Execution finished.")

    def load_module(self, file_path: str, project_root: str, is_entry_point: bool = False) -> ModuleDef:
        self.logger.debug(f"Loading module: {file_path}")
        with open(file_path, "r") as file:
            source_code = file.read()
        self.logger.debug(f"Source code: {source_code}")
        lexer = Lexer(source_code, verbosity=self.verbosity)
        tokens = lexer.tokenize()
        self.logger.debug(f"Tokens: {tokens}")
        parser = Parser(tokens, verbosity=self.verbosity)
        ast = parser.parse()
        self.logger.debug(f"AST: {ast}")
        semantic_analyzer = SemanticAnalyzer(verbosity=self.verbosity)
        semantic_analyzer.analyze(ast)
        self.logger.debug("Semantic analysis complete")
        type_checker = TypeChecker(verbosity=self.verbosity)
        type_checker.check(ast)
        self.logger.debug("Type checking complete")
        module = None
        module_body = ast
        module_name = None
        for node in ast:
            if isinstance(node, ModuleDef):
                module = node
                module_body = node.body
                module_name = node.name
                break
        if module_name is None:
            raise SyntaxError(f"Module name not defined in {file_path}")
        self.logger.debug(f"Module name: {module_name}")
        module = ModuleDef(module_name, module_body)
        self.module_cache[module_name] = module
        self.logger.debug(f"Module: {module}")
        # First pass: register all classes and functions
        for node in module_body:
            if isinstance(node, (ClassDef, ExceptionDef)):
                self.logger.debug(f"[load_module] Registering class: {node.name}")
                self.global_scope[node.name] = self.evaluate_exception_def(node)
            elif isinstance(node, FunctionDef):
                self.logger.debug(f"[load_module] Registering function: {node.name}")
                self.global_scope[node.name] = node
        # Second pass: process imports and exports
        for node in module_body:
            if isinstance(node, ModuleDef):
                self.logger.debug("[load_module] Skipping ModuleDef node in module body evaluation loop.")
                continue
            if isinstance(node, ImportDef):
                import_path = self.resolve_import(node.module_name)
                self.logger.debug(f"[load_module] Importing module: {import_path}")
                self.load_module(import_path, project_root)
            if isinstance(node, ExportDef):
                self.logger.debug(f"[load_module] Exporting: {node.name}")
                value = self.evaluate(node.value)
                if isinstance(value, str) and value in self.global_scope:
                    value = self.global_scope[value]
                self.global_scope[node.name] = value
                fq_name = f"{module_name}.{node.name}"
                self.global_scope[fq_name] = value
            elif is_entry_point:
                self.logger.debug(f"[load_module] Evaluating (entry point): {type(node)} - {repr(node)}")
                self.evaluate(node)
        return module

    def evaluate(self, node: ASTNode) -> Any:
        self.logger.debug(f"[evaluate] Evaluating AST node: {type(node)} - {repr(node)}")
        if isinstance(node, FunctionDef):
            self.logger.debug(f"[evaluate] Registering function: {node.name}")
            self.global_scope[node.name] = node
        elif isinstance(node, ClassDef):
            self.logger.debug(f"[evaluate] Registering class: {node.name}")
            self.global_scope[node.name] = node
        elif isinstance(node, Expression):
            value = self.evaluate_expression(node)
            self.logger.debug(f"[evaluate] Evaluating expression: {repr(node)} -> {value}")
            return value
        elif type(node).__name__ == "FunctionCall":
            value = self.evaluate_expression(node)
            self.logger.debug(f"[evaluate] Evaluating function call: {repr(node)} -> {value}")
            return value
        elif isinstance(node, Assignment):
            value = self.evaluate_expression(node.value)
            self.logger.debug(f"[evaluate] Assignment: {node.target} = {value}")
            if self.local_scope is not None and node.target in self.local_scope:
                self.local_scope[node.target] = value
            elif self.local_scope is not None and len(self.local_scope) > 0:
                self.local_scope[node.target] = value
            else:
                self.global_scope[node.target] = value
        elif isinstance(node, ExportDef):
            self.logger.debug(f"[evaluate] Exporting: {node.name}")
            self.global_scope[node.name] = self.evaluate(node.value)
        elif isinstance(node, ForCStyleLoop):
            self.evaluate_for_cstyle_loop(node)
        elif isinstance(node, ForInLoop):
            self.evaluate_for_in_loop(node)
        elif isinstance(node, WhileStatement):
            self.evaluate_while_statement(node)
        elif isinstance(node, IfStatement):
            self.evaluate_if_statement(node)
        elif isinstance(node, Continue):
            raise ContinueSignal()
        elif isinstance(node, Break):
            raise BreakSignal()
        elif isinstance(node, TryExceptStatement):
            return self.evaluate_try_except_statement(node)
        elif isinstance(node, ThrowStatement):
            return self.evaluate_throw_statement(node)
        elif isinstance(node, ExceptionDef):
            return self.evaluate_exception_def(node)
        elif isinstance(node, ModuleDef):
            for stmt in node.body:
                self.evaluate(stmt)
        elif isinstance(node, ReturnStatement):
            self.logger.debug(f"[evaluate] Handling ReturnStatement: {repr(node)}")
            value = self.evaluate_expression(node.expression)
            raise ReturnSignal(value)
        elif hasattr(node, "instance") and hasattr(node, "method_name") and hasattr(node, "args"):
            # MethodCall node (for property access like e.message)
            instance = self.evaluate_expression(node.instance)
            if not node.args:  # Property access
                if hasattr(instance, node.method_name):
                    attr = getattr(instance, node.method_name)
                    if callable(attr):
                        import inspect

                        sig = inspect.signature(attr)
                        if len(sig.parameters) == 0:
                            return attr()
                    return attr
                else:
                    raise AttributeError(f"'{type(instance).__name__}' object has no attribute '{node.method_name}'")
            else:  # Method call with arguments
                args = [self.evaluate_expression(arg) for arg in node.args]
                if hasattr(instance, node.method_name):
                    method = getattr(instance, node.method_name)
                    if callable(method):
                        return method(*args)
                    else:
                        return method
                else:
                    raise AttributeError(f"'{type(instance).__name__}' object has no method '{node.method_name}'")
        elif type(node).__name__ == "ImportDef":
            # No-op for import statements (already handled by load_standard_library)
            return None
        else:
            self.logger.debug(f"[evaluate] Unknown node type: {type(node)} - {repr(node)}")
            raise TypeError(f"Unknown AST node type: {type(node)}")

    def evaluate_expression(self, node: ASTNode) -> Any:
        self.logger.debug(f"[evaluate_expression] ENTRY: node={node}, type={type(node)}")
        self.logger.debug(f"[evaluate_expression] Node type: {type(node)} - {repr(node)}")
        if isinstance(node, int):
            return node
        elif isinstance(node, str):
            if node in self.local_scope:
                value = self.local_scope[node]
                self.logger.debug(f"[evaluate_expression] Variable '{node}' in local_scope -> {value}")
                return value
            elif node in self.global_scope:
                value = self.global_scope[node]
                self.logger.debug(f"[evaluate_expression] Variable '{node}' in global_scope -> {value}")
                return value
            # If not a variable, treat as string literal
            self.logger.debug(f"[evaluate_expression] String literal: {node}")
            return node
        elif hasattr(node, "func_name") and hasattr(node, "args"):
            # FunctionCall node (for exception instantiation like ChildError("message"))
            func_name = node.func_name
            args = [self.evaluate_expression(arg) for arg in node.args]
            self.logger.debug(f"[FunctionCall] func_name: {repr(func_name)}")
            if func_name in self.global_scope:
                obj = self.global_scope[func_name]
                self.logger.debug(f"[FunctionCall] Retrieved obj for {func_name}: {obj}, type: {type(obj)}")
                if isinstance(obj, type) and issubclass(obj, BaseException):
                    # It's an exception class, instantiate it
                    if len(args) == 1:
                        message = args[0]
                        # If it's a quoted string, strip the quotes
                        if isinstance(message, str) and len(message) >= 2 and message[0] == '"' and message[-1] == '"':
                            message = message[1:-1]
                        try:
                            instance = obj(message)
                            instance.message = message  # Explicitly set message attribute
                            self.logger.error(
                                f"[FunctionCall] Created exception instance: {instance}, "
                                f"type: {type(instance)}, message: {getattr(instance, 'message', None)}"
                            )
                            return instance
                        except Exception as e:
                            self.logger.error(f"[FunctionCall] Exception during instantiation: {e}")
                            raise
                    else:
                        raise ValueError(f"Exception constructor expects exactly 1 argument (message), got {len(args)}")
                elif isinstance(obj, FunctionDef):
                    # User-defined function: interpret its body
                    return self.evaluate_function_call(func_name, args)
                elif callable(obj):
                    # Builtin or Python function
                    try:
                        return obj(*args)
                    except Exception as e:
                        self.logger.error(f"[FunctionCall] Exception during call: {e}")
                        raise
                else:
                    raise TypeError(f"Object {func_name} is not callable")
            else:
                raise NameError(f"Undefined function or class: {func_name}")
        elif hasattr(node, "expression"):
            # Expression node
            if isinstance(node.expression, int):
                return node.expression
            elif isinstance(node.expression, str):
                if node.expression in self.local_scope:
                    value = self.local_scope[node.expression]
                    self.logger.debug(f"[evaluate_expression] Variable '{node.expression}' in local_scope -> {value}")
                    return value
                elif node.expression in self.global_scope:
                    value = self.global_scope[node.expression]
                    self.logger.debug(f"[evaluate_expression] Variable '{node.expression}' in global_scope -> {value}")
                    return value
                # If not a variable, treat as string literal
                self.logger.debug(f"[evaluate_expression] String literal: {node.expression}")
                return node.expression
            elif (
                hasattr(node.expression, "instance")
                and hasattr(node.expression, "method_name")
                and hasattr(node.expression, "args")
            ):
                # MethodCall wrapped in Expression
                return self.evaluate_expression(node.expression)
            else:
                # Other expression types
                value = self.evaluate_expression(node.expression)
                self.logger.debug(f"[evaluate_expression] Expression node: {repr(node.expression)} -> {value}")
                return value
        elif hasattr(node, "left") and hasattr(node, "right") and hasattr(node, "operator"):
            # BinaryOp node
            left = self.evaluate_expression(node.left)
            right = self.evaluate_expression(node.right)
            if node.operator == "+":
                # If either side is an exception, convert to string for concatenation
                if isinstance(left, BaseException):
                    left = str(left)
                if isinstance(right, BaseException):
                    right = str(right)
                result = left + right
            elif node.operator == "-":
                result = left - right
            elif node.operator == "*":
                result = left * right
            elif node.operator == "/":
                result = left / right
            elif node.operator == "%":
                result = left % right
            elif node.operator == "**":
                result = left**right
            elif node.operator == "//":
                result = left // right
            elif node.operator == "==":
                result = left == right
            elif node.operator == "!=":
                result = left != right
            elif node.operator == "<":
                result = left < right
            elif node.operator == "<=":
                result = left <= right
            elif node.operator == ">":
                result = left > right
            elif node.operator == ">=":
                result = left >= right
            elif node.operator == "&&":
                result = left and right
            elif node.operator == "||":
                result = left or right
            else:
                raise ValueError(f"Unsupported binary operator: {node.operator}")
            self.logger.debug(
                f"[evaluate_expression] BinaryOp {node.operator}: {left} {node.operator} {right} = {result}"
            )
            return result
        elif hasattr(node, "operand") and hasattr(node, "operator") and not hasattr(node, "left"):
            # UnaryOp node
            operand = self.evaluate_expression(node.operand)
            if node.operator == "-":
                result = -operand
            elif node.operator == "+":
                result = +operand
            else:
                raise ValueError(f"Unsupported unary operator: {node.operator}")
            self.logger.debug(f"[evaluate_expression] UnaryOp {node.operator}: {node.operator}{operand} = {result}")
            return result
        elif hasattr(node, "value") and type(node).__name__ == "StringLiteral":
            # Strip leading and trailing quotes from the string literal
            raw = node.value
            if isinstance(raw, str) and len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
                value = raw[1:-1]
            else:
                value = raw
            self.logger.debug(f"[evaluate_expression] StringLiteral node: {value}")
            return value
        elif hasattr(node, "instance") and hasattr(node, "method_name") and hasattr(node, "args"):
            # MethodCall node (for property access like e.message)
            instance = self.evaluate_expression(node.instance)
            if not node.args:  # Property access
                if hasattr(instance, node.method_name):
                    attr = getattr(instance, node.method_name)
                    if callable(attr):
                        import inspect

                        sig = inspect.signature(attr)
                        if len(sig.parameters) == 0:
                            return attr()
                    return attr
                else:
                    raise AttributeError(f"'{type(instance).__name__}' object has no attribute '{node.method_name}'")
            else:  # Method call with arguments
                args = [self.evaluate_expression(arg) for arg in node.args]
                if hasattr(instance, node.method_name):
                    method = getattr(instance, node.method_name)
                    if callable(method):
                        return method(*args)
                    else:
                        return method
                else:
                    raise AttributeError(f"'{type(instance).__name__}' object has no method '{node.method_name}'")
        return None

    def evaluate_function_call(self, func_name: str, args: List[Any]) -> Any:
        """Evaluate a function call by interpreting the FunctionDef body."""
        func = self.global_scope[func_name]
        if not isinstance(func, FunctionDef):
            raise TypeError(f"{func_name} is not a function definition")
        prev_local_scope = self.local_scope.copy()
        self.local_scope = {}
        for param, arg in zip(func.params, args):
            self.local_scope[param] = arg
        try:
            for stmt in func.body:
                self.logger.debug(f"[evaluate_function_call] Evaluating stmt: {type(stmt)} - {repr(stmt)}")
                self.evaluate(stmt)
        except ReturnSignal as ret:
            self.logger.debug(f"[evaluate_function_call] Caught ReturnSignal with value: {ret.value}")
            self.local_scope = prev_local_scope
            # If the return value is an exception, convert to string
            if isinstance(ret.value, BaseException):
                return str(ret.value)
            return ret.value
        self.logger.debug("[evaluate_function_call] No return encountered, returning None")
        self.local_scope = prev_local_scope
        return None

    def evaluate_for_cstyle_loop(self, node: ForCStyleLoop) -> None:
        """Evaluate a C-style for loop.

        This function takes a C-style for loop and evaluates it.

        Args:
            node: The C-style for loop to evaluate

        The function performs the following steps:
        1. Evaluates the initialization expression
        2. Evaluates the condition expression
        3. Executes the body of the loop
        4. Evaluates the increment expression
        """
        self.evaluate_expression(node.init)
        while self.evaluate_expression(node.condition):
            for statement in node.body:
                self.evaluate(statement)
            self.evaluate_expression(node.increment)

    def evaluate_for_in_loop(self, node: ForInLoop) -> None:
        iterable = self.evaluate_expression(node.iterable)
        for item in iterable:
            self.local_scope[node.var] = item
            for statement in node.body:
                self.evaluate(statement)

    def evaluate_while_statement(self, node: WhileStatement) -> None:
        while self.evaluate_expression(node.condition):
            try:
                for statement in node.body:
                    self.evaluate(statement)
            except ContinueSignal:
                continue
            except BreakSignal:
                break

    def evaluate_if_statement(self, node: IfStatement) -> None:
        condition = self.evaluate_expression(node.condition)
        if condition:
            for stmt in node.then_body:
                self.evaluate(stmt)
        elif node.else_body:
            for stmt in node.else_body:
                self.evaluate(stmt)

    def load_standard_library(self) -> None:
        stdlib_path = self.standard_library_path
        for root, _, files in os.walk(stdlib_path):
            for file in files:
                if file.endswith(".ymr"):
                    file_path = os.path.join(root, file)
                    self.load_module(file_path, stdlib_path)

    def resolve_import(self, module_name: str) -> str:
        stdlib_path = self.standard_library_path
        module_parts = module_name.split(".")
        if len(module_parts) == 1:
            # Assume standard library
            file_path = os.path.join(stdlib_path, module_parts[0] + ".ymr")
            if os.path.exists(file_path):
                return file_path
        else:
            # Project module
            file_path = os.path.join(*module_parts) + ".ymr"
            if os.path.exists(file_path):
                return file_path
        raise ImportError(f"Cannot find module {module_name}")

    def build_ymir(self, input_file: str, output_file: str, arch: Optional[str] = None) -> None:
        self.load_standard_library()
        project_root = os.path.dirname(os.path.abspath(input_file))
        main_module = self.load_module(input_file, project_root, is_entry_point=True)

        code_generator = CodeGenerator()
        llvm_ir = code_generator.generate_code(main_module.body)

        self.save_binary(llvm_ir, output_file, arch)

    def save_binary(self, llvm_ir: str, output_file: str, arch: Optional[str] = None) -> None:
        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()

        llvm_module = binding.parse_assembly(llvm_ir)
        llvm_module.verify()

        target_machine = self.create_target_machine(arch)
        with binding.create_mcjit_compiler(llvm_module, target_machine) as ee:
            ee.finalize_object()
            ee.run_static_constructors()

            obj_file = output_file + ".o"
            with open(obj_file, "wb") as f:
                f.write(target_machine.emit_object(llvm_module))

            # Link the object file to create the final binary
            if platform.system() == "Windows":
                self.link_windows(obj_file, output_file)
            else:
                self.link_unix(obj_file, output_file)

            # Clean up the object file
            os.remove(obj_file)

    def create_target_machine(self, arch: Optional[str]) -> binding.TargetMachine:
        target = binding.Target.from_default_triple()
        if arch:
            triple = f"{arch}-pc-{platform.system().lower()}"
            target = binding.Target.from_triple(triple)
        return target.create_target_machine()

    def link_windows(self, obj_file: str, output_file: str) -> None:
        link_command = [
            "link.exe",
            "/OUT:" + output_file,
            obj_file,
            "/ENTRY:main",
            "/SUBSYSTEM:CONSOLE",
            "kernel32.lib",
        ]
        subprocess.run(link_command, check=True)

    def link_unix(self, obj_file: str, output_file: str) -> None:
        link_command = ["gcc", obj_file, "-o", output_file]
        subprocess.run(link_command, check=True)

    def evaluate_try_except_statement(self, node: TryExceptStatement) -> Any:
        """Evaluate a try-except-finally statement."""
        try:
            result = None
            for stmt in node.try_block:
                self.logger.debug(f"[evaluate_try_except_statement] Evaluating try stmt: {type(stmt)} - {repr(stmt)}")
                result = self.evaluate(stmt)
            return result
        except BaseException as exc:
            self.logger.debug(
                f"[TryExcept] Caught exception: {exc}, type: {type(exc)}, message: {getattr(exc, 'message', None)}"
            )
            for except_clause in node.except_clauses:
                # Extract exception type name from Expression node
                exception_type_name = None
                if except_clause.exception_type is not None:
                    if isinstance(except_clause.exception_type, Expression):
                        exception_type_name = except_clause.exception_type.expression
                    else:
                        exception_type_name = str(except_clause.exception_type)

                if exception_type_name is None or (
                    exception_type_name in self.global_scope and isinstance(exc, self.global_scope[exception_type_name])
                ):
                    if except_clause.exception_var:
                        self.local_scope[except_clause.exception_var] = exc
                        self.logger.debug(
                            f"[TryExcept] Bound variable '{except_clause.exception_var}' "
                            f"to exception: {exc}, message: {getattr(exc, 'message', None)}"
                        )
                    for stmt in except_clause.except_block:
                        result = self.evaluate(stmt)
                    return result
            raise
        finally:
            if node.finally_clause:
                for stmt in node.finally_clause.finally_block:
                    self.evaluate(stmt)

    def evaluate_throw_statement(self, node: ThrowStatement) -> None:
        """Evaluate a throw statement."""
        # Evaluate the expression to get the exception value
        self.logger.debug(
            f"[ThrowStatement] node.expression type: {type(node.expression)}, value: {repr(node.expression)}"
        )
        if hasattr(node.expression, "value"):
            exception = node.expression.value
        else:
            exception = self.evaluate_expression(node.expression)
        # If it's not a BaseException, wrap it in YmirException
        if not isinstance(exception, BaseException):
            # If it's a quoted string, strip the quotes
            if isinstance(exception, str) and len(exception) >= 2 and exception[0] == '"' and exception[-1] == '"':
                exception = exception[1:-1]
            exception = YmirException(exception)
        raise exception

    def evaluate_exception_def(self, node: ExceptionDef) -> type:
        """Evaluate an exception class definition."""
        # Create a new exception class
        base_exception = Exception
        if node.base_class:
            base_exception = self.global_scope.get(node.base_class, Exception)

        # Always inject an __init__ that sets self.message
        def exception_init(self, message):
            self.message = message
            base_exception.__init__(self, message)

        class_dict = {"__init__": exception_init}
        # If this is the base Exception class, inject a __str__ method
        if node.name == "Exception":

            def exception_str(self):
                return f"{self.__class__.__name__}: {self.message}"

            class_dict["__str__"] = exception_str
        # Add any custom methods (but ignore __init__ since we provide our own)
        for method in node.methods:
            if method.name != "__init__":
                pass  # Do not add custom methods for now

        # Define the new exception class
        exception_class = type(node.name, (base_exception,), class_dict)
        # Attach interpreter reference for method execution
        exception_class._interpreter = self

        # Register the exception class
        self.global_scope[node.name] = exception_class
        self.logger.debug(f"[ExceptionDef] Registered exception class: {node.name} in global_scope")
        return exception_class

    def is_instance_of_exception(self, exception, exception_class):
        """Check if an exception is an instance of a specified exception class."""
        if exception_class is None:
            return True
        return isinstance(exception, exception_class)


class ContinueSignal(Exception):
    pass


class BreakSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class YmirException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return str(self.message)
