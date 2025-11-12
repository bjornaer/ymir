# Ymir Language Syntax Guidelines

## Overview

Ymir is a functional programming language designed to abstract away mathematical computations, AI model training, and model serving through built-in abstractions. Files use the `.ymr` extension.

## File Structure

### Module Declaration
Every Ymir file must start with a module declaration:

```ymr
module module_name

# Module content goes here
```

Module names can be dotted (e.g., `module stdlib.math`).

### Comments
Use `#` for single-line comments:

```ymr
# This is a comment
func add(a: int, b: int) -> int {
    return a + b  # Inline comment
}
```

## Basic Syntax

### Variables and Assignment

```ymr
# Simple assignment
x = 42
name = "Ymir"

# Typed variable declaration
var matrix_a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
var count: int = 0
var message: string = "Hello"
```

### Data Types

#### Primitive Types
- `int` - Integer numbers
- `float` - Floating-point numbers
- `string` - Text strings
- `bool` - Boolean values (`true`/`false`)
- `any` - Any type (flexible type checking)

#### Complex Types
- `array[type]` - Arrays of specified type
- `matrix[type]` - 2D matrices of specified type
- `map[key_type]value_type` - Key-value mappings
- `tuple[type1, type2, ...]` - Fixed-size tuples
- `func(param_types) -> return_type` - Function types

#### Special Types
- `nil` - Null/none value
- `error` - Error type for exception handling

### Literals

```ymr
# Numbers
integer = 42
float_num = 3.14
scientific = 1.23e-4

# Strings
message = "Hello, Ymir!"
multiline = "Line 1\nLine 2"

# Booleans
is_true = true
is_false = false

# Arrays
numbers = [1, 2, 3, 4, 5]
mixed = [1, "hello", 3.14]

# Matrices
matrix = [[1.0, 2.0], [3.0, 4.0]]

# Maps
config = {"key1": "value1", "key2": 42}

# Tuples
coordinates = (10, 20)
rgb = (255, 128, 64)
```

## Functions

### Function Definition

```ymr
# Basic function
func add(a: int, b: int) -> int {
    return a + b
}

# Function with no return type (void)
func print_hello() {
    print("Hello!")
}

# Function with complex types
func process_matrix(data: matrix[float]) -> matrix[float] {
    return transpose(data)
}

# Function with multiple return values
func divide(a: int, b: int) -> int, error {
    if b == 0 {
        return 0, "division by zero"
    }
    return a / b, nil
}
```

### Function Calls

```ymr
# Simple function call
result = add(10, 20)

# Function call with module prefix
math_result = stdlib.math.add(5, 3)

# Method calls
array = [1, 2, 3]
new_array = array.append(4)
```

## Control Flow

### Conditional Statements

```ymr
# If-else statement
func check_number(n: int) -> string {
    if n > 0 {
        return "Positive"
    } else if n < 0 {
        return "Negative"
    } else {
        return "Zero"
    }
}

# Nested conditionals
func grade_score(score: int) -> string {
    if score >= 90 {
        return "A"
    } else if score >= 80 {
        return "B"
    } else if score >= 70 {
        return "C"
    } else {
        return "F"
    }
}
```

### Loops

#### While Loops
```ymr
func countdown(start: int) {
    while start > 0 {
        print(str(start))
        start = start - 1
    }
    print("Liftoff!")
}
```

#### For-In Loops
```ymr
func sum_array(arr: array[int]) -> int {
    total = 0
    for item in arr {
        total = total + item
    }
    return total
}
```

#### C-Style For Loops
```ymr
func factorial(n: int) -> int {
    result = 1
    for (i = 1; i <= n; i++) {
        result = result * i
    }
    return result
}
```

### Loop Control
```ymr
func process_data(data: array[int]) {
    for item in data {
        if item < 0 {
            continue  # Skip negative items
        }
        if item > 100 {
            break     # Stop if item is too large
        }
        print(str(item))
    }
}
```

## Exception Handling

### Exception Definition

