import ctypes
import functools
import logging
from typing import Any, Dict, List, Union

from llvmlite import binding, ir

from ymir.core.ast import (
    ArrayLiteral,
    Assignment,
    AsyncFunctionDef,
    AwaitExpression,
    BinaryOp,
    Break,
    ClassDef,
    ClassInstance,
    Continue,
    ExceptionDef,
    Expression,
    ForCStyleLoop,
    ForInLoop,
    FunctionCall,
    FunctionDef,
    IfStatement,
    ImportDef,
    MapLiteral,
    MethodCall,
    ModuleDef,
    StringLiteral,
    ThrowStatement,
    TryExceptStatement,
    TupleLiteral,
    WhileStatement,
)
from ymir.core.builtin_functions import create_builtin_functions
from ymir.core.builtin_networking import create_networking_functions
from ymir.core.types import ArrayType, MapType, NilType, TupleType
from ymir.tools.async_support import AsyncSupport


class CodeGenerator:
    def __init__(self):
        self.module = ir.Module(name="ymir_module")
        self.builder = None
        self.function = None
        self.global_scope: Dict[str, Any] = {}
        self.local_scope: Dict[str, Any] = {}
        self.builtins = create_builtin_functions(self.module)
        self.networking = create_networking_functions(self.module)
        self.async_support = AsyncSupport()

        # Add exception handling tracking
        self.exception_handlers = []  # Stack of exception handlers
        self.current_try_block = None
        self.current_landing_pad = None
        self.logger = logging.getLogger("ymir.codegen")
        if not self.logger.hasHandlers():
            logging.basicConfig(level=logging.DEBUG)

    def generate_code(self, ast: List[Any]) -> str:
        self.logger.debug(f"[CodeGen] Generating code for AST: {ast}")
        for node in ast:
            if isinstance(node, ModuleDef):
                self.logger.warning(f"[CodeGen] Skipping unexpected ModuleDef node: {repr(node)}")
                continue
            self.logger.debug(f"[CodeGen] Visiting node: {type(node)} - {repr(node)}")
            self.visit(node)
        return str(self.module)

    @functools.lru_cache(maxsize=128)
    def visit(self, node: Any):
        self.logger.debug(f"[CodeGen] In visit: {type(node)} - {repr(node)}")
        if isinstance(node, FunctionDef):
            self.visit_function_def(node)
        elif isinstance(node, AsyncFunctionDef):
            self.visit_async_function_def(node)
        elif isinstance(node, ClassDef):
            self.visit_class_def(node)
        elif isinstance(node, IfStatement):
            self.visit_if_statement(node)
        elif isinstance(node, WhileStatement):
            self.visit_while_statement(node)
        elif isinstance(node, ForCStyleLoop):
            self.visit_for_cstyle_loop(node)
        elif isinstance(node, ForInLoop):
            self.visit_for_in_loop(node)
        elif isinstance(node, Continue):
            self.visit_continue(node)
        elif isinstance(node, Break):
            self.visit_break(node)
        elif isinstance(node, AwaitExpression):
            return self.visit_await_expression(node)
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
        elif isinstance(node, TupleLiteral):
            return self.visit_tuple_literal(node)
        elif isinstance(node, MapLiteral):
            return self.visit_dictionary_literal(node)
        elif isinstance(node, ClassInstance):
            return self.visit_class_instance(node)
        elif isinstance(node, MethodCall):
            return self.visit_method_call(node)
        elif isinstance(node, NilType):
            return self.visit_nil(node)
        elif isinstance(node, TryExceptStatement):
            return self.visit_try_except_statement(node)
        elif isinstance(node, ThrowStatement):
            return self.visit_throw_statement(node)
        elif isinstance(node, ExceptionDef):
            return self.visit_exception_def(node)
        else:
            raise TypeError(f"Unknown AST node type: {type(node)}")

    def visit_function_def(self, node: FunctionDef):
        param_types = [ir.PointerType(ir.IntType(32)) for _ in node.params]
        func_type = ir.FunctionType(ir.VoidType(), param_types)
        return_type = self.get_ir_type(node.return_type)
        func = ir.Function(self.module, func_type, name=node.name)
        self.function = func
        self.global_scope[node.name] = func
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        for param, arg in zip(node.params, func.args):
            arg.name = param
            self.local_scope[param] = arg
        for statement in node.body:
            self.visit(statement)
        if return_type == ir.VoidType():
            self.builder.ret_void()
        else:
            self.builder.ret(self.visit_expression(node.body[-1]))

    def visit_class_def(self, node: ClassDef):
        class_name = node.name
        member_types = [self.get_ir_type(member["type"]) for member in node.members]  # Extract member types
        # class_type = ir.LiteralStructType(member_types)
        # class_ptr_type = ir.PointerType(class_type)

        # Create a structure type for the class
        class_struct = ir.global_context.get_identified_type(class_name)
        class_struct.set_body(*member_types)

        # Add class to the global scope
        self.global_scope[class_name] = class_struct

        # Handle methods
        for method in node.methods:
            self.visit(method)

        # Store methods in the class type
        for method in node.methods:
            func = self.global_scope[method.name]
            method_name = f"{class_name}.{method.name}"
            self.global_scope[method_name] = func

        # Allocate space for the class instance
        instance_alloc = self.builder.alloca(class_struct, name=class_name)
        self.local_scope[class_name] = instance_alloc

        # Initialize class members (default values)
        for idx, member in enumerate(node.members):
            member_name = member["name"]
            member_value = self.visit_expression(member["value"])
            member_ptr = self.builder.gep(
                instance_alloc, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], name=member_name
            )
            self.builder.store(member_value, member_ptr)
            self.local_scope[member_name] = member_ptr

    def get_ir_type(self, ymir_type: str) -> ir.Type:
        if isinstance(ymir_type, str):
            if ymir_type == "int":
                return ir.IntType(32)
            elif ymir_type == "float":
                return ir.DoubleType()
            elif ymir_type == "str":
                return ir.PointerType(ir.IntType(8))
            elif ymir_type == "bool":
                return ir.IntType(1)
            elif ymir_type == "void":
                return ir.VoidType()
            elif ymir_type == "error":
                return ir.PointerType(ir.IntType(8))  # Representing error as a pointer to char
            elif ymir_type == "nil":
                return ir.VoidType()  # Representing nil as void
        elif isinstance(ymir_type, ArrayType):
            element_type = self.get_ir_type(ymir_type.element_type)
            return ir.PointerType(element_type)
        elif isinstance(ymir_type, MapType):
            key_type = self.get_ir_type(ymir_type.key_type)
            value_type = self.get_ir_type(ymir_type.value_type)
            return ir.PointerType(ir.LiteralStructType([key_type, value_type]))
        elif isinstance(ymir_type, TupleType):
            element_types = [self.get_ir_type(t) for t in ymir_type.element_types]
            return ir.LiteralStructType(element_types)
        else:
            raise TypeError(f"Unknown type: {ymir_type}")

    def visit_if_statement(self, node: IfStatement):
        cond_val = self.visit_expression(node.condition)
        then_block = self.function.append_basic_block(name="then")
        else_block = self.function.append_basic_block(name="else")
        merge_block = self.function.append_basic_block(name="ifcont")
        self.builder.cbranch(cond_val, then_block, else_block)

        self.builder.position_at_end(then_block)
        for statement in node.then_body:
            self.visit(statement)
        self.builder.branch(merge_block)

        self.builder.position_at_end(else_block)
        if node.else_body:
            for statement in node.else_body:
                self.visit(statement)
        self.builder.branch(merge_block)

        self.builder.position_at_end(merge_block)

    def visit_while_statement(self, node: WhileStatement):
        cond_block = self.function.append_basic_block(name="cond")
        loop_block = self.function.append_basic_block(name="loop")
        after_block = self.function.append_basic_block(name="afterloop")

        self.builder.branch(cond_block)
        self.builder.position_at_end(cond_block)
        cond_val = self.visit_expression(node.condition)
        self.builder.cbranch(cond_val, loop_block, after_block)

        self.builder.position_at_end(loop_block)
        for statement in node.body:
            self.visit(statement)
        self.builder.branch(cond_block)

        self.builder.position_at_end(after_block)

    def visit_for_cstyle_loop(self, node: ForCStyleLoop):
        self.visit_expression(node.init)

        cond_block = self.function.append_basic_block(name="cond")
        loop_block = self.function.append_basic_block(name="loop")
        after_block = self.function.append_basic_block(name="afterloop")

        self.builder.branch(cond_block)
        self.builder.position_at_end(cond_block)
        cond_val = self.visit_expression(node.condition)
        self.builder.cbranch(cond_val, loop_block, after_block)

        self.builder.position_at_end(loop_block)
        self.continue_block = cond_block
        self.break_block = after_block
        for statement in node.body:
            self.visit(statement)
        self.visit_expression(node.increment)
        self.builder.branch(cond_block)

        self.builder.position_at_end(after_block)

    def visit_for_in_loop(self, node: ForInLoop):
        iterable = self.visit_expression(node.iterable)
        iterator = iter(iterable)  # iterable is a Python list or tuple

        loop_block = self.function.append_basic_block(name="loop")
        after_block = self.function.append_basic_block(name="afterloop")

        self.continue_block = loop_block
        self.break_block = after_block

        for item in iterator:
            self.local_scope[node.var] = item
            self.builder.branch(loop_block)
            self.builder.position_at_end(loop_block)
            for statement in node.body:
                self.visit(statement)
        self.builder.position_at_end(after_block)

    def visit_expression(self, node: Expression) -> Union[ir.Constant, Any, None]:
        if isinstance(node.expression, int):
            return ir.Constant(ir.IntType(32), node.expression)
        elif isinstance(node.expression, str):
            if node.expression in self.local_scope:
                return self.local_scope[node.expression]
            elif node.expression in self.global_scope:
                return self.global_scope[node.expression]
            raise NameError(f"Undefined variable: {node.expression}")
        elif isinstance(node.expression, bool):
            return ir.Constant(ir.IntType(1), int(node.expression))
        elif isinstance(node.expression, NilType):
            return ir.Constant(ir.VoidType(), None)  # Representing nil as void
        return None

    def visit_binary_op(self, node: BinaryOp):
        left = self.visit_expression(node.left)
        right = self.visit_expression(node.right)
        if node.operator == "+":
            return self.builder.add(left, right, name="addtmp")
        elif node.operator == "-":
            return self.builder.sub(left, right, name="subtmp")
        elif node.operator == "*":
            return self.builder.mul(left, right, name="multmp")
        elif node.operator == "/":
            return self.builder.sdiv(left, right, name="divtmp")
        elif node.operator == "**":
            return self.builder.call(self.builtins["pow"], [left, right], name="powtmp")
        elif node.operator == "//":
            return self.builder.sdiv(left, right, name="divtmp")
        elif node.operator == "++":
            return self.builder.add(left, ir.Constant(ir.IntType(32), 1), name="inc")
        elif node.operator == "--":
            return self.builder.sub(left, ir.Constant(ir.IntType(32), 1), name="dec")
        elif node.operator == "+=":
            return self.builder.add(left, right, name="addtmp")
        elif node.operator == "%":
            return self.builder.srem(left, right, name="modtmp")
        else:
            raise ValueError(f"Unknown operator: {node.operator}")

    def visit_assignment(self, node: Assignment) -> ir.AllocaInstr:
        value = self.visit_expression(node.value)
        if node.type:
            var_type = self.get_ir_type(node.type)
            var_address = self.builder.alloca(var_type, name=node.target)
        else:
            var_address = self.builder.alloca(value.type, name=node.target)
        self.builder.store(value, var_address)
        self.local_scope[node.target] = var_address
        return var_address

    def visit_function_call(self, node: FunctionCall) -> ir.CallInstr:
        func = self.local_scope.get(node.func_name) or self.global_scope.get(node.func_name)
        if not func:
            func = self.builtins.get(node.func_name)
            if not func:
                func = self.networking.get(node.func_name)
                if not func:
                    raise NameError(f"Undefined function: {node.func_name}")
        args = [self.visit_expression(arg) for arg in node.args]
        return self.builder.call(func, args, name="calltmp")

    def visit_array_literal(self, node: ArrayLiteral) -> ir.Constant:
        element_type = ir.IntType(32)  # Placeholder for element type
        array_type = ir.ArrayType(element_type, len(node.elements))
        array_value = ir.Constant(array_type, [self.visit_expression(element) for element in node.elements])
        return array_value

    def visit_string_literal(self, node: StringLiteral) -> ir.Constant:
        string_value = node.value.strip('"')
        return ir.Constant(
            ir.ArrayType(ir.IntType(8), len(string_value) + 1), bytearray(string_value.encode("utf8") + b"\0")
        )

    def visit_tuple_literal(self, node: TupleLiteral) -> ir.Constant:
        element_values = [self.visit_expression(element) for element in node.elements]
        tuple_type = ir.LiteralStructType([val.type for val in element_values])
        return ir.Constant(tuple_type, element_values)

    def visit_dictionary_literal(self, node: MapLiteral) -> ir.Constant:
        key_values = [(self.visit_expression(key), self.visit_expression(value)) for key, value in node.pairs.items()]
        dict_type = ir.LiteralStructType([ir.LiteralStructType([key.type, value.type]) for key, value in key_values])
        dict_value = ir.Constant(
            dict_type,
            [ir.Constant(ir.LiteralStructType([key.type, value.type]), [key, value]) for key, value in key_values],
        )
        return dict_value

    def visit_class_instance(self, node: ClassInstance) -> Dict[str, Any]:
        class_def: ClassDef = self.global_scope.get(node.class_name)
        if not class_def:
            raise NameError(f"Undefined class: {node.class_name}")
        instance = {}
        for method in class_def.methods:
            instance[method.name] = method
        return instance

    def visit_method_call(self, node: MethodCall) -> Any:
        instance = self.local_scope.get(node.instance) or self.global_scope.get(node.instance)
        if not instance:
            raise NameError(f"Undefined instance: {node.instance}")
        method = instance.get(node.method_name)
        if not method:
            raise NameError(f"Undefined method: {node.method_name}")
        args = [self.visit_expression(arg) for arg in node.args]
        local_scope_backup = self.local_scope.copy()
        self.local_scope = {param: arg for param, arg in zip(method.params, args)}
        result = None
        for statement in method.body:
            result = self.visit(statement)
        self.local_scope = local_scope_backup
        return result

    def visit_continue(self, _: Continue) -> None:
        self.builder.branch(self.continue_block)

    def visit_break(self, _: Break) -> None:
        self.builder.branch(self.break_block)

    def visit_nil(self, _: NilType) -> ir.Constant:
        return ir.Constant(ir.VoidType(), None)  # Representing nil as void

    def visit_async_function_def(self, node: AsyncFunctionDef):
        param_types = [ir.PointerType(ir.IntType(32)) for _ in node.params]
        return_type = self.get_ir_type(node.return_type)
        func_type = ir.FunctionType(return_type, param_types)
        func = ir.Function(self.module, func_type, name=node.name)
        self.function = func
        self.global_scope[node.name] = func
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        for param, arg in zip(node.params, func.args):
            arg.name = param
            self.local_scope[param] = arg
        for statement in node.body:
            self.visit(statement)
        if return_type == ir.VoidType():
            self.builder.ret_void()
        else:
            self.builder.ret(self.visit_expression(node.body[-1]))

        # Register the coroutine with the async support
        self.async_support.register_coroutine(node.name, self.async_support.create_coroutine(self.run_function, func))

    def run_function(self, func, *args):
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

    def visit_import_def(self, _: ImportDef):
        pass  # Handled during the module loading phase

    def visit_module_def(self, _: ModuleDef):
        pass  # Handled during the module loading phase

    def visit_try_except_statement(self, node: TryExceptStatement):
        """Generate LLVM IR for try-except-finally statements."""
        # Create basic blocks for the try, except clauses, finally, and continuation
        try_block = self.function.append_basic_block(name="try")
        except_blocks = []
        for _ in node.except_clauses:
            except_blocks.append(self.function.append_basic_block(name="except"))
        finally_block = None
        if node.finally_clause:
            finally_block = self.function.append_basic_block(name="finally")
        cont_block = self.function.append_basic_block(name="try_cont")

        # Save current exception handlers
        prev_handlers = self.exception_handlers

        # Set up exception handlers for this try block
        landing_pad = self.function.append_basic_block(name="landing_pad")
        self.exception_handlers.append(
            {
                "landing_pad": landing_pad,
                "except_blocks": except_blocks,
                "finally_block": finally_block,
                "except_clauses": node.except_clauses,
            }
        )

        # Branch to try block
        self.builder.branch(try_block)

        # Generate code for try block
        self.builder.position_at_end(try_block)
        self.current_try_block = try_block
        for stmt in node.try_block:
            self.visit(stmt)

        # If we get here normally (no exceptions), go to finally or cont
        if finally_block:
            self.builder.branch(finally_block)
        else:
            self.builder.branch(cont_block)

        # Set up landing pad for exception handling
        self.builder.position_at_end(landing_pad)
        # NOTE(@bjornaer): In a robust (TODO) implementation,
        # I plan to use LLVM's exception handling intrinsics
        # For simplicity, I'll just create a phi node to handle different exception types
        exception_var = self.builder.phi(ir.PointerType(ir.IntType(8)), name="exception")

        # Generate code for except blocks
        for i, (except_block, except_clause) in enumerate(zip(except_blocks, node.except_clauses)):
            self.builder.position_at_end(except_block)

            # Bind exception variable if needed
            if except_clause.exception_var:
                var_ptr = self.builder.alloca(ir.PointerType(ir.IntType(8)), name=except_clause.exception_var)
                self.builder.store(exception_var, var_ptr)
                self.local_scope[except_clause.exception_var] = var_ptr

            # Generate code for the except block
            for stmt in except_clause.except_block:
                self.visit(stmt)

            # Branch to finally or continuation
            if finally_block:
                self.builder.branch(finally_block)
            else:
                self.builder.branch(cont_block)

        # Generate code for finally block if present
        if finally_block:
            self.builder.position_at_end(finally_block)
            for stmt in node.finally_clause.finally_block:
                self.visit(stmt)
            self.builder.branch(cont_block)

        # Restore previous exception handlers
        self.exception_handlers = prev_handlers

        # Position at continuation block
        self.builder.position_at_end(cont_block)

    def visit_throw_statement(self, node: ThrowStatement):
        """Generate LLVM IR for throw statements."""
        # Generate the exception value
        exception_value = self.visit_expression(node.expression)

        # Call runtime function to handle throwing
        throw_func = self.module.get_global("throw_exception")
        if not throw_func:
            # Define the throw_exception function if not already defined
            throw_type = ir.FunctionType(ir.VoidType(), [ir.PointerType(ir.IntType(8))])
            throw_func = ir.Function(self.module, throw_type, name="throw_exception")

        # Call the throw function with the exception value
        self.builder.call(throw_func, [exception_value])

        # Branch to the nearest exception handler's landing pad
        if self.exception_handlers:
            handler = self.exception_handlers[-1]
            self.builder.branch(handler["landing_pad"])
        else:
            # If no handler, call panic
            panic_func = self.builtins.get("panic")
            if panic_func:
                self.builder.call(panic_func, [exception_value])
            # Unreachable code after throw with no handler
            self.builder.unreachable()

    def visit_exception_def(self, node: ExceptionDef):
        """Generate LLVM IR for exception class definitions."""
        # Create a struct type for the exception
        exception_struct = ir.global_context.get_identified_type(node.name)

        # If there's a base class, include its fields
        member_types = []
        if node.base_class:
            base_class = self.global_scope.get(node.base_class)
            if isinstance(base_class, ir.Type):
                # Get fields from base class if possible
                for field in base_class.elements:
                    member_types.append(field)

        # Add fields from this exception
        for member in node.members:
            if isinstance(member, dict) and "type" in member:
                member_type = self.get_ir_type(member["type"])
                member_types.append(member_type)

        # Set the body of the struct type
        exception_struct.set_body(*member_types)

        # Store the type in global scope
        self.global_scope[node.name] = exception_struct

        # Generate code for methods
        for method in node.methods:
            self.visit(method)
