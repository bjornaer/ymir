from abc import ABC, abstractmethod
from typing import List, Optional


class Type(ABC):
    """Base class for all types in Ymir."""

    @abstractmethod
    def __str__(self) -> str:
        pass

    def __eq__(self, other) -> bool:
        return type(self) is type(other)

    def __hash__(self) -> int:
        return hash(type(self))


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


class AnyType(Type):
    """Represents any type (for flexible type checking)."""

    def __str__(self) -> str:
        return "any"

    def __eq__(self, other) -> bool:
        return isinstance(other, AnyType)

    def __hash__(self) -> int:
        return hash(AnyType)


class ArrayType(Type):
    def __init__(self, element_type: Type):
        self.element_type = element_type

    def __str__(self) -> str:
        return f"array[{self.element_type}]"

    def __eq__(self, other) -> bool:
        return isinstance(other, ArrayType) and self.element_type == other.element_type

    def __hash__(self) -> int:
        return hash((ArrayType, self.element_type))


class MatrixType(Type):
    """Represents a matrix type (2D array of numbers)."""

    def __init__(self, element_type: Type = FloatType()):
        self.element_type = element_type

    def __str__(self) -> str:
        return f"matrix[{self.element_type}]"

    def __eq__(self, other) -> bool:
        return isinstance(other, MatrixType) and self.element_type == other.element_type

    def __hash__(self) -> int:
        return hash((MatrixType, self.element_type))


class MapType(Type):
    def __init__(self, key_type: Type, value_type: Type):
        self.key_type = key_type
        self.value_type = value_type

    def __str__(self) -> str:
        return f"map[{self.key_type}]{self.value_type}]"

    def __eq__(self, other) -> bool:
        return isinstance(other, MapType) and self.key_type == other.key_type and self.value_type == other.value_type

    def __hash__(self) -> int:
        return hash((MapType, self.key_type, self.value_type))


class TupleType(Type):
    def __init__(self, element_types: List[Type]):
        self.element_types = element_types

    def __str__(self) -> str:
        return f"tuple[{', '.join(str(t) for t in self.element_types)}]"

    def __eq__(self, other) -> bool:
        return isinstance(other, TupleType) and self.element_types == other.element_types

    def __hash__(self) -> int:
        return hash((TupleType, tuple(self.element_types)))


class FunctionType(Type):
    def __init__(self, param_types: List[Type], return_type: Optional[Type]):
        self.param_types = param_types
        self.return_type = return_type

    def __str__(self) -> str:
        param_str = ", ".join(str(t) for t in self.param_types)
        return_str = str(self.return_type) if self.return_type else "void"
        return f"func({param_str}) -> {return_str}"

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, FunctionType)
            and self.param_types == other.param_types
            and self.return_type == other.return_type
        )

    def __hash__(self) -> int:
        return hash((FunctionType, tuple(self.param_types), self.return_type))


class ErrorType(Type):
    def __str__(self) -> str:
        return "error"


class NilType(Type):
    def __str__(self) -> str:
        return "nil"
