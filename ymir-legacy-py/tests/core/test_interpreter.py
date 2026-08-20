from ymir.core.ast import ExportDef, Expression, FunctionDef, ModuleDef, ReturnStatement
from ymir.core.types import IntType
from ymir.interpreter import YmirInterpreter


def test_interpreter_moduledef_evaluation():
    # Create a simple module AST: module test { export x = 42 }
    export = ExportDef("x", Expression(42))
    module = ModuleDef("test", [export])
    interpreter = YmirInterpreter(verbosity="DEBUG")
    # Should not raise an error
    interpreter.evaluate(module)
    assert interpreter.global_scope["x"] == 42

    # Add a function and check it is registered
    func = FunctionDef("add", ["a", "b"], [IntType(), IntType()], IntType(), [ReturnStatement(Expression("a"))])
    module_with_func = ModuleDef("test", [export, func])
    interpreter2 = YmirInterpreter(verbosity="DEBUG")
    interpreter2.evaluate(module_with_func)
    assert "add" in interpreter2.global_scope
    assert interpreter2.global_scope["x"] == 42
