import ctypes
import functools
import logging
from typing import Any, Dict, List, Optional, Union

from llvmlite import binding, ir

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
    SelectStatement,
    SpawnStatement,
    StringLiteral,
    ThrowStatement,
    TryExceptStatement,
    TupleLiteral,
    UnaryOp,
    WhileStatement,
)
from ymir.core.builtin_functions import create_builtin_functions
from ymir.core.builtin_networking import create_networking_functions
from ymir.core.concurrency import get_runtime
from ymir.core.types import ArrayType, MapType, NilType, TupleType


class UnsupportedFeatureError(Exception):
    """Raised when LLVM codegen encounters a feature that requires interpreter fallback."""

    pass


class FeatureDetector:
    """Detects unsupported features in AST that require interpreter execution."""

    UNSUPPORTED_NODES = (
        SpawnStatement,  # Concurrency - spawn
        ChannelSend,  # Concurrency - channel send
        ChannelReceive,  # Concurrency - channel receive
        SelectStatement,  # Concurrency - select
    )

    @classmethod
    def check_ast(cls, ast_nodes: List[Any]) -> Optional[str]:
        """
        Check if AST contains unsupported features.
        Returns feature name if unsupported, None otherwise.
        """
        for node in ast_nodes:
            if isinstance(node, cls.UNSUPPORTED_NODES):
                return type(node).__name__
            # Recursively check nested structures
            if hasattr(node, "body") and isinstance(node.body, list):
                nested = cls.check_ast(node.body)
                if nested:
                    return nested
            if hasattr(node, "then_body"):
                nested = cls.check_ast(node.then_body)
                if nested:
                    return nested
            if hasattr(node, "else_body") and node.else_body:
                nested = cls.check_ast(node.else_body)
                if nested:
                    return nested
        return None


