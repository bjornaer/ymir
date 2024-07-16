from llvmlite import ir


def create_builtin_functions(module):
    # Create a dictionary to hold built-in functions
    builtins = {}

    # Define a print function
    func_type = ir.FunctionType(ir.VoidType(), [ir.PointerType(ir.IntType(8))])
    printf = ir.Function(module, func_type, name="print")
    builtins["print"] = printf

    func_type = ir.FunctionType(ir.VoidType(), [ir.PointerType(ir.IntType(8))])
    panic = ir.Function(module, func_type, name="panic")
    builtins["panic"] = panic

    # Define math functions
    func_type = ir.FunctionType(ir.DoubleType(), [ir.DoubleType()])
    builtins["sqrt"] = ir.Function(module, func_type, name="sqrt")
    builtins["sin"] = ir.Function(module, func_type, name="sin")
    builtins["cos"] = ir.Function(module, func_type, name="cos")
    builtins["tan"] = ir.Function(module, func_type, name="tan")

    func_type = ir.FunctionType(ir.DoubleType(), [ir.DoubleType(), ir.DoubleType()])
    builtins["pow"] = ir.Function(module, func_type, name="pow")

    # Define file I/O functions
    func_type = ir.FunctionType(
        ir.PointerType(ir.IntType(8)), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))]
    )
    builtins["open"] = ir.Function(module, func_type, name="open")
    func_type = ir.FunctionType(
        ir.IntType(32), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8)), ir.IntType(32)]
    )
    builtins["read"] = ir.Function(module, func_type, name="read")
    builtins["write"] = ir.Function(module, func_type, name="write")
    func_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))])
    builtins["close"] = ir.Function(module, func_type, name="close")

    # Define string functions
    func_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))])
    builtins["strlen"] = ir.Function(module, func_type, name="strlen")
    func_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
    builtins["strcmp"] = ir.Function(module, func_type, name="strcmp")
    func_type = ir.FunctionType(
        ir.PointerType(ir.IntType(8)), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))]
    )
    builtins["strcat"] = ir.Function(module, func_type, name="strcat")

    return builtins
