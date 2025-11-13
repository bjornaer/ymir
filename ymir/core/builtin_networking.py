# import socket
# import ctypes
from llvmlite import ir


def create_networking_functions(module):
    # Create a dictionary to hold networking functions
    networking = {}

    # Define networking functions
    func_type = ir.FunctionType(ir.PointerType(ir.IntType(8)), [ir.IntType(32), ir.IntType(32), ir.IntType(32)])
    networking["socket"] = ir.Function(module, func_type, name="socket")

    func_type = ir.FunctionType(
        ir.IntType(32), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8)), ir.IntType(32)]
    )
    networking["connect"] = ir.Function(module, func_type, name="connect")

    func_type = ir.FunctionType(
        ir.IntType(32), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8)), ir.IntType(32)]
    )
    networking["send"] = ir.Function(module, func_type, name="send")

    func_type = ir.FunctionType(
        ir.IntType(32), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8)), ir.IntType(32)]
    )
    networking["recv"] = ir.Function(module, func_type, name="recv")

    # Check if 'close' already exists in module (it might be defined by builtin_functions)
    try:
        close_func = module.get_global("close")
        networking["close"] = close_func
    except KeyError:
        # If not defined, create it
        func_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))])
        networking["close"] = ir.Function(module, func_type, name="close")

    return networking
