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

        code_generator = CodeGenerator()
        llvm_ir = code_generator.generate_code(main_module.body)

        self.execute(llvm_ir)

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

        module_name = None

        for node in ast:
            if isinstance(node, ModuleDef):
                module_name = node.name
                break

        if module_name is None:
            raise SyntaxError(f"Module name not defined in {file_path}")

        self.logger.debug(f"Module name: {module_name}")

        module = ModuleDef(module_name, ast)
        self.module_cache[module_name] = module
        self.logger.debug(f"Module: {module}")
        for node in ast:
            if isinstance(node, ImportDef):
                import_path = self.resolve_import(node.module_name)
                self.load_module(import_path, project_root)
            if isinstance(node, ExportDef):
                self.global_scope[node.name] = self.evaluate(node.value)
            elif is_entry_point:
                self.evaluate(node)

        return module

    def evaluate(self, node: ASTNode) -> Any:
        """Evaluate an AST node.

        This function takes an AST node and evaluates it.

        Args:
            node: The AST node to evaluate

        The function performs the following steps:
        1. Evaluates the node based on its type
        2. Returns the result of the evaluation
        """
        if isinstance(node, FunctionDef):
            self.global_scope[node.name] = node
        elif isinstance(node, ClassDef):
            self.global_scope[node.name] = node
        elif isinstance(node, Expression):
            return self.evaluate_expression(node)
        elif isinstance(node, Assignment):
            self.global_scope[node.target] = self.evaluate_expression(node.value)
        elif isinstance(node, ExportDef):
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
        else:
            raise TypeError(f"Unknown AST node type: {type(node)}")

    def evaluate_expression(self, node: ASTNode) -> Any:
        if isinstance(node, int):
            return node
        elif isinstance(node, str):
            if node in self.local_scope:
                return self.local_scope[node]
            elif node in self.global_scope:
                return self.global_scope[node]
            raise NameError(f"Undefined variable: {node}")
        return None

    def evaluate_function_call(self, func_name: str, args: List[Any]) -> Any:
        """Evaluate a function call.

        This function takes a function name and a list of arguments, and evaluates the function call.

        Args:
            func_name: The name of the function to call
            args: List of arguments to pass to the function

        Returns:
            The result of the function call

        The function performs the following steps:
        1. Retrieves the function from the global scope
        2. Converts the arguments to the appropriate types
        3. Executes the function and returns the result
        """
        func = self.global_scope[func_name]
        return func(*args)

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
            # Execute the try block
            result = None
            for stmt in node.try_block:
                result = self.evaluate(stmt)
            return result
        except Exception as e:
            # Handle exceptions with except clauses
            for except_clause in node.except_clauses:
                # Check if the except clause should catch this exception
                if except_clause.exception_type is None or self.is_instance_of_exception(
                    e, self.evaluate_expression(except_clause.exception_type)
                ):
                    # Bind the exception to a variable if needed
                    if except_clause.exception_var:
                        self.local_scope[except_clause.exception_var] = e

                    # Execute the except block
                    result = None
                    for stmt in except_clause.except_block:
                        result = self.evaluate(stmt)
                    return result

            # Re-raise if no matching except clause
            raise
        finally:
            # Execute the finally clause if present
            if node.finally_clause:
                for stmt in node.finally_clause.finally_block:
                    self.evaluate(stmt)

    def evaluate_throw_statement(self, node: ThrowStatement) -> None:
        """Evaluate a throw statement."""
        exception = self.evaluate_expression(node.expression)
        raise exception

    def evaluate_exception_def(self, node: ExceptionDef) -> None:
        """Evaluate an exception class definition."""
        # Create a new exception class
        base_exception = Exception
        if node.base_class:
            base_exception = self.global_scope.get(node.base_class, Exception)

        # Define the new exception class
        exception_class = type(node.name, (base_exception,), {})

        # Add methods
        for method in node.methods:
            exception_class.__dict__[method.name] = method

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
