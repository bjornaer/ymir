import ctypes
import logging
import os
import platform
import subprocess
from typing import Any, Dict, List, Optional

import numpy as np
from llvmlite import binding, ir

from ymir.core.ast import (
    ArrayAccess,
    Assignment,
    ASTNode,
    BinaryOp,
    Break,
    ChannelReceive,
    ChannelSend,
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
    SpawnStatement,
    ThrowStatement,
    TryExceptStatement,
    WhileStatement,
)
from ymir.core.builtin_http import HTTPServer, Request, Response, get_http_client
from ymir.core.concurrency import get_runtime as get_concurrency_runtime
from ymir.core.lexer import Lexer
from ymir.core.matrix_backend import get_backend as get_matrix_backend
from ymir.core.parser import Parser
from ymir.core.semantic_analyzer import SemanticAnalyzer
from ymir.core.type_checker import TypeChecker
from ymir.logging import get_logger
from ymir.tools.codegen import CodeGenerator


class Module:
    """Simple module class to hold exported functions and constants."""

    def __init__(self, name: str):
        self.name = name
        self.exports = {}


class YmirInterpreter:
    def __init__(self, verbosity: str = "INFO"):
        self.verbosity = verbosity
        self.logger = get_logger("ymir", verbosity)
        self.logger.setLevel(getattr(logging, verbosity))
        self.global_scope = {}
        self.local_scope = {}
        self.loaded_modules: Dict[str, Module] = {}
        self.standard_library_path = os.path.join(os.path.dirname(__file__), "stdlib")

        # Initialize matrix backend
        self.matrix_backend = get_matrix_backend()
        self.logger.info(f"Matrix backend initialized: GPU available = {self.matrix_backend.is_gpu_available()}")

        # Initialize concurrency runtime
        self.concurrency_runtime = get_concurrency_runtime()
        self.concurrency_runtime.initialize()
        self.logger.info("Concurrency runtime initialized")

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

        self.global_scope["abs"] = abs
        self.global_scope["round"] = round
        self.global_scope["min"] = min
        self.global_scope["max"] = max

        # Matrix methods
        def matrix_transpose(matrix):
            """Transpose a matrix."""
            if self.is_matrix(matrix):
                backend_matrix = self.to_numpy_matrix(matrix)
                result = self.matrix_backend.transpose(backend_matrix)
                return self.from_numpy_matrix(result)
            else:
                raise TypeError("transpose() can only be called on matrices")

        def matrix_determinant(matrix):
            """Calculate the determinant of a matrix."""
            if self.is_matrix(matrix):
                backend_matrix = self.to_numpy_matrix(matrix)
                return self.matrix_backend.determinant(backend_matrix)
            else:
                raise TypeError("det() can only be called on matrices")

        def matrix_inverse(matrix):
            """Calculate the inverse of a matrix."""
            if self.is_matrix(matrix):
                backend_matrix = self.to_numpy_matrix(matrix)
                try:
                    result = self.matrix_backend.inverse(backend_matrix)
                    return self.from_numpy_matrix(result)
                except Exception as e:
                    raise ValueError(f"Matrix is not invertible: {e}")
            else:
                raise TypeError("inverse() can only be called on matrices")

        def matrix_shape(matrix):
            """Get the shape of a matrix."""
            if self.is_matrix(matrix):
                backend_matrix = self.to_numpy_matrix(matrix)
                return self.matrix_backend.shape(backend_matrix)
            else:
                raise TypeError("shape() can only be called on matrices")

        def matrix_gpu_available():
            """Check if GPU acceleration is available."""
            return self.matrix_backend.is_gpu_available()

        def matrix_to_gpu(matrix):
            """Transfer matrix to GPU memory."""
            if self.is_matrix(matrix):
                backend_matrix = self.to_numpy_matrix(matrix)
                gpu_matrix = self.matrix_backend.to_gpu(backend_matrix)
                # Return as opaque GPU matrix (backend-specific type)
                return gpu_matrix
            else:
                raise TypeError("matrix_to_gpu() can only be called on matrices")

        def matrix_from_gpu(gpu_matrix):
            """Transfer matrix from GPU to CPU and convert to Ymir format."""
            cpu_matrix = self.matrix_backend.to_cpu(gpu_matrix)
            return self.from_numpy_matrix(cpu_matrix)

        def matrix_gpu_multiply(a, b):
            """Perform matrix multiplication on GPU (if available)."""
            # Convert inputs if they're Python lists
            if self.is_matrix(a):
                a = self.to_numpy_matrix(a)
            if self.is_matrix(b):
                b = self.to_numpy_matrix(b)

            # Move to GPU if available
            if self.matrix_backend.is_gpu_available():
                a_gpu = self.matrix_backend.to_gpu(a)
                b_gpu = self.matrix_backend.to_gpu(b)
                result_gpu = self.matrix_backend.matmul(a_gpu, b_gpu)
                result = self.matrix_backend.to_cpu(result_gpu)
            else:
                result = self.matrix_backend.matmul(a, b)

            return self.from_numpy_matrix(result)

        self.global_scope["transpose"] = matrix_transpose
        self.global_scope["det"] = matrix_determinant
        self.global_scope["inverse"] = matrix_inverse
        self.global_scope["shape"] = matrix_shape
        self.global_scope["matrix_gpu_available"] = matrix_gpu_available
        self.global_scope["matrix_to_gpu"] = matrix_to_gpu
        self.global_scope["matrix_from_gpu"] = matrix_from_gpu
        self.global_scope["matrix_gpu_multiply"] = matrix_gpu_multiply

        # Concurrency functions
        def make_channel(buffer_size=0):
            """Create a new channel for concurrent communication."""
            return self.concurrency_runtime.create_channel(Any, buffer_size)

        self.global_scope["make_channel"] = make_channel

        # HTTP client functions
        def http_get(url: str, headers: dict = None):
            """Perform HTTP GET request."""
            import asyncio

            client = get_http_client()
            return self.concurrency_runtime.run_until_complete(client.get(url, headers))

        def http_post(url: str, data: str = None, json_data: Any = None, headers: dict = None):
            """Perform HTTP POST request."""
            import asyncio

            client = get_http_client()
            return self.concurrency_runtime.run_until_complete(client.post(url, data, json_data, headers))

        # HTTP server classes
        self.global_scope["http_get"] = http_get
        self.global_scope["http_post"] = http_post
        self.global_scope["HTTPServer"] = HTTPServer
        self.global_scope["Request"] = Request
        self.global_scope["Response"] = Response

        # Add ALL functions from the math module
        for name, func in math.__dict__.items():
            if callable(func) and not name.startswith("__"):
                self.global_scope[name] = func

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
        # Don't try to access .body on Module objects
        if hasattr(main_module, "body"):
            self.logger.debug(f"Main module body: {main_module.body}")
        else:
            self.logger.debug(f"Main module exports: {main_module.exports}")

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

    def load_module(self, file_path: str, project_root: str, is_entry_point: bool = False) -> Module:
        canonical_path = os.path.realpath(file_path)
        if canonical_path in self.loaded_modules:
            self.logger.debug(f"Returning cached module for path: {canonical_path}")
            return self.loaded_modules[canonical_path]

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
        module_body = ast
        module_name = None
        for node in ast:
            if isinstance(node, ModuleDef):
                module_body = node.body
                module_name = node.name
                break
        if module_name is None:
            raise SyntaxError(f"Module name not defined in {file_path}")
        self.logger.debug(f"Module name: {module_name}")

        # Create a Module object to hold exports and cache it to handle cycles
        module_obj = Module(module_name)
        self.loaded_modules[canonical_path] = module_obj

        self.logger.debug(f"Module: {module_obj}")
        # First pass: register all classes and functions
        for node in module_body:
            if isinstance(node, (ClassDef, ExceptionDef)):
                self.logger.debug(f"[load_module] Registering class: {node.name}")
                class_obj = self.evaluate_exception_def(node)
                module_obj.exports[node.name] = class_obj
                self.global_scope[f"{module_name}.{node.name}"] = class_obj
            elif isinstance(node, FunctionDef):
                self.logger.debug(f"[load_module] Registering function: {node.name}")
                module_obj.exports[node.name] = node
                self.global_scope[f"{module_name}.{node.name}"] = node
            elif isinstance(node, ExportDef):
                if isinstance(node.value, FunctionDef):
                    func_node = node.value
                    self.logger.debug(f"[load_module] Registering exported function: {func_node.name}")
                    module_obj.exports[func_node.name] = func_node
                    self.global_scope[f"{module_name}.{func_node.name}"] = func_node

        # Second pass: process imports and exports
        for node in module_body:
            if isinstance(node, ModuleDef):
                continue
            if isinstance(node, ImportDef):
                self.process_import(node.module_name, project_root)
            elif isinstance(node, ExportDef):
                # Functions are handled in the first pass
                if not isinstance(node.value, FunctionDef):
                    self.logger.debug(f"[load_module] Exporting: {node.name}")
                    value = self.evaluate(node.value)
                    if isinstance(value, str) and value in self.global_scope:
                        value = self.global_scope[value]
                    module_obj.exports[node.name] = value
            elif is_entry_point:
                self.logger.debug(f"[load_module] Evaluating (entry point): {type(node)} - {repr(node)}")
                self.evaluate(node)
        return module_obj

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

            # Handle array element assignment (e.g., arr[0] = value)
            if isinstance(node.target, ArrayAccess):
                array_val = self.evaluate_expression(node.target.array)
                index_val = self.evaluate_expression(node.target.index)
                # Convert index to integer since Python lists require integer indices
                if isinstance(index_val, float):
                    index_val = int(index_val)
                # Perform the assignment
                array_val[index_val] = value
                return value

            # Handle attribute assignment (e.g., self.count = value)
            if type(node.target).__name__ == "MethodCall":
                # Attribute assignment
                instance = self.evaluate_expression(node.target.instance)
                setattr(instance, node.target.method_name, value)
                return value

            # Handle regular variable assignment
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
        elif isinstance(node, SpawnStatement):
            return self.evaluate_spawn_statement(node)
        elif isinstance(node, ModuleDef):
            for stmt in node.body:
                self.evaluate(stmt)
        elif isinstance(node, ReturnStatement):
            self.logger.debug(f"[evaluate] Handling ReturnStatement: {repr(node)}")
            value = self.evaluate_expression(node.expression)
            raise ReturnSignal(value)
        elif type(node).__name__ == "ImportDef":
            # No-op for import statements (already handled by load_standard_library)
            return None
        elif isinstance(node, BinaryOp):
            return self.evaluate_expression(node)
        elif type(node).__name__ == "MethodCall":
            # Handle method calls as statements (e.g., counter.increment())
            return self.evaluate_expression(node)
        else:
            self.logger.debug(f"[evaluate] Unknown node type: {type(node)} - {repr(node)}")
            raise TypeError(f"Unknown AST node type: {type(node)}")

    def evaluate_expression(self, node: ASTNode) -> Any:
        self.logger.debug(f"[evaluate_expression] ENTRY: node={node}, type={type(node)}")
        self.logger.debug(f"[evaluate_expression] Node type: {type(node)} - {repr(node)}")
        if isinstance(node, int):
            return node
        elif isinstance(node, float):
            return node
        elif isinstance(node, str):
            if node in self.local_scope:
                value = self.local_scope[node]
                self.logger.debug(f"[evaluate_expression] Variable '{node}' in local_scope -> {value}")
                return value
            elif node in self.global_scope:
                value = self.global_scope[node]
                self.logger.debug(f"[evaluate_expression] Variable '{node}' in global_scope -> {value}")
                if isinstance(value, Module):
                    return value
                return value
            # If not a variable, treat as string literal
            self.logger.debug(f"[evaluate_expression] String literal: {node}")
            return node
        elif isinstance(node, ArrayAccess):
            array_val = self.evaluate_expression(node.array)
            index_val = self.evaluate_expression(node.index)
            # Convert index to integer since Python lists require integer indices
            if isinstance(index_val, float):
                index_val = int(index_val)
            return array_val[index_val]
        elif hasattr(node, "elements") and type(node).__name__ == "ArrayLiteral":
            # ArrayLiteral node
            elements = [self.evaluate_expression(element) for element in node.elements]
            self.logger.debug(f"[evaluate_expression] ArrayLiteral: {elements}")
            return elements
        elif hasattr(node, "func_name") and hasattr(node, "args"):
            # FunctionCall node (for exception instantiation like ChildError("message"))
            func_name = node.func_name
            args = [self.evaluate_expression(arg) for arg in node.args]
            self.logger.debug(f"[FunctionCall] func_name: {repr(func_name)}")

            # Handle module access in function calls (e.g., stdlib.math.add)
            if "." in func_name:
                module_parts = func_name.split(".")
                if len(module_parts) >= 2:
                    module_name = ".".join(module_parts[:-1])
                    method_name = module_parts[-1]
                    if module_name in self.global_scope:
                        module_obj = self.global_scope[module_name]
                        if isinstance(module_obj, Module):
                            # It's a Module object, look in its exports
                            if method_name in module_obj.exports:
                                export = module_obj.exports[method_name]
                                if callable(export):
                                    return export(*args)
                                else:
                                    return export
                        # Try to find the function in the module's global scope
                        fq_name = f"{module_name}.{method_name}"
                        if fq_name in self.global_scope:
                            func = self.global_scope[fq_name]
                            if callable(func):
                                return func(*args)
                            else:
                                return func

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
                elif isinstance(obj, ClassDef):
                    # Class instantiation: create instance and call __init__
                    instance = type("Instance", (), {})()  # Create a simple object
                    instance.__class__.__name__ = func_name
                    instance._ymir_class_def = obj  # Store reference to ClassDef for method lookup

                    # Find the __init__ method
                    init_method = None
                    for method in obj.methods:
                        if method.name == "__init__":
                            init_method = method
                            break

                    # Call __init__ if it exists
                    if init_method:
                        # Save current scope
                        prev_local_scope = self.local_scope.copy()

                        # Add 'self' and parameters to local scope
                        self.local_scope["self"] = instance
                        for param, arg in zip(init_method.params[1:], args):  # Skip 'self' parameter
                            self.local_scope[param] = arg

                        # Execute __init__ body
                        for stmt in init_method.body:
                            self.evaluate(stmt)

                        # Restore scope
                        self.local_scope = prev_local_scope

                    return instance
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
            elif isinstance(node.expression, float):
                return node.expression
            elif isinstance(node.expression, str):
                if node.expression in self.local_scope:
                    value = self.local_scope[node.expression]
                    self.logger.debug(f"[evaluate_expression] Variable '{node.expression}' in local_scope -> {value}")
                    return value
                elif node.expression in self.global_scope:
                    value = self.global_scope[node.expression]
                    self.logger.debug(f"[evaluate_expression] Variable '{node.expression}' in global_scope -> {value}")
                    if isinstance(value, Module):
                        return value
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
                # Handle matrix addition
                if self.is_matrix(left) and self.is_matrix(right):
                    result = self.matrix_operation(left, right, "+")
                # Handle array concatenation
                elif isinstance(left, list) and isinstance(right, list):
                    result = left + right
                # Handle string + number concatenation
                elif isinstance(left, str) and isinstance(right, (int, float)):
                    result = left + str(right)
                elif isinstance(left, (int, float)) and isinstance(right, str):
                    result = str(left) + right
                # If either side is an exception, convert to string for concatenation
                elif isinstance(left, BaseException):
                    left = str(left)
                    result = left + right
                elif isinstance(right, BaseException):
                    right = str(right)
                    result = left + right
                else:
                    result = left + right
            elif node.operator == "-":
                # Handle matrix subtraction
                if self.is_matrix(left) and self.is_matrix(right):
                    result = self.matrix_operation(left, right, "-")
                else:
                    result = left - right
            elif node.operator == "*":
                # Handle matrix elementwise multiplication
                if self.is_matrix(left) and self.is_matrix(right):
                    result = self.matrix_operation(left, right, "*")
                # Handle string repetition
                elif isinstance(left, str) and isinstance(right, int):
                    result = left * right
                elif isinstance(left, int) and isinstance(right, str):
                    result = left * right
                else:
                    result = left * right
            elif node.operator == "@":
                # Handle matrix multiplication
                if self.is_matrix(left) and self.is_matrix(right):
                    result = self.matrix_operation(left, right, "@")
                else:
                    raise ValueError("Matrix multiplication (@) can only be used with matrices")
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
        elif isinstance(node, ChannelSend):
            # Channel send operation: channel <- value
            channel = self.evaluate_expression(node.channel)
            value = self.evaluate_expression(node.value)
            # Send is async, so we need to run it in the event loop
            import asyncio

            asyncio.create_task(channel.send(value))
            self.logger.debug(f"[evaluate_expression] ChannelSend: sent {value} to channel")
            return None
        elif isinstance(node, ChannelReceive):
            # Channel receive operation: <- channel
            channel = self.evaluate_expression(node.channel)
            # Receive is async, so we need to run it in the event loop
            import asyncio

            loop = self.concurrency_runtime.loop
            if loop and loop.is_running():
                # If we're already in an async context, create a task
                future = asyncio.ensure_future(channel.receive())
                return future
            else:
                # Run synchronously
                return self.concurrency_runtime.run_until_complete(channel.receive())
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
            # This handles all dot-notation access, including module functions and constants.
            instance = self.evaluate_expression(node.instance)

            # Special case for __str__ on exceptions
            if isinstance(instance, BaseException) and node.method_name == "__str__":
                return str(instance)

            # --- STRING METHODS: Comprehensive Python-like API ---
            if isinstance(instance, str):
                # Basic transformations
                if node.method_name == "upper":
                    return instance.upper()
                elif node.method_name == "lower":
                    return instance.lower()
                elif node.method_name == "capitalize":
                    return instance.capitalize()
                elif node.method_name == "title":
                    return instance.title()
                elif node.method_name == "strip":
                    chars = self.evaluate_expression(node.args[0]) if node.args else None
                    return instance.strip(chars)
                elif node.method_name == "lstrip":
                    chars = self.evaluate_expression(node.args[0]) if node.args else None
                    return instance.lstrip(chars)
                elif node.method_name == "rstrip":
                    chars = self.evaluate_expression(node.args[0]) if node.args else None
                    return instance.rstrip(chars)

                # Search/check methods
                elif node.method_name == "startswith":
                    if len(node.args) < 1:
                        raise TypeError("startswith() takes at least 1 argument")
                    prefix = self.evaluate_expression(node.args[0])
                    start = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else 0
                    end = self.evaluate_expression(node.args[2]) if len(node.args) > 2 else len(instance)
                    return instance[start:end].startswith(prefix)
                elif node.method_name == "endswith":
                    if len(node.args) < 1:
                        raise TypeError("endswith() takes at least 1 argument")
                    suffix = self.evaluate_expression(node.args[0])
                    start = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else 0
                    end = self.evaluate_expression(node.args[2]) if len(node.args) > 2 else len(instance)
                    return instance[start:end].endswith(suffix)
                elif node.method_name == "find":
                    if len(node.args) < 1:
                        raise TypeError("find() takes at least 1 argument")
                    sub = self.evaluate_expression(node.args[0])
                    start = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else 0
                    end = self.evaluate_expression(node.args[2]) if len(node.args) > 2 else len(instance)
                    return instance.find(sub, start, end)
                elif node.method_name == "rfind":
                    if len(node.args) < 1:
                        raise TypeError("rfind() takes at least 1 argument")
                    sub = self.evaluate_expression(node.args[0])
                    start = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else 0
                    end = self.evaluate_expression(node.args[2]) if len(node.args) > 2 else len(instance)
                    return instance.rfind(sub, start, end)
                elif node.method_name == "index":
                    if len(node.args) < 1:
                        raise TypeError("index() takes at least 1 argument")
                    sub = self.evaluate_expression(node.args[0])
                    start = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else 0
                    end = self.evaluate_expression(node.args[2]) if len(node.args) > 2 else len(instance)
                    return instance.index(sub, start, end)
                elif node.method_name == "count":
                    if len(node.args) < 1:
                        raise TypeError("count() takes at least 1 argument")
                    sub = self.evaluate_expression(node.args[0])
                    start = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else 0
                    end = self.evaluate_expression(node.args[2]) if len(node.args) > 2 else len(instance)
                    return instance.count(sub, start, end)
                elif node.method_name == "contains":
                    if len(node.args) != 1:
                        raise TypeError("contains() takes exactly 1 argument")
                    sub = self.evaluate_expression(node.args[0])
                    return sub in instance

                # Manipulation methods
                elif node.method_name == "split":
                    sep = self.evaluate_expression(node.args[0]) if node.args else None
                    maxsplit = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else -1
                    return instance.split(sep, maxsplit)
                elif node.method_name == "replace":
                    if len(node.args) < 2:
                        raise TypeError("replace() takes at least 2 arguments")
                    old = self.evaluate_expression(node.args[0])
                    new = self.evaluate_expression(node.args[1])
                    count = self.evaluate_expression(node.args[2]) if len(node.args) > 2 else -1
                    return instance.replace(old, new, count)
                elif node.method_name == "join":
                    if len(node.args) != 1:
                        raise TypeError("join() takes exactly 1 argument")
                    iterable = self.evaluate_expression(node.args[0])
                    # Convert all elements to strings
                    str_items = [str(item) for item in iterable]
                    return instance.join(str_items)
                elif node.method_name == "format":
                    args = [self.evaluate_expression(arg) for arg in node.args]
                    return instance.format(*args)

                # Validation methods
                elif node.method_name == "isdigit":
                    return instance.isdigit()
                elif node.method_name == "isalpha":
                    return instance.isalpha()
                elif node.method_name == "isalnum":
                    return instance.isalnum()
                elif node.method_name == "isspace":
                    return instance.isspace()
                elif node.method_name == "isupper":
                    return instance.isupper()
                elif node.method_name == "islower":
                    return instance.islower()

                # Utility methods
                elif node.method_name == "repeat":
                    if len(node.args) != 1:
                        raise TypeError("repeat() takes exactly 1 argument")
                    n = self.evaluate_expression(node.args[0])
                    return instance * int(n)
                elif node.method_name == "reverse":
                    return instance[::-1]
                elif node.method_name == "slice":
                    if len(node.args) < 1:
                        raise TypeError("slice() takes at least 1 argument")
                    start = self.evaluate_expression(node.args[0])
                    end = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else len(instance)
                    return instance[int(start) : int(end)]
            # --- END STRING METHODS ---

            # --- COLLECTION METHODS: Arrays with comprehensive API ---
            if isinstance(instance, list):
                if node.method_name == "append":
                    # Return a new list with the element added
                    if len(node.args) != 1:
                        raise TypeError("append() takes exactly one argument")
                    value = self.evaluate_expression(node.args[0])
                    return instance + [value]
                elif node.method_name == "push":
                    # Alias for append
                    if len(node.args) != 1:
                        raise TypeError("push() takes exactly one argument")
                    value = self.evaluate_expression(node.args[0])
                    return instance + [value]
                elif node.method_name == "pop":
                    # Return a new list with the last element removed
                    if len(instance) == 0:
                        raise IndexError("pop from empty list")
                    return instance[:-1]
                elif node.method_name == "insert":
                    # Return a new list with value inserted at index
                    if len(node.args) != 2:
                        raise TypeError("insert() takes exactly two arguments")
                    index = self.evaluate_expression(node.args[0])
                    value = self.evaluate_expression(node.args[1])
                    return instance[:index] + [value] + instance[index:]
                elif node.method_name == "remove":
                    # Return a new list with the first occurrence of value removed
                    if len(node.args) != 1:
                        raise TypeError("remove() takes exactly one argument")
                    value = self.evaluate_expression(node.args[0])
                    new_list = instance.copy()
                    new_list.remove(value)
                    return new_list
                elif node.method_name == "clear":
                    # Return an empty list
                    return []
                elif node.method_name == "extend":
                    # Return a new list with another list concatenated
                    if len(node.args) != 1:
                        raise TypeError("extend() takes exactly one argument")
                    other = self.evaluate_expression(node.args[0])
                    if not isinstance(other, list):
                        raise TypeError("extend() argument must be a list")
                    return instance + other

                # Aggregation methods
                elif node.method_name == "sum":
                    if not all(isinstance(x, (int, float)) for x in instance):
                        raise TypeError("sum() requires all elements to be numeric")
                    return sum(instance)
                elif node.method_name == "min":
                    if len(instance) == 0:
                        raise ValueError("min() arg is an empty sequence")
                    return min(instance)
                elif node.method_name == "max":
                    if len(instance) == 0:
                        raise ValueError("max() arg is an empty sequence")
                    return max(instance)
                elif node.method_name == "avg" or node.method_name == "mean":
                    if len(instance) == 0:
                        raise ValueError("avg() arg is an empty sequence")
                    if not all(isinstance(x, (int, float)) for x in instance):
                        raise TypeError("avg() requires all elements to be numeric")
                    return sum(instance) / len(instance)

                # Functional programming methods
                elif node.method_name == "filter":
                    if len(node.args) != 1:
                        raise TypeError("filter() takes exactly 1 argument")
                    predicate_expr = node.args[0]
                    result = []
                    for item in instance:
                        # Evaluate predicate with item
                        # For now, we expect a function call or lambda
                        if hasattr(predicate_expr, "func_name"):
                            pred_result = self.evaluate_function_call(predicate_expr.func_name, [item])
                        else:
                            # Try to evaluate as expression
                            self.local_scope["_item"] = item
                            pred_result = self.evaluate_expression(predicate_expr)
                            del self.local_scope["_item"]
                        if pred_result:
                            result.append(item)
                    return result
                elif node.method_name == "map":
                    if len(node.args) != 1:
                        raise TypeError("map() takes exactly 1 argument")
                    func_expr = node.args[0]
                    result = []
                    for item in instance:
                        if hasattr(func_expr, "func_name"):
                            mapped_value = self.evaluate_function_call(func_expr.func_name, [item])
                        else:
                            self.local_scope["_item"] = item
                            mapped_value = self.evaluate_expression(func_expr)
                            del self.local_scope["_item"]
                        result.append(mapped_value)
                    return result
                elif node.method_name == "reduce":
                    if len(node.args) < 1 or len(node.args) > 2:
                        raise TypeError("reduce() takes 1 or 2 arguments")
                    func_expr = node.args[0]
                    if len(instance) == 0:
                        if len(node.args) == 2:
                            return self.evaluate_expression(node.args[1])
                        raise TypeError("reduce() of empty sequence with no initial value")

                    if len(node.args) == 2:
                        accumulator = self.evaluate_expression(node.args[1])
                        start_idx = 0
                    else:
                        accumulator = instance[0]
                        start_idx = 1

                    for i in range(start_idx, len(instance)):
                        if hasattr(func_expr, "func_name"):
                            accumulator = self.evaluate_function_call(func_expr.func_name, [accumulator, instance[i]])
                        else:
                            self.local_scope["_acc"] = accumulator
                            self.local_scope["_item"] = instance[i]
                            accumulator = self.evaluate_expression(func_expr)
                            del self.local_scope["_acc"]
                            del self.local_scope["_item"]
                    return accumulator
                elif node.method_name == "forEach":
                    if len(node.args) != 1:
                        raise TypeError("forEach() takes exactly 1 argument")
                    func_expr = node.args[0]
                    for item in instance:
                        if hasattr(func_expr, "func_name"):
                            self.evaluate_function_call(func_expr.func_name, [item])
                        else:
                            self.local_scope["_item"] = item
                            self.evaluate_expression(func_expr)
                            del self.local_scope["_item"]
                    return None

                # Utility methods
                elif node.method_name == "sort":
                    return sorted(instance)
                elif node.method_name == "sortDesc":
                    return sorted(instance, reverse=True)
                elif node.method_name == "reverse":
                    return instance[::-1]
                elif node.method_name == "slice":
                    if len(node.args) < 1:
                        raise TypeError("slice() takes at least 1 argument")
                    start = self.evaluate_expression(node.args[0])
                    end = self.evaluate_expression(node.args[1]) if len(node.args) > 1 else len(instance)
                    return instance[int(start) : int(end)]
                elif node.method_name == "indexOf":
                    if len(node.args) != 1:
                        raise TypeError("indexOf() takes exactly 1 argument")
                    value = self.evaluate_expression(node.args[0])
                    try:
                        return instance.index(value)
                    except ValueError:
                        return -1
                elif node.method_name == "lastIndexOf":
                    if len(node.args) != 1:
                        raise TypeError("lastIndexOf() takes exactly 1 argument")
                    value = self.evaluate_expression(node.args[0])
                    try:
                        # Find last occurrence
                        for i in range(len(instance) - 1, -1, -1):
                            if instance[i] == value:
                                return i
                        return -1
                    except:
                        return -1
                elif node.method_name == "contains":
                    if len(node.args) != 1:
                        raise TypeError("contains() takes exactly 1 argument")
                    value = self.evaluate_expression(node.args[0])
                    return value in instance
                elif node.method_name == "unique":
                    # Preserve order while removing duplicates
                    seen = set()
                    result = []
                    for item in instance:
                        # Use str representation for unhashable types
                        try:
                            if item not in seen:
                                seen.add(item)
                                result.append(item)
                        except TypeError:
                            item_str = str(item)
                            if item_str not in seen:
                                seen.add(item_str)
                                result.append(item)
                    return result
                elif node.method_name == "flatten":
                    # Flatten one level
                    result = []
                    for item in instance:
                        if isinstance(item, list):
                            result.extend(item)
                        else:
                            result.append(item)
                    return result
                elif node.method_name == "join":
                    if len(node.args) != 1:
                        raise TypeError("join() takes exactly 1 argument")
                    separator = self.evaluate_expression(node.args[0])
                    # Convert all elements to strings
                    str_items = [str(item) for item in instance]
                    return separator.join(str_items)
            # --- END COLLECTION METHODS ---

            if isinstance(instance, Module):
                if node.method_name in instance.exports:
                    export = instance.exports[node.method_name]
                    if isinstance(export, FunctionDef):
                        # It's a Ymir function defined in a module.
                        args = [self.evaluate_expression(arg) for arg in node.args]
                        return self.evaluate_function_call(export.name, args, module_context=instance)
                    elif callable(export):
                        # It's a callable python object (like a built-in).
                        if node.args:
                            args = [self.evaluate_expression(arg) for arg in node.args]
                            return export(*args)
                        else:
                            return export  # It's a reference to a callable.
                    else:
                        # It's a constant.
                        return export
                else:
                    raise AttributeError(f"Module '{instance.name}' has no export named '{node.method_name}'")

            # Handle custom class instances
            elif hasattr(instance, "_ymir_class_def"):
                class_def = instance._ymir_class_def

                # First, check if it's a method in the ClassDef
                method_def = None
                for method in class_def.methods:
                    if method.name == node.method_name:
                        method_def = method
                        break

                if method_def:
                    # It's a method call
                    # Save current scope
                    prev_local_scope = self.local_scope.copy()

                    # Add 'self' and parameters to local scope
                    self.local_scope["self"] = instance
                    args = [self.evaluate_expression(arg) for arg in node.args]
                    for param, arg in zip(method_def.params[1:], args):  # Skip 'self' parameter
                        self.local_scope[param] = arg

                    # Execute method body
                    result = None
                    for stmt in method_def.body:
                        result = self.evaluate(stmt)
                        # Handle return statements
                        if isinstance(stmt, ReturnStatement):
                            break

                    # Restore scope
                    self.local_scope = prev_local_scope

                    return result
                else:
                    # Not a method, so treat as attribute access
                    if hasattr(instance, node.method_name):
                        return getattr(instance, node.method_name)
                    else:
                        raise AttributeError(
                            f"'{instance.__class__.__name__}' object has no attribute or method '{node.method_name}'"
                        )

            # Fallback for regular object method calls (if you add classes with methods).
            elif hasattr(instance, node.method_name):
                method = getattr(instance, node.method_name)
                if callable(method):
                    if node.args:
                        args = [self.evaluate_expression(arg) for arg in node.args]
                        return method(*args)
                    else:
                        return method
                else:
                    return method  # It's a property.
            else:
                raise AttributeError(f"'{type(instance).__name__}' object has no attribute '{node.method_name}'")
        return None

    def evaluate_function_call(self, func_name: str, args: List[Any], module_context: Optional[Module] = None) -> Any:
        """Evaluate a function call by interpreting the FunctionDef body."""
        func = None
        # First, try to find the function in the module context if provided
        if module_context:
            func = module_context.exports.get(func_name)
        # If not found in module context, try global scope
        if func is None:
            func = self.global_scope.get(func_name)

        if not isinstance(func, FunctionDef):
            # Try to find a python function in global scope
            if func_name in self.global_scope and callable(self.global_scope[func_name]):
                return self.global_scope[func_name](*args)
            raise TypeError(f"{func_name} is not a function definition")

        prev_local_scope = self.local_scope.copy()
        prev_global_scope = self.global_scope.copy()
        self.local_scope = {}
        # Inject module exports into global_scope for intra-module calls
        if module_context:
            self.global_scope = {**self.global_scope, **module_context.exports}
        for param, arg in zip(func.params, args):
            self.local_scope[param] = arg

        last_value = None
        try:
            for stmt in func.body:
                self.logger.debug(f"[evaluate_function_call] Evaluating stmt: {type(stmt)} - {repr(stmt)}")
                last_value = self.evaluate(stmt)
        except ReturnSignal as ret:
            self.logger.debug(f"[evaluate_function_call] Caught ReturnSignal with value: {ret.value}")
            self.local_scope = prev_local_scope
            self.global_scope = prev_global_scope
            # If the return value is an exception, convert to string
            if isinstance(ret.value, BaseException):
                return str(ret.value)
            return ret.value

        self.logger.debug(f"[evaluate_function_call] No return, returning last evaluated value: {last_value}")
        self.local_scope = prev_local_scope
        self.global_scope = prev_global_scope
        return last_value

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
        # First, check for the module in the standard library
        module_path_parts = module_name.split(".")
        if module_path_parts[0] == "stdlib":
            # The module name is like 'stdlib.math', so we look for 'math.ymr'
            # inside the stdlib directory.
            filename = f"{module_path_parts[-1]}.ymr"
            stdlib_file_path = os.path.join(self.standard_library_path, filename)
            if os.path.exists(stdlib_file_path):
                return stdlib_file_path

        # If not in stdlib, check project-relative paths
        # This assumes the CWD is the project root.
        project_file_path = os.path.join(*module_path_parts) + ".ymr"
        if os.path.exists(project_file_path):
            return project_file_path

        # Also check inside the 'ymir' source directory for project modules
        ymir_source_path = os.path.join("ymir", project_file_path)
        if os.path.exists(ymir_source_path):
            return ymir_source_path

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

    def evaluate_spawn_statement(self, node: SpawnStatement) -> str:
        """Evaluate a spawn statement to launch a concurrent task."""
        self.logger.debug(f"[evaluate_spawn_statement] Spawning: {node.call.func_name}")

        # Get the function to spawn
        func_name = node.call.func_name
        args = [self.evaluate_expression(arg) for arg in node.call.args]

        # Create a wrapper function that calls the Ymir function
        def task_wrapper():
            return self.evaluate_function_call(func_name, args)

        # Spawn the task
        task_id = self.concurrency_runtime.spawn(task_wrapper)
        self.logger.info(f"[evaluate_spawn_statement] Spawned task {task_id} for function {func_name}")
        return task_id

    def process_import(self, module_name: str, project_root: str):
        """Processes an import statement, creating nested module objects."""
        self.logger.debug(f"Processing import: {module_name}")
        import_path = self.resolve_import(module_name)

        imported_module_obj = self.load_module(import_path, project_root)

        parts = module_name.split(".")

        scope = self.global_scope
        for part in parts[:-1]:
            if part not in scope:
                scope[part] = Module(part)

            if isinstance(scope[part], Module):
                scope = scope[part].exports
            else:
                raise ImportError(f"Cannot import '{module_name}'; '{part}' is not a module.")

        scope[parts[-1]] = imported_module_obj

    def is_matrix(self, value: Any) -> bool:
        """Check if a value is a matrix (2D array of numbers)."""
        if not isinstance(value, list) or len(value) == 0:
            return False

        # Check if it's a 2D array
        if not isinstance(value[0], list):
            return False

        # Check if all elements are numbers
        for row in value:
            if not isinstance(row, list):
                return False
            for element in row:
                if not isinstance(element, (int, float)):
                    return False

        return True

    def to_numpy_matrix(self, value: Any) -> np.ndarray:
        """Convert a Ymir matrix (2D array) to backend array."""
        if self.is_matrix(value):
            return self.matrix_backend.to_array(value)
        else:
            raise ValueError("Value is not a valid matrix")

    def from_numpy_matrix(self, matrix: Any) -> List[List[float]]:
        """Convert backend array back to Ymir matrix format."""
        return self.matrix_backend.to_list(matrix)

    def matrix_operation(self, left: Any, right: Any, operation: str) -> Any:
        """Perform matrix operations using the matrix backend."""
        # Convert to backend arrays
        left_matrix = self.to_numpy_matrix(left)
        right_matrix = self.to_numpy_matrix(right)

        if operation == "+":
            result = self.matrix_backend.add(left_matrix, right_matrix)
        elif operation == "-":
            result = self.matrix_backend.subtract(left_matrix, right_matrix)
        elif operation == "*":
            result = self.matrix_backend.multiply(left_matrix, right_matrix)  # Elementwise multiplication
        elif operation == "@":
            result = self.matrix_backend.matmul(left_matrix, right_matrix)  # Matrix multiplication
        else:
            raise ValueError(f"Unsupported matrix operation: {operation}")

        return self.from_numpy_matrix(result)


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
