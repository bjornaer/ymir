from typing import Dict, List, Optional, Union

from ymir.core.types import Type


class ASTNode:
    pass


class FunctionDef(ASTNode):
    def __init__(
        self, name: str, params: List[str], param_types: List[Type], return_type: Optional[Type], body: List[ASTNode]
    ):
        self.name = name
        self.params = params
        self.param_types = param_types
        self.return_type = return_type
        self.body = body
        self.is_export = False


class ReturnStatement(ASTNode):
    def __init__(self, expression: ASTNode):
        self.expression = expression


class ClassDef(ASTNode):
    def __init__(self, name: str, base_class: Optional[str], methods: List[FunctionDef], members: List[Dict[str, str]]):
        self.name = name
        self.base_class = base_class
        self.methods = methods
        self.members = members


class IfStatement(ASTNode):
    def __init__(self, condition: ASTNode, then_body: List[ASTNode], else_body: Optional[List[ASTNode]]):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body


class WhileStatement(ASTNode):
    def __init__(self, condition: ASTNode, body: List[ASTNode]):
        self.condition = condition
        self.body = body


class Expression(ASTNode):
    def __init__(self, expression: Union[int, str]):
        self.expression = expression


class BinaryOp(ASTNode):
    def __init__(self, operator: str, left: ASTNode, right: ASTNode):
        self.operator = operator
        self.left = left
        self.right = right


class Assignment(ASTNode):
    def __init__(self, target: Union[str, Expression], value: ASTNode, var_type: Optional["Type"] = None):
        self.target = target
        self.value = value
        self.var_type = var_type


class FunctionCall(ASTNode):
    def __init__(self, func_name: str, args: List[ASTNode]):
        self.func_name = func_name
        self.args = args


class ArrayLiteral(ASTNode):
    def __init__(self, elements: List[ASTNode]):
        self.elements = elements


class StringLiteral(ASTNode):
    def __init__(self, value: str):
        self.value = value


class ClassInstance(ASTNode):
    def __init__(self, class_name: str):
        self.class_name = class_name


class MethodCall(ASTNode):
    def __init__(self, instance: str, method_name: str, args: List[ASTNode]):
        self.instance = instance
        self.method_name = method_name
        self.args = args


class TupleLiteral(ASTNode):
    def __init__(self, elements: List[ASTNode]):
        self.elements = elements


class MapLiteral(ASTNode):
    def __init__(self, pairs: Dict[ASTNode, ASTNode]):
        self.pairs = pairs


class ModuleDef(ASTNode):
    def __init__(self, name: str, body: List[ASTNode]):
        self.name = name
        self.body = body


class ExportDef(ASTNode):
    def __init__(self, name: str, value: ASTNode):
        self.name = name
        self.value = value


class ForInLoop(ASTNode):
    def __init__(self, var: str, iterable: ASTNode, body: List[ASTNode]):
        self.var = var
        self.iterable = iterable
        self.body = body


class ForCStyleLoop(ASTNode):
    def __init__(self, init: ASTNode, condition: ASTNode, increment: ASTNode, body: List[ASTNode]):
        self.init = init
        self.condition = condition
        self.increment = increment
        self.body = body


class Continue(ASTNode):
    pass


class Break(ASTNode):
    pass


class AsyncFunctionDef(FunctionDef):
    pass


class AwaitExpression(Expression):
    def __init__(self, expression: Expression):
        super().__init__(expression)


class ImportDef(ASTNode):
    def __init__(self, module_name: str):
        self.module_name = module_name


class TryExceptStatement(ASTNode):
    def __init__(
        self,
        try_block: List[ASTNode],
        except_clauses: List["ExceptClause"],
        finally_clause: Optional["FinallyClause"] = None,
    ):
        self.try_block = try_block
        self.except_clauses = except_clauses
        self.finally_clause = finally_clause


class ExceptClause(ASTNode):
    def __init__(
        self,
        except_block: List[ASTNode],
        exception_type: Optional[Expression] = None,
        exception_var: Optional[str] = None,
    ):
        self.except_block = except_block
        self.exception_type = exception_type
        self.exception_var = exception_var


class FinallyClause(ASTNode):
    def __init__(self, finally_block: List[ASTNode]):
        self.finally_block = finally_block


class ThrowStatement(ASTNode):
    def __init__(self, expression: Expression):
        self.expression = expression


class ExceptionDef(ASTNode):
    def __init__(
        self, name: str, methods: List[FunctionDef], members: List[Dict[str, str]], base_class: Optional[str] = None
    ):
        self.name = name
        self.base_class = base_class
        self.methods = methods
        self.members = members


class UnaryOp(ASTNode):
    """AST node for unary operations like ++, --, !, etc."""

    def __init__(self, operator: str, operand: Expression, postfix=False):
        self.operator = operator  # The operator (e.g., "++", "--", "!")
        self.operand = operand  # The operand expression
        self.postfix = postfix  # Whether this is a prefix (i++) or postfix (++i) operator

    def __str__(self):
        if self.postfix:
            return f"{self.operand}{self.operator}"
        else:
            return f"{self.operator}{self.operand}"


class ArrayAccess(ASTNode):
    def __init__(self, array: ASTNode, index: ASTNode):
        self.array = array
        self.index = index


# Concurrency AST Nodes


class SpawnStatement(ASTNode):
    """AST node for spawning a concurrent task: spawn functionCall()"""

    def __init__(self, call: FunctionCall):
        self.call = call


class ChannelSend(ASTNode):
    """AST node for sending to a channel: channel <- value"""

    def __init__(self, channel: ASTNode, value: ASTNode):
        self.channel = channel
        self.value = value


class ChannelReceive(ASTNode):
    """AST node for receiving from a channel: value <- channel or just <- channel"""

    def __init__(self, channel: ASTNode):
        self.channel = channel


class SelectStatement(ASTNode):
    """AST node for select statement (future implementation)"""

    def __init__(self, cases: List["SelectCase"]):
        self.cases = cases


class SelectCase(ASTNode):
    """AST node for a case in a select statement"""

    def __init__(self, operation: ASTNode, body: List[ASTNode]):
        self.operation = operation  # Either ChannelSend or ChannelReceive
        self.body = body