class CodeGenerator:
    def __init__(self):
        self.module = ir.Module(name="ymir_module")
        self.builder = None
        self.function = None
        self.global_scope: Dict[str, Any] = {}
        self.local_scope: Dict[str, Any] = {}
        self.builtins = create_builtin_functions(self.module)
        self.networking = create_networking_functions(self.module)
        # Note: async/await is unsupported in LLVM mode, will fall back to interpreter
        self.concurrency_runtime = get_runtime()

        # Track loop context for break/continue
        self.loop_stack = []  # Stack of (continue_block, break_block) tuples

        # Add exception handling tracking
        self.exception_handlers = []  # Stack of exception handlers
        self.current_try_block = None
        self.current_landing_pad = None
        self.logger = logging.getLogger("ymir.codegen")
        if not self.logger.hasHandlers():
            logging.basicConfig(level=logging.DEBUG)

    def generate_code(self, ast: List[Any]) -> str:
        self.logger.debug(f"[CodeGen] Generating code for AST: {ast}")

        # Check for unsupported features first
        unsupported = FeatureDetector.check_ast(ast)
        if unsupported:
            raise UnsupportedFeatureError(
                f"Feature '{unsupported}' requires interpreter execution. "
                f"Use --mode interpret or let auto mode fallback."
            )

        # Separate function definitions from top-level statements
        function_defs = []
        top_level_stmts = []

        for node in ast:
            if isinstance(node, ModuleDef):
                self.logger.warning(f"[CodeGen] Skipping unexpected ModuleDef node: {repr(node)}")
                continue
            if isinstance(node, FunctionDef):
                function_defs.append(node)
            else:
                top_level_stmts.append(node)

        # Check if user defined a main function and we have top-level statements
        user_has_main = any(hasattr(func, "name") and func.name == "main" for func in function_defs)
        self._rename_main = user_has_main and len(top_level_stmts) > 0

        # Generate all function definitions first
        for func_def in function_defs:
            self.logger.debug(f"[CodeGen] Visiting function def: {type(func_def)} - {repr(func_def)}")
            self.visit(func_def)

        # If there are top-level statements, wrap them in a main function
        if top_level_stmts:
            self.logger.debug(f"[CodeGen] Wrapping {len(top_level_stmts)} top-level statements in main")

            # Create the actual main entry point function
            func_type = ir.FunctionType(ir.VoidType(), [])
            entry_func = ir.Function(self.module, func_type, name="main")
            self.function = entry_func
            block = entry_func.append_basic_block(name="entry")
            self.builder = ir.IRBuilder(block)

            # Execute top-level statements
            for stmt in top_level_stmts:
                self.logger.debug(f"[CodeGen] Visiting top-level statement: {type(stmt)} - {repr(stmt)}")
                self.visit(stmt)

            # Add return
            if not self.builder.block.is_terminated:
                self.builder.ret_void()

        return str(self.module)

    @functools.lru_cache(maxsize=128)
    def visit(self, node: Any):
        self.logger.debug(f"[CodeGen] In visit: {type(node)} - {repr(node)}")
        if isinstance(node, FunctionDef):
            self.visit_function_def(node)
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
        elif isinstance(node, Expression):
            return self.visit_expression(node)
        elif isinstance(node, BinaryOp):
            return self.visit_binary_op(node)
        elif isinstance(node, Assignment):
            return self.visit_assignment(node)
        elif isinstance(node, FunctionCall):
            return self.visit_function_call(node)
        elif hasattr(node, "__class__") and node.__class__.__name__ == "ReturnStatement":
            return self.visit_return_statement(node)
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
        return_type = self.get_ir_type(node.return_type)
        # Get parameter types from annotations if available
        param_types = []
        for param in node.params:
            if param in node.param_types:
                param_types.append(self.get_ir_type(node.param_types[param]))
            else:
                # Default to i32 if no type annotation
                param_types.append(ir.IntType(32))
        func_type = ir.FunctionType(return_type, param_types)

        # Store the original name for scope lookup, but potentially rename in LLVM
        original_name = node.name
        llvm_name = node.name

        # Check if we need to rename this function (stored in temp attribute by generate_code)
        if hasattr(self, "_rename_main") and self._rename_main and node.name == "main":
            llvm_name = "_ymir_user_main"

        func = ir.Function(self.module, func_type, name=llvm_name)
        self.function = func
        self.global_scope[original_name] = func  # Store with original name for lookups
        if llvm_name != original_name:
            self.global_scope[llvm_name] = func  # Also store with LLVM name
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        for param, arg in zip(node.params, func.args):
            arg.name = param
            self.local_scope[param] = arg
        for statement in node.body:
            self.visit(statement)
        # Add return statement if needed
        if not self.builder.block.is_terminated:
            if return_type == ir.VoidType():
                self.builder.ret_void()
            else:
                # If there's no explicit return and the function is non-void, return 0/null
                if isinstance(return_type, ir.PointerType):
                    self.builder.ret(ir.Constant(return_type, None))
                elif isinstance(return_type, ir.IntType):
                    self.builder.ret(ir.Constant(return_type, 0))
                elif isinstance(return_type, ir.DoubleType):
                    self.builder.ret(ir.Constant(return_type, 0.0))
                else:
                    self.builder.ret_void()

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
        # Handle None (no return type) as void
        if ymir_type is None:
            return ir.VoidType()
        elif isinstance(ymir_type, str):
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
            # Handle Type objects from ymir.core.types
            type_name = type(ymir_type).__name__
            if type_name == "IntType":
                return ir.IntType(32)
            elif type_name == "FloatType":
                return ir.DoubleType()
            elif type_name == "StringType":
                return ir.PointerType(ir.IntType(8))
            elif type_name == "BoolType":
                return ir.IntType(1)
            elif type_name == "VoidType":
                return ir.VoidType()
            elif type_name == "NilType":
                return ir.VoidType()
            elif type_name == "AnyType":
                return ir.PointerType(ir.IntType(8))  # Generic pointer
            else:
                raise TypeError(f"Unknown type: {ymir_type} (type name: {type_name})")

    def visit_if_statement(self, node: IfStatement):
        """Generate code for if-else statements."""
        cond_val = self.visit_expression(node.condition)

        # Convert to boolean if needed
        if not isinstance(cond_val.type, ir.IntType) or cond_val.type.width != 1:
            # Compare with zero for boolean conversion
            if isinstance(cond_val.type, ir.IntType):
                cond_val = self.builder.icmp_signed("!=", cond_val, ir.Constant(cond_val.type, 0))
            elif isinstance(cond_val.type, ir.DoubleType):
                cond_val = self.builder.fcmp_ordered("!=", cond_val, ir.Constant(cond_val.type, 0.0))

        # Create basic blocks
        then_block = self.function.append_basic_block(name="if.then")
        else_block = self.function.append_basic_block(name="if.else") if node.else_body else None
        merge_block = self.function.append_basic_block(name="if.end")

        # Branch based on condition
        if else_block:
            self.builder.cbranch(cond_val, then_block, else_block)
        else:
            self.builder.cbranch(cond_val, then_block, merge_block)

        # Generate then block
        self.builder.position_at_end(then_block)
        for stmt in node.then_body:
            self.visit(stmt)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)

        # Generate else block if present
        if else_block:
            self.builder.position_at_end(else_block)
            for stmt in node.else_body:
                self.visit(stmt)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)

        # Continue in merge block
        self.builder.position_at_end(merge_block)

    def visit_while_statement(self, node: WhileStatement):
        """Generate code for while loops."""
        # Create basic blocks
        cond_block = self.function.append_basic_block(name="while.cond")
        body_block = self.function.append_basic_block(name="while.body")
        end_block = self.function.append_basic_block(name="while.end")

        # Push loop context for break/continue
        self.loop_stack.append((cond_block, end_block))

        # Jump to condition
        self.builder.branch(cond_block)

        # Generate condition block
        self.builder.position_at_end(cond_block)
        cond_val = self.visit_expression(node.condition)

        # Convert to boolean
        if not isinstance(cond_val.type, ir.IntType) or cond_val.type.width != 1:
            if isinstance(cond_val.type, ir.IntType):
                cond_val = self.builder.icmp_signed("!=", cond_val, ir.Constant(cond_val.type, 0))

        self.builder.cbranch(cond_val, body_block, end_block)

        # Generate body block
        self.builder.position_at_end(body_block)
        for stmt in node.body:
            self.visit(stmt)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        # Pop loop context
        self.loop_stack.pop()

        # Continue in end block
        self.builder.position_at_end(end_block)

    def visit_for_cstyle_loop(self, node: ForCStyleLoop):
        """Generate code for C-style for loops: for(init; cond; incr) {...}"""
        # Execute initialization
        self.visit(node.init)

        # Create basic blocks
        cond_block = self.function.append_basic_block(name="for.cond")
        body_block = self.function.append_basic_block(name="for.body")
        incr_block = self.function.append_basic_block(name="for.incr")
        end_block = self.function.append_basic_block(name="for.end")

        # Push loop context (continue goes to increment, break goes to end)
        self.loop_stack.append((incr_block, end_block))

        # Jump to condition
        self.builder.branch(cond_block)

        # Generate condition block
        self.builder.position_at_end(cond_block)
        cond_val = self.visit_expression(node.condition)

        # Convert to boolean
        if not isinstance(cond_val.type, ir.IntType) or cond_val.type.width != 1:
            if isinstance(cond_val.type, ir.IntType):
                cond_val = self.builder.icmp_signed("!=", cond_val, ir.Constant(cond_val.type, 0))

        self.builder.cbranch(cond_val, body_block, end_block)

        # Generate body block
        self.builder.position_at_end(body_block)
        for stmt in node.body:
            self.visit(stmt)
        if not self.builder.block.is_terminated:
            self.builder.branch(incr_block)

        # Generate increment block
        self.builder.position_at_end(incr_block)
        self.visit_expression(node.increment)
        self.builder.branch(cond_block)

        # Pop loop context
        self.loop_stack.pop()

        # Continue in end block
        self.builder.position_at_end(end_block)

    def visit_for_in_loop(self, node: ForInLoop):
        """Generate code for for-in loops: for item in array {...}

        Supports compile-time known arrays (literals). Runtime arrays still
        require interpreter mode.
        """
        # Check if iterable is a compile-time known array (ArrayLiteral)
        if not isinstance(node.iterable, ArrayLiteral):
            raise UnsupportedFeatureError(
                "For-in loops over runtime arrays not yet supported in LLVM mode. "
                "Only array literals are supported. Use C-style for loops or interpreter mode."
            )

        # Get the array elements
        elements = node.iterable.elements
        if not elements:
            # Empty array, nothing to iterate
            return

        # Allocate a variable for the loop variable
        loop_var_type = ir.IntType(32)  # Default to int32, could be inferred
        loop_var_ptr = self.builder.alloca(loop_var_type, name=node.var)
        self.local_scope[node.var] = loop_var_ptr

        # Create basic blocks for loop
        cond_block = self.function.append_basic_block(name="forin.cond")
        body_block = self.function.append_basic_block(name="forin.body")
        end_block = self.function.append_basic_block(name="forin.end")

        # Push loop context
        self.loop_stack.append((cond_block, end_block))

        # Create an index variable to track position in array
        index_ptr = self.builder.alloca(ir.IntType(32), name=f"{node.var}_index")
        self.builder.store(ir.Constant(ir.IntType(32), 0), index_ptr)

        # Jump to condition
        self.builder.branch(cond_block)

        # Generate condition block: check if index < array length
        self.builder.position_at_end(cond_block)
        index_val = self.builder.load(index_ptr)
        array_len = ir.Constant(ir.IntType(32), len(elements))
        cond = self.builder.icmp_signed("<", index_val, array_len)
        self.builder.cbranch(cond, body_block, end_block)

        # Generate body block
        self.builder.position_at_end(body_block)

        # Load the current element from the array
        # For simplicity, evaluate elements dynamically and use a switch/select
        # This is a simplified approach - better would be to store array in memory
        index_load = self.builder.load(index_ptr)

        # Create a phi node or use select chain for element values
        # For now, use a simple approach: evaluate all elements and select based on index
        element_values = []
        for elem in elements:
            elem_val = self.visit_expression(elem)
            element_values.append(elem_val)

        # Use the first element type as the loop variable type
        if element_values:
            # Create a simple select chain for small arrays
            # For larger arrays, this becomes inefficient but works
            current_val = element_values[0]
            for i in range(1, len(element_values)):
                is_index = self.builder.icmp_signed("==", index_load, ir.Constant(ir.IntType(32), i))
                current_val = self.builder.select(is_index, element_values[i], current_val)

            # Store the selected value in the loop variable
            self.builder.store(current_val, loop_var_ptr)

        # Execute loop body
        for stmt in node.body:
            self.visit(stmt)

        # Increment index and loop back
        if not self.builder.block.is_terminated:
            index_next = self.builder.add(index_load, ir.Constant(ir.IntType(32), 1))
            self.builder.store(index_next, index_ptr)
            self.builder.branch(cond_block)

        # Pop loop context
        self.loop_stack.pop()

        # Continue in end block
        self.builder.position_at_end(end_block)

    def visit_expression(self, node: Expression) -> Union[ir.Value, ir.Constant]:
        """Visit and generate code for an expression node."""
        # Handle FunctionCall
        if isinstance(node, FunctionCall):
            return self.visit_function_call(node)

        # Handle BinaryOp
        if isinstance(node, BinaryOp):
            return self.visit_binary_op(node)

        # Handle UnaryOp
        if isinstance(node, UnaryOp):
            return self.visit_unary_op(node)

        # Handle ArrayAccess
        if isinstance(node, ArrayAccess):
            return self.visit_array_access(node)

        # Handle ArrayLiteral
        if isinstance(node, ArrayLiteral):
            return self.visit_array_literal(node)

        # Handle StringLiteral
        if hasattr(node, "value") and isinstance(node, StringLiteral):
            return self.visit_string_literal(node)

        # Handle Expression wrapper with nested expression
        if hasattr(node, "expression"):
            inner = node.expression
            if isinstance(inner, int):
                return ir.Constant(ir.IntType(32), inner)
            elif isinstance(inner, float):
                return ir.Constant(ir.DoubleType(), inner)
            elif isinstance(inner, str):
                # Variable reference
                return self._load_variable(inner)
            elif isinstance(inner, bool):
                return ir.Constant(ir.IntType(1), int(inner))
            elif isinstance(inner, NilType):
                return ir.Constant(ir.VoidType(), None)
            else:
                # Recursively handle nested expression
                return self.visit_expression(inner)

        # Handle direct constants
        if isinstance(node, int):
            return ir.Constant(ir.IntType(32), node)
        if isinstance(node, float):
            return ir.Constant(ir.DoubleType(), node)
        if isinstance(node, str):
            # Variable reference
            return self._load_variable(node)

        raise TypeError(f"Unsupported expression type: {type(node)}")

    def _load_variable(self, name: str) -> ir.Value:
        """Load a variable, handling pointer vs value correctly."""
        if name in self.local_scope:
            var = self.local_scope[name]
            # If it's a pointer (alloca), load it
            if isinstance(var.type, ir.PointerType):
                return self.builder.load(var, name=name)
            # Otherwise it's a direct value (function parameter)
            return var
        elif name in self.global_scope:
            var = self.global_scope[name]
            if hasattr(var, "type") and isinstance(var.type, ir.PointerType):
                return self.builder.load(var, name=name)
            return var
        else:
            raise NameError(f"Undefined variable: {name}")

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
        # Comparison operators
        elif node.operator == "==":
            return self.builder.icmp_signed("==", left, right, name="eqtmp")
        elif node.operator == "!=":
            return self.builder.icmp_signed("!=", left, right, name="netmp")
        elif node.operator == "<":
            return self.builder.icmp_signed("<", left, right, name="lttmp")
        elif node.operator == "<=":
            return self.builder.icmp_signed("<=", left, right, name="letmp")
        elif node.operator == ">":
            return self.builder.icmp_signed(">", left, right, name="gttmp")
        elif node.operator == ">=":
            return self.builder.icmp_signed(">=", left, right, name="getmp")
        else:
            raise ValueError(f"Unknown operator: {node.operator}")

    def visit_unary_op(self, node: UnaryOp) -> ir.Value:
        """Generate code for unary operations."""
        operand = self.visit_expression(node.operand)

        if node.operator == "-":
            # Negate
            if isinstance(operand.type, ir.IntType):
                return self.builder.neg(operand, name="negtmp")
            elif isinstance(operand.type, ir.DoubleType):
                return self.builder.fneg(operand, name="fnegtmp")
            else:
                raise TypeError(f"Cannot negate type: {operand.type}")
        elif node.operator == "!":
            # Logical not
            return self.builder.not_(operand, name="nottmp")
        elif node.operator == "+":
            # Unary plus is a no-op
            return operand
        else:
            raise ValueError(f"Unsupported unary operator: {node.operator}")

    def visit_array_access(self, node: ArrayAccess) -> ir.Value:
        """Generate code for array element access with bounds checking: arr[index]"""
        array = self.visit_expression(node.array)
        index = self.visit_expression(node.index)

        # For array types, add bounds checking
        if isinstance(array.type, ir.ArrayType):
            array_len = ir.Constant(ir.IntType(32), array.type.count)

            # Create blocks for bounds check
            check_block = self.function.append_basic_block(name="bounds_check")
            valid_block = self.function.append_basic_block(name="bounds_valid")
            error_block = self.function.append_basic_block(name="bounds_error")

            # Branch to check
            self.builder.branch(check_block)

            # Check if index >= 0 and index < length
            self.builder.position_at_end(check_block)
            index_non_neg = self.builder.icmp_signed(">=", index, ir.Constant(ir.IntType(32), 0))
            index_in_bounds = self.builder.icmp_signed("<", index, array_len)
            valid = self.builder.and_(index_non_neg, index_in_bounds)
            self.builder.cbranch(valid, valid_block, error_block)

            # Error block - for now, just return zero (in full implementation would throw exception)
            self.builder.position_at_end(error_block)
            # TODO: Properly throw out-of-bounds exception
            # For now, return a zero value of the element type
            zero_val = ir.Constant(array.type.element, 0)
            self.builder.ret(zero_val)

            # Valid block - perform actual access
            self.builder.position_at_end(valid_block)

        # GEP to get pointer to element
        element_ptr = self.builder.gep(array, [ir.Constant(ir.IntType(32), 0), index])
        # Load the element value
        return self.builder.load(element_ptr, name="arr_elem")

    def visit_assignment(self, node: Assignment) -> ir.AllocaInstr:
        value = self.visit_expression(node.value)

        # Check if variable already exists (reassignment)
        if node.target in self.local_scope:
            var_address = self.local_scope[node.target]
            self.builder.store(value, var_address)
            return var_address

        # New variable - create alloca
        if hasattr(node, "type") and node.type:
            var_type = self.get_ir_type(node.type)
            var_address = self.builder.alloca(var_type, name=node.target)
        else:
            var_address = self.builder.alloca(value.type, name=node.target)
        self.builder.store(value, var_address)
        self.local_scope[node.target] = var_address
        return var_address

    def visit_return_statement(self, node):
        """Handle return statements."""
        if hasattr(node, "expression") and node.expression is not None:
            return_value = self.visit_expression(node.expression)
            self.builder.ret(return_value)
        else:
            self.builder.ret_void()

    def visit_function_call(self, node: FunctionCall) -> ir.CallInstr:
        # Handle str() function specially for type conversion
        if node.func_name == "str":
            if len(node.args) != 1:
                raise ValueError("str() takes exactly 1 argument")
            arg = self.visit_expression(node.args[0])
            if isinstance(arg.type, ir.IntType):
                # Convert int to string using sprintf
                buf_size = 32
                buf = self.builder.alloca(ir.ArrayType(ir.IntType(8), buf_size), name="str_buf")
                buf_ptr = self.builder.gep(buf, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])

                # Create format string "%d"
                fmt_str = ir.Constant(ir.ArrayType(ir.IntType(8), 3), bytearray(b"%d\0"))
                fmt_global = ir.GlobalVariable(self.module, fmt_str.type, name=self.module.get_unique_name("fmt"))
                fmt_global.global_constant = True
                fmt_global.initializer = fmt_str
                fmt_ptr = self.builder.gep(fmt_global, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])

                # Call sprintf
                sprintf = self.builtins.get("sprintf")
                self.builder.call(sprintf, [buf_ptr, fmt_ptr, arg])
                return buf_ptr
            else:
                # For non-int types, just return the arg as-is for now
                return arg

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
        # Create a global constant string
        string_const = ir.Constant(
            ir.ArrayType(ir.IntType(8), len(string_value) + 1), bytearray(string_value.encode("utf8") + b"\0")
        )
        # Create a global variable to hold the string
        global_str = ir.GlobalVariable(self.module, string_const.type, name=self.module.get_unique_name("str"))
        global_str.global_constant = True
        global_str.initializer = string_const
        # Return a pointer to the first element of the array
        return self.builder.gep(global_str, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])

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

    def visit_break(self, node: Break):
        """Generate code for break statement."""
        if not self.loop_stack:
            raise SyntaxError("break outside loop")
        _, break_block = self.loop_stack[-1]
        self.builder.branch(break_block)

    def visit_continue(self, node: Continue):
        """Generate code for continue statement."""
        if not self.loop_stack:
            raise SyntaxError("continue outside loop")
        continue_block, _ = self.loop_stack[-1]
        self.builder.branch(continue_block)

    def visit_nil(self, _: NilType) -> ir.Constant:
        return ir.Constant(ir.VoidType(), None)  # Representing nil as void

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
