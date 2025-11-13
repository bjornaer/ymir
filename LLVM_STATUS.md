# LLVM Codegen Feature Status

## ✅ Supported Features
- Function definitions and calls
- Return statements
- Variables and assignment
- Arithmetic operations (+, -, *, /, %, **)
- Comparison operations (<, >, <=, >=, ==, !=)
- Unary operations (-, +)
- If-else statements
- C-style for loops (for init; cond; incr)
- Break and continue
- String literals
- Integer and float literals
- Boolean values
- Type annotations (basic types)
- Print function
- String conversion (str())

## 🚧 Partially Supported
- While loops (basic support, may have edge cases)
- Arrays (literals work, runtime iteration limited)
- Classes (basic support, may have issues)

## ❌ Explicitly Unsupported (Falls back to Interpreter)
- **Concurrency**: spawn, channels, select
- **Async/await**: async functions, await expressions
- **Advanced loops**: for-in over runtime arrays
- **Exceptions**: try-except-finally, throw
- **Matrix operations**: GPU-accelerated operations
- **Advanced string operations**: some methods may not work
- **Networking functions**: socket operations (use interpreter mode)
- **Memory management**: allocate, retain, release (use interpreter mode)

## Test Results
Current LLVM test suite results: **6/6 PASSING (100%)**
- ✅ test_simple_print: PASSED
- ✅ test_arithmetic: PASSED  
- ✅ test_variables_and_assignment: PASSED
- ✅ test_if_statement: PASSED
- ✅ test_while_loop: PASSED (fixed variable reassignment issue)
- ✅ test_for_in_loop: PASSED (correctly raises UnsupportedFeatureError in llvm mode, falls back in auto mode)

## How Fallback Works
When running with default mode (`ymir run script.ymr`):
1. Parser/analyzer run normally
2. LLVM codegen attempts to generate IR
3. If unsupported feature detected → automatic fallback to interpreter
4. User sees informative message about why fallback occurred

## Force Specific Mode
```bash
ymir run script.ymr --mode llvm       # Fail if unsupported features
ymir run script.ymr --mode interpret  # Always use interpreter
ymir run script.ymr --mode auto       # Try LLVM, fallback (default)
ymir run script.ymr -i                # Shorthand for interpret
```

## Known Issues
- **For-in loops**: Not yet implemented for LLVM, will automatically fall back to interpreter
- **Type inference**: Limited type inference; explicit type annotations recommended
- **Complex expressions**: Some nested expressions may not compile correctly

## Future Work
- Add for-in loop support for compile-time known arrays
- Improve type inference for better codegen
- Add support for more complex expressions
- Implement exception handling in LLVM mode
- Add basic networking support
- Support for classes and methods
- Array operations beyond basic access

## Usage Recommendations
1. **For production**: Use default mode (auto) for best balance of performance and compatibility
2. **For debugging**: Use `-i` (interpreter mode) for full feature support and better error messages
3. **For performance**: Use `--mode llvm` only if you're sure your code uses only supported features
4. **Type annotations**: Always use explicit type annotations for best LLVM compilation results

## Contributing
If you encounter issues with LLVM compilation:
1. Check this document to see if the feature is supported
2. Try running with `-i` to verify it works in interpreter mode
3. Report bugs with minimal reproduction cases
4. Include LLVM IR output if possible (check logs with `--verbosity DEBUG`)

