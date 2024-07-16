from typing import List


class Type:
    pass


class IntType(Type):
    def __str__(self) -> str:
        return "int"


class FloatType(Type):
    def __str__(self) -> str:
        return "float"


class StringType(Type):
    def __str__(self) -> str:
        return "string"


class BoolType(Type):
    def __str__(self) -> str:
        return "bool"


class ArrayType(Type):
    def __init__(self, element_type: Type):
        self.element_type = element_type

    def __str__(self) -> str:
        return f"array[{self.element_type}]"


class MapType(Type):
    def __init__(self, key_type: Type, value_type: Type):
        self.key_type = key_type
        self.value_type = value_type

    def __str__(self) -> str:
        return f"map[{self.key_type}]{self.value_type}"


class TupleType(Type):
    def __init__(self, element_types: List[Type]):
        self.element_types = element_types

    def __str__(self) -> str:
        return f"tuple[{', '.join(str(t) for t in self.element_types)}]"


class FunctionType(Type):
    def __init__(self, param_types: List[Type], return_type: Type):
        self.param_types = param_types
        self.return_type = return_type

    def __str__(self) -> str:
        param_types_str = ", ".join(str(t) for t in self.param_types)
        return f"({param_types_str}) -> {self.return_type}"


class ErrorType(Type):
    def __str__(self) -> str:
        return "error"


class NilType(Type):
    def __str__(self) -> str:
        return "nil"