```ymr
# Base exception
exception Exception {
    func __str__() -> string {
        return self.message
    }
}

# Custom exception
exception ValidationError: Exception {
    func __init__(field: string, message: string) {
        self.field = field
        self.message = message
    }
}
```

### Try-Except Blocks

```ymr
func safe_divide(a: int, b: int) -> int {
    try {
        return a / b
    } except ValueError as error {
        print("Value error: " + str(error))
        return 0
    } except Exception as error {
        print("Unexpected error: " + str(error))
        return 0
    } finally {
        print("Division operation completed")
    }
}
```

### Throwing Exceptions

```ymr
func validate_age(age: int) {
    if age < 0 {
        throw ValueError("Age cannot be negative")
    }
    if age > 150 {
        throw ValidationError("age", "Age seems unrealistic")
    }
}
```

## Classes and Objects

### Class Definition

```ymr
class Calculator {
    func __init__(self) {
        self.result = 0
    }

    func add(self, a: int, b: int) -> int {
        self.result = a + b
        return self.result
    }

    func get_result(self) -> int {
        return self.result
    }
}
```

### Class Usage

```ymr
func use_calculator() {
    calc = Calculator()
    result = calc.add(10, 20)
    print("Result: " + str(result))
}
```

## Modules and Imports

### Importing Modules

```ymr
# Import by string
import "stdlib.math"

# Import by identifier
import stdlib.http

# Import with dotted notation
import stdlib.collections
```

### Exporting from Modules

```ymr
module my_module

# Export a value
export PI = 3.14159

# Export a function
export func add(a: int, b: int) -> int {
    return a + b
}

# Export a class
export class MyClass {
    func __init__(self) {
        self.value = 0
    }
}
```

## Mathematical Operations

### Matrix Operations

```ymr
# Matrix creation
matrix_a = [[1.0, 2.0], [3.0, 4.0]]
identity = stdlib.math.matrix_eye(3)
zeros = stdlib.math.matrix_zeros(2, 3)

# Matrix arithmetic
result = matrix_a + matrix_b      # Element-wise addition
result = matrix_a - matrix_b      # Element-wise subtraction
result = matrix_a * matrix_b      # Element-wise multiplication
result = matrix_a @ matrix_b      # Matrix multiplication

# Matrix functions
transposed = transpose(matrix_a)
determinant = det(matrix_a)
inverse = inverse(matrix_a)
shape = shape(matrix_a)
```

### Array Operations

```ymr
# Array creation and manipulation
arr = [1, 2, 3, 4, 5]
new_arr = arr.append(6)
popped = arr.pop()
inserted = arr.insert(2, 10)
removed = arr.remove(3)
cleared = arr.clear()
extended = arr.extend([6, 7, 8])

# Array access
first = arr[0]
last = arr[-1]
slice = arr[1:3]
```

## Built-in Functions

### Mathematical Functions
```ymr
# Basic math
result = sqrt(16.0)
result = sin(3.14)
result = cos(1.57)
result = pow(2.0, 3.0)
result = abs(-42)
result = round(3.7)
result = min(1, 2, 3)
result = max(1, 2, 3)
```

### Utility Functions
```ymr
# Type conversion and utilities
str_value = str(42)
length = len([1, 2, 3])
print("Hello, World!")
```

## Advanced Features

### Async/Await (Placeholder)
```ymr
async func fetch_data(url: string) -> string {
    # Placeholder for async operations
    return await http_get(url)
}
```

### Type Annotations
```ymr
# Function with complex type annotations
func process_data(
    input: array[matrix[float]],
    config: map[string]any
) -> tuple[matrix[float], error] {
    # Function body
    return result, nil
}
```

## Best Practices

### Naming Conventions
- Use `snake_case` for variables and functions
- Use `PascalCase` for classes and exceptions
- Use `UPPER_CASE` for constants
- Use descriptive names that indicate purpose

### Code Organization
- Start every file with a module declaration
- Group related functions together
- Use comments to explain complex logic
- Export only what needs to be public

