import ctypes
import os
import platform
import subprocess
from typing import Any, Dict, Optional

from llvmlite import binding, ir

from ymir.core.ast import (
    Assignment,
    ASTNode,
    Break,
    ClassDef,
    Continue,
    ExportDef,
    Expression,
    ForCStyleLoop,
    ForInLoop,
    FunctionDef,
    ImportDef,
    ModuleDef,
    WhileStatement,
)
from ymir.core.lexer import Lexer
from ymir.core.parser import Parser
from ymir.core.semantic_analyzer import SemanticAnalyzer
from ymir.core.type_checker import TypeChecker
from ymir.tools.codegen import CodeGenerator


class YmirInterpreter:
    def __init__(self):
        self.global_scope: Dict[str, Any] = {}
        self.local_scope: Dict[str, Any] = {}
        self.module_cache: Dict[str, ModuleDef] = {}
        self.standard_library_path = os.path.join(os.path.dirname(__file__), "stdlib")

    def execute(self, llvm_ir: str) -> None:
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
        self.load_standard_library()
        project_root = os.path.dirname(os.path.abspath(file_path))
        main_module = self.load_module(file_path, project_root, is_entry_point=True)

        code_generator = CodeGenerator()
        llvm_ir = code_generator.generate_code(main_module.body)

        self.execute(llvm_ir)

    def load_module(self, file_path: str, project_root: str, is_entry_point: bool = False) -> ModuleDef:
        with open(file_path, "r") as file:
            source_code = file.read()

        lexer = Lexer(source_code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        semantic_analyzer = SemanticAnalyzer()
        semantic_analyzer.analyze(ast)

        type_checker = TypeChecker()
        type_checker.check(ast)
        module_name = None

        for node in ast:
            if isinstance(node, ModuleDef):
                module_name = node.name
                break

        if module_name is None:
            raise SyntaxError(f"Module name not defined in {file_path}")

        module = ModuleDef(module_name, ast)
        self.module_cache[module_name] = module
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

    def evaluate_for_cstyle_loop(self, node: ForCStyleLoop) -> None:
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


class ContinueSignal(Exception):
    pass


class BreakSignal(Exception):
    pass
