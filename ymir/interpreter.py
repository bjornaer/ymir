import ctypes
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
        self.global_scope: Dict[str, Any] = {}
        self.local_scope: Dict[str, Any] = {}
        self.module_cache: Dict[str, ModuleDef] = {}
        self.standard_library_path = os.path.join(os.path.dirname(__file__), "stdlib")
        self.verbosity = verbosity
        self.logger = get_logger("ymir", verbosity)

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
        codegen_body = [node for node in main_module.body if not isinstance(node, ModuleDef)]
        self.logger.debug(f"Filtered codegen body: {codegen_body}")
        code_generator = CodeGenerator()
        self.logger.debug("Starting code generation...")
        llvm_ir = code_generator.generate_code(codegen_body)
        self.logger.debug(f"Generated LLVM IR:\n{llvm_ir}")
        self.logger.debug("Starting execution...")
        self.execute(llvm_ir)
        self.logger.debug("Execution finished.")

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
        for node in ast:
            self.logger.debug(f"[load_module] Top-level AST node: {type(node)} - {repr(node)}")
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
        for node in module_body:
            self.logger.debug(f"[load_module] Evaluating node in module body: {type(node)} - {repr(node)}")
            if isinstance(node, ModuleDef):
                self.logger.debug("[load_module] Skipping ModuleDef node in module body evaluation loop.")
                continue
            if isinstance(node, ImportDef):
                import_path = self.resolve_import(node.module_name)
                self.logger.debug(f"[load_module] Importing module: {import_path}")
                self.load_module(import_path, project_root)
            if isinstance(node, ExportDef):
                self.logger.debug(f"[load_module] Exporting: {node.name}")
                self.global_scope[node.name] = self.evaluate(node.value)
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
            self.logger.error(f"[evaluate] Evaluating expression: {repr(node)} -> {value}")
            return value
        elif isinstance(node, Assignment):
            value = self.evaluate_expression(node.value)
            self.logger.error(f"[evaluate] Assignment: {node.target} = {value}")
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
        elif hasattr(node, "instance") and hasattr(node, "method_name") and hasattr(node, "arguments"):
            # MethodCall node (for property access like e.message)
            instance = self.evaluate_expression(node.instance)
            if not node.arguments:  # Property access
                if hasattr(instance, node.method_name):
                    return getattr(instance, node.method_name)
                else:
                    raise AttributeError(f"'{type(instance).__name__}' object has no attribute '{node.method_name}'")
            else:  # Method call with arguments
                args = [self.evaluate_expression(arg) for arg in node.arguments]
                if hasattr(instance, node.method_name):
                    method = getattr(instance, node.method_name)
                    if callable(method):
                        return method(*args)
                    else:
                        return method
                else:
                    raise AttributeError(f"'{type(instance).__name__}' object has no method '{node.method_name}'")
        elif hasattr(node, "function_name") and hasattr(node, "arguments"):
            # FunctionCall node
            func_name = node.function_name
            args = [self.evaluate_expression(arg) for arg in node.arguments]
            self.logger.error(f"[FunctionCall] Instantiating {func_name} with args: {args}")
            # Check if this is an exception class
            if func_name in self.global_scope:
                obj = self.global_scope[func_name]
                if isinstance(obj, type) and issubclass(obj, BaseException):
                    # For exception classes, automatically set the message attribute
                    if len(args) == 1:
                        message = args[0]
                        self.logger.error(
                            f"[FunctionCall] Creating exception instance of {func_name} with message: {message}"
                        )
                        try:
                            instance = obj(message)
                            instance.message = message  # Explicitly set message attribute
                            self.logger.error(
                                f"[FunctionCall] Created instance: {instance}, "
                                f"message: {getattr(instance, 'message', None)}"
                            )
                            self.logger.error(f"[FunctionCall] Instance class: {instance.__class__}")
                            self.logger.error(f"[FunctionCall] Instance MRO: {instance.__class__.__mro__}")
                            self.logger.error(f"[FunctionCall] Instance __init__: {instance.__class__.__init__}")
                        except Exception as e:
                            self.logger.error(f"[FunctionCall] Exception during instantiation: {e}")
                            raise
                        return instance
                    else:
                        raise ValueError(f"Exception constructor expects exactly 1 argument (message), got {len(args)}")
                elif callable(obj):
                    return obj(*args)
            raise NameError(f"Undefined function or class: {func_name}")
        else:
            self.logger.debug(f"[evaluate] Unknown node type: {type(node)} - {repr(node)}")
            raise TypeError(f"Unknown AST node type: {type(node)}")

    def evaluate_expression(self, node: ASTNode) -> Any:
        self.logger.error(f"[evaluate_expression] Node type: {type(node)} - {repr(node)}")
        if isinstance(node, int):
            return node
        elif isinstance(node, str):
            if node in self.local_scope:
                value = self.local_scope[node]
                # If the value is an exception, convert to string for return/concat
                if isinstance(value, BaseException):
                    value = str(value)
                self.logger.error(f"[evaluate_expression] Variable '{node}' in local_scope -> {value}")
                return value
            elif node in self.global_scope:
                value = self.global_scope[node]
                if isinstance(value, BaseException):
                    value = str(value)
                self.logger.error(f"[evaluate_expression] Variable '{node}' in global_scope -> {value}")
                return value
            # If not a variable, treat as string literal
            self.logger.error(f"[evaluate_expression] String literal: {node}")
            return node
        elif hasattr(node, "expression"):
            # Expression node
            if isinstance(node.expression, int):
                return node.expression
            elif isinstance(node.expression, str):
                if node.expression in self.local_scope:
                    value = self.local_scope[node.expression]
                    # If the value is an exception, convert to string for return/concat
                    if isinstance(value, BaseException):
                        value = str(value)
                    self.logger.error(f"[evaluate_expression] Variable '{node.expression}' in local_scope -> {value}")
                    return value
                elif node.expression in self.global_scope:
                    value = self.global_scope[node.expression]
                    if isinstance(value, BaseException):
                        value = str(value)
                    self.logger.error(f"[evaluate_expression] Variable '{node.expression}' in global_scope -> {value}")
                    return value
                # If not a variable, treat as string literal
                self.logger.error(f"[evaluate_expression] String literal: {node.expression}")
                return node.expression
            elif (
                hasattr(node.expression, "instance")
                and hasattr(node.expression, "method_name")
                and hasattr(node.expression, "arguments")
            ):
                # MethodCall wrapped in Expression
                return self.evaluate_expression(node.expression)
            else:
                # Other expression types
                value = self.evaluate_expression(node.expression)
                self.logger.error(f"[evaluate_expression] Expression node: {repr(node.expression)} -> {value}")
                return value
        elif hasattr(node, "left") and hasattr(node, "right") and hasattr(node, "operator"):
            # BinaryOp node
            left = self.evaluate_expression(node.left)
            right = self.evaluate_expression(node.right)
            # If either side is an exception, convert to string
            if isinstance(left, BaseException):
                left = str(left)
            if isinstance(right, BaseException):
                right = str(right)
            if node.operator == "+":
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
            self.logger.error(
                f"[evaluate_expression] BinaryOp {node.operator}: {left} {node.operator} {right} = {result}"
            )
            return result
        elif hasattr(node, "value") and type(node).__name__ == "StringLiteral":
            # Strip leading and trailing quotes from the string literal
            raw = node.value
            if isinstance(raw, str) and len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
                value = raw[1:-1]
            else:
                value = raw
            self.logger.error(f"[evaluate_expression] StringLiteral node: {value}")
            return value
        elif hasattr(node, "instance") and hasattr(node, "method_name") and hasattr(node, "arguments"):
            # MethodCall node (for property access like e.message)
            instance = self.evaluate_expression(node.instance)
            if not node.arguments:  # Property access
                if hasattr(instance, node.method_name):
                    return getattr(instance, node.method_name)
                else:
                    raise AttributeError(f"'{type(instance).__name__}' object has no attribute '{node.method_name}'")
            else:  # Method call with arguments
                args = [self.evaluate_expression(arg) for arg in node.arguments]
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
                self.logger.error(f"[evaluate_function_call] Evaluating stmt: {type(stmt)} - {repr(stmt)}")
                self.evaluate(stmt)
        except ReturnSignal as ret:
            self.logger.error(f"[evaluate_function_call] Caught ReturnSignal with value: {ret.value}")
            self.local_scope = prev_local_scope
            return ret.value
        self.logger.error("[evaluate_function_call] No return encountered, returning None")
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
            self.logger.error(
                f"[TryExcept] Caught exception: {exc}, type: {type(exc)}, message: {getattr(exc, 'message', None)}"
            )
            for except_clause in node.except_clauses:
                if except_clause.exception_type is None or (
                    except_clause.exception_type in self.global_scope
                    and isinstance(exc, self.global_scope[except_clause.exception_type])
                ):
                    if except_clause.exception_var:
                        self.local_scope[except_clause.exception_var] = exc
                        self.logger.error(
                            f"[TryExcept] Bound variable '{except_clause.exception_var}' "
                            f"to exception: {exc}, message: {getattr(exc, 'message', None)}"
                        )
                    for stmt in except_clause.body:
                        result = self.evaluate(stmt)
                    return result
            raise
        finally:
            if node.finally_clause:
                for stmt in node.finally_clause:
                    self.evaluate(stmt)

    def evaluate_throw_statement(self, node: ThrowStatement) -> None:
        """Evaluate a throw statement."""
        # Evaluate the expression to get the exception value
        self.logger.error(
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

    def evaluate_exception_def(self, node: ExceptionDef) -> None:
        """Evaluate an exception class definition."""
        # Create a new exception class
        base_exception = Exception
        if node.base_class:
            base_exception = self.global_scope.get(node.base_class, Exception)

        # Always inject an __init__ that sets self.message
        def exception_init(self, message):
            self.message = message
            # Correct super() usage for proper chaining
            super().__init__(message)

        class_dict = {"__init__": exception_init}
        # Add any custom methods (but ignore __init__ since we provide our own)
        for method in node.methods:
            if method.name != "__init__":
                class_dict[method.name] = method

        # Define the new exception class
        exception_class = type(node.name, (base_exception,), class_dict)

        # Register the exception class
        self.global_scope[node.name] = exception_class

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
