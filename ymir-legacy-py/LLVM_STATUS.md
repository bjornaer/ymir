# LLVM Codegen Feature Status

## ✅ Supported Features
- Function definitions and calls
- Return statements
- Variables and assignment (including `:=` operator)
- Arithmetic operations (+, -, *, /, %, **)
- Comparison operations (<, >, <=, >=, ==, !=)
- Unary operations (-, +)
- If-else statements
- While loops (fully supported with break/continue)
- C-style for loops (for init; cond; incr)
- For-in loops (compile-time known array literals only)
- Break and continue (in all loop types)
- Try-except-finally blocks (exception handling)
- Throw statements
- Exception definitions
- Array literals and operations
- Array access with runtime bounds checking
- String literals
- Integer and float literals
- Boolean values
- Type annotations (basic types)
- Print function
- String conversion (str())

## 🚧 Partially Supported
- Arrays (literals work, runtime iteration limited)
- Classes (basic support, may have issues)
- For-in loops (only over compile-time array literals, not runtime arrays)

## ❌ Explicitly Unsupported (Falls back to Interpreter)
- **Concurrency**: spawn, channels (`<-`, walrus operator with type), select - uses event loop
- **Matrix operations**: GPU-accelerated operations (JAX/NumPy backend)
- **Advanced string operations**: some methods may not work
- **Networking functions**: socket operations (use interpreter mode)
- **Memory management**: allocate, retain, release (use interpreter mode)
- **Runtime array iteration**: for-in loops over runtime arrays (only compile-time array literals supported)

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
- **For-in loops**: Only work with compile-time array literals `[1, 2, 3]`, not runtime arrays
- **Type inference**: Limited type inference; explicit type annotations recommended
- **Complex expressions**: Some nested expressions may not compile correctly
- **Array bounds errors**: Out-of-bounds access returns zero instead of throwing exception (needs proper exception integration)
- **Classes**: Basic support exists but may have issues with inheritance and complex methods

## Future Work
- Add for-in loop support for runtime arrays (requires array metadata)
- Improve array bounds checking to throw proper exceptions
- Improve type inference for better codegen
- Add support for more complex expressions
- Enhanced exception handling with proper LLVM invoke/landingpad integration
- Add basic networking support in LLVM mode
- Enhanced support for classes and methods
- Optimize array operations and memory management

## Concurrency Design

Ymir provides pure Go-style concurrency with spawn and channels:

### Channel Syntax (Go-style with walrus operator)
Channels use Go-style syntax with unambiguous send and receive operations:

```ymr
# Create a channel
var ch: any = make_channel(10)  # Buffered channel with capacity 10

# Send to channel
ch <- value

# Receive from channel (new variable declaration with walrus operator)
result: int := <-ch

# Receive from channel (assignment to existing variable)
result = <-ch
```

### Spawn: Launching Concurrent Tasks
Use `spawn` to launch functions concurrently:

```ymr
func worker(id: int, ch: any) {
    var result: int = id * 2
    ch <- result
}

func main() {
    var ch: any = make_channel(3)
    
    # Spawn concurrent workers
    spawn worker(1, ch)
    spawn worker(2, ch)
    spawn worker(3, ch)
    
    # Collect results using walrus operator with types
    r1: int := <-ch
    r2: int := <-ch
    r3: int := <-ch
    
    print("Results: " + str(r1) + ", " + str(r2) + ", " + str(r3))
}
```

Note: All functions are regular functions. There is no `async` keyword in Ymir.

### Event Loop Management
- **Automatic Initialization**: Event loop initializes automatically on first spawn/channel operation
- **Internal Only**: Event loop is an implementation detail, not exposed to users
- **Transparent Blocking**: Channel operations block synchronously from user perspective
- **Go-style API**: Pure spawn + channels, no async/await keywords

### Implementation Details
- Channel operations use `asyncio.Queue` internally for non-blocking I/O
- `spawn` wraps regular functions to run in the event loop
- Event loop is managed automatically by the runtime
- All operations are thread-safe

**Note**: All concurrency features require interpreter mode and will cause automatic fallback from LLVM compilation.

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

