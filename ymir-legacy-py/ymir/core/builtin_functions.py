from llvmlite import ir


def create_builtin_functions(module):
    # Create a dictionary to hold built-in functions
    builtins = {}

    # Define printf from libc (variadic)
    func_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
    printf_func = ir.Function(module, func_type, name="printf")
    builtins["printf"] = printf_func

    # Define puts from libc (simpler, takes a string and prints with newline)
    func_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))])
    puts_func = ir.Function(module, func_type, name="puts")
    builtins["puts"] = puts_func
    builtins["print"] = puts_func  # Map print to puts for now

    # Define sprintf from libc (for converting int to string)
    sprintf_type = ir.FunctionType(
        ir.IntType(32), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))], var_arg=True
    )
    sprintf_func = ir.Function(module, sprintf_type, name="sprintf")
    builtins["sprintf"] = sprintf_func

    # We'll handle str() conversion in codegen

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
