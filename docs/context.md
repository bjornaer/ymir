# Ymir Language Context Refresh

> **SUPERSEDED.** This document describes the frozen Python implementation in
> `/ymir-legacy-py/`, and contains claims that have since been disproved by direct
> execution. It is kept for history. The normative definition of Ymir is
> [`/docs/spec/`](spec/), and the migration plan is [`/PLAN.md`](../PLAN.md).

## Quick Overview

**Ymir** is a functional programming language designed to abstract away mathematical computations, AI model training, and model serving. It's built using Python and Poetry, with files using the `.ymr` extension.

## Core Architecture

### Implementation Stack
- **Language**: Python-based interpreter
- **Package Management**: Poetry
- **Backend**: LLVM for code generation (via llvmlite)
- **Mathematical Operations**: NumPy for matrix operations
- **File Extension**: `.ymr`

### Key Components
- **Lexer** (`ymir/core/lexer.py`) - Tokenizes source code
- **Parser** (`ymir/core/parser.py`) - Builds AST from tokens
- **Semantic Analyzer** (`ymir/core/semantic_analyzer.py`) - Validates semantics
- **Type Checker** (`ymir/core/type_checker.py`) - Performs type checking
- **Interpreter** (`ymir/interpreter.py`) - Executes Ymir code
- **Code Generator** (`ymir/tools/codegen.py`) - Generates LLVM IR

## Language Features

### Core Syntax
```ymr
module example

# Variables and types
var matrix_a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
var count: int = 0

# Functions
func add(a: int, b: int) -> int {
    return a + b
}

# Control flow
if condition {
    # code
} else {
    # code
}

while condition {
    # code
}

for item in array {
    # code
}

for (i = 0; i < n; i++) {
    # code
}

# Exception handling
try {
    # code
} except Exception as error {
    # handle error
} finally {
    # cleanup
}
```

### Data Types
- **Primitive**: `int`, `float`, `string`, `bool`, `any`
- **Complex**: `array[type]`, `matrix[type]`, `map[key]value`, `tuple[type1, type2]`
- **Special**: `nil`, `error`

### Mathematical Focus
- Built-in matrix operations with NumPy backend
- Matrix arithmetic: `+`, `-`, `*` (element-wise), `@` (matrix multiplication)
- Matrix functions: `transpose()`, `det()`, `inverse()`, `shape()`
- Array operations: `append()`, `pop()`, `insert()`, `remove()`, `clear()`, `extend()`

### Module System
```ymr
# Import
import stdlib.math
import "custom.module"

# Export
export func public_function() -> int {
    return 42
}

export PI = 3.14159
```

### Exception System
```ymr
# Define exceptions
exception CustomError: Exception {
    func __init__(message: string) {
        self.message = message
    }
}

# Throw exceptions
throw CustomError("Something went wrong")
```

## Standard Library

### Current Modules
- `stdlib.math` - Mathematical operations and constants
- `stdlib.exceptions` - Exception classes
- `stdlib.http` - HTTP operations (placeholder)
- `stdlib.string` - String utilities
- `stdlib.io` - Input/output operations
- `stdlib.datetime` - Date/time operations
- `stdlib.collections` - Collection utilities

### Built-in Functions
- **Math**: `sqrt()`, `sin()`, `cos()`, `pow()`, `abs()`, `round()`, `min()`, `max()`
- **Utilities**: `print()`, `str()`, `len()`
- **Matrix**: `transpose()`, `det()`, `inverse()`, `shape()`

## Development Workflow

### Running Ymir Code
```bash
# Using the interpreter directly
python -m ymir.interpreter path/to/file.ymr

# Using CLI (if implemented)
ymir run path/to/file.ymr
```

### Testing
- Tests located in `tests/` directory
- Uses pytest framework
- Test files follow pattern `test_*.py`

### Project Structure
```
ymir/
├── ymir/                    # Main package
│   ├── core/               # Core language components
│   ├── stdlib/             # Standard library modules
│   ├── tools/              # Development tools
│   └── cli/                # Command-line interface
├── examples/               # Example programs
├── tests/                  # Test suite
├── docs/                   # Documentation
└── scripts/                # Build and utility scripts
```

## Key Implementation Details

### AST Nodes
- `FunctionDef`, `ClassDef`, `ExceptionDef`
- `IfStatement`, `WhileStatement`, `ForInLoop`, `ForCStyleLoop`
- `Assignment`, `Expression`, `BinaryOp`, `UnaryOp`
- `ArrayLiteral`, `StringLiteral`, `MapLiteral`, `TupleLiteral`
- `ModuleDef`, `ImportDef`, `ExportDef`
- `TryExceptStatement`, `ThrowStatement`

### Type System
- Static type checking with type annotations
- Support for complex nested types
- Type inference for some expressions
- Built-in type validation

### Memory Management
- Automatic memory management (Python-based)
- Support for explicit allocation/deallocation (placeholder)
- Reference counting for objects

### Performance Features
- LLVM JIT compilation for performance-critical code
- NumPy integration for efficient matrix operations
- Optimized mathematical operations

## Current Limitations

### Known Issues
- LLVM code generation needs main function fix
- Some async/await features are placeholders
- HTTP and networking features are basic
- GPU acceleration is placeholder
- Limited standard library implementation

### Planned Features
- Full async/await support
- Complete standard library
- GPU acceleration for matrix operations
- Better error messages and debugging
- Package management system
- IDE support and tooling

## Development Guidelines

### Code Style
- Follow Python PEP 8 for Python code
- Use descriptive names for Ymir functions and variables
- Include type annotations where possible
- Add comprehensive tests for new features

### Adding Features
1. Update lexer for new tokens
2. Extend parser for new syntax
3. Add AST nodes if needed
4. Update semantic analyzer
5. Extend type checker
6. Implement interpreter logic
7. Add tests
8. Update documentation

### Debugging
- Use verbosity levels in interpreter
- Check AST structure during parsing
- Validate type checking results
- Monitor symbol table state

## Quick Reference

### File Structure
```ymr
module module_name

# Imports
import stdlib.math

# Exports
export func public_function() -> int {
    return 42
}

# Main function
func main() {
    # Program logic
}

main()
```

### Common Patterns
```ymr
# Matrix operations
matrix_a = [[1.0, 2.0], [3.0, 4.0]]
result = matrix_a @ matrix_b

# Error handling
try {
    result = risky_operation()
} except Exception as error {
    print("Error: " + str(error))
}

# Array manipulation
arr = [1, 2, 3]
new_arr = arr.append(4)
```

This context refresh document provides a quick reference for the Ymir language implementation. Use this to quickly get up to speed on the current state of the language and its features.