### Error Handling
- Always handle potential errors with try-except blocks
- Use specific exception types when possible
- Provide meaningful error messages
- Clean up resources in finally blocks

### Performance Considerations
- Use appropriate data types for your use case
- Leverage matrix operations for mathematical computations
- Consider using built-in optimizations for large datasets
- Profile code when performance is critical

## Examples

### Complete Program Example
```ymr
module calculator

import stdlib.math

func main() {
    print("=== Ymir Calculator ===")

    # Basic arithmetic
    result = add(10, 20)
    print("10 + 20 = " + str(result))

    # Matrix operations
    matrix_a = [[1.0, 2.0], [3.0, 4.0]]
    matrix_b = [[5.0, 6.0], [7.0, 8.0]]
    matrix_result = matrix_a @ matrix_b
    print("Matrix multiplication result: " + str(matrix_result))

    # Error handling
    try {
        result = divide(10, 0)
    } except Exception as error {
        print("Error: " + str(error))
    }
}

func add(a: int, b: int) -> int {
    return a + b
}

func divide(a: int, b: int) -> int {
    if b == 0 {
        throw ValueError("Division by zero")
    }
    return a / b
}

main()
```

## Method Chaining

Ymir supports method chaining for fluent, readable code:

### String Method Chaining

```ymr
# Clean and transform user input
user_input = "  HELLO WORLD  "
result = user_input.strip().lower().capitalize()
# Result: "Hello world"

# Complex text processing
text = "hello,world,test"
words = text.split(",")
formatted = " | ".join(words).upper()
# Result: "HELLO | WORLD | TEST"
```

### Collection Method Chaining

```ymr
# Data processing pipeline
data = [5, 2, 8, 1, 9, 2, 5, 3]
result = data.unique().sort().slice(0, 5)
# Result: [1, 2, 3, 5, 8]
```

## Operator Overloading Semantics

Ymir operators work intelligently based on operand types:

### Addition (`+`)

- **Numbers**: Arithmetic addition
- **Strings**: Concatenation
- **String + Number**: Automatic type conversion
- **Arrays**: Concatenation
- **Matrices**: Element-wise addition

```ymr
# String + Number auto-conversion
result = "Count: " + 42  # "Count: 42"
```

### Multiplication (`*`)

- **Numbers**: Arithmetic multiplication
- **String * int**: String repetition
- **Matrices**: Element-wise multiplication

```ymr
# String repetition
result = "abc" * 3  # "abcabcabc"
```

### Matrix Multiplication (`@`)

- **Matrices only**: True matrix multiplication

```ymr
result = matrix_a @ matrix_b
```

## Functional Programming Patterns

Ymir embraces functional programming with immutable collections:

### Immutability

All collection methods return new arrays:

```ymr
original = [3, 1, 2]
sorted_copy = original.sort()
# original is still [3, 1, 2]
# sorted_copy is [1, 2, 3]
```

### Higher-Order Functions

```ymr
func isEven(n: int) -> bool {
    return n % 2 == 0
}

func double(n: int) -> int {
    return n * 2
}

numbers = [1, 2, 3, 4, 5, 6]
result = numbers.filter(isEven).map(double)
# Result: [4, 8, 12]
```

### Complete Functional Pipeline

```ymr
func isPositive(n: int) -> bool { return n > 0 }
func square(n: int) -> int { return n * n }
func add(a: int, b: int) -> int { return a + b }

numbers = [-2, -1, 0, 1, 2, 3, 4, 5]
result = numbers.filter(isPositive).map(square).reduce(add)
# Result: 55 (1 + 4 + 9 + 16 + 25)
```

## Standard Library Reference

For complete documentation of all string methods, collection methods, and operators, see:
- `docs/stdlib_reference.md` - Complete API reference
- `examples/stdlib_showcase.ymr` - Comprehensive examples

This syntax guide covers the core features of the Ymir language. As the language evolves, additional features and syntax will be documented here.
