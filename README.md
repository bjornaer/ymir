# Ymir Programming Language
<p align="center">
  <img src="assets/ymir_logo.png" alt="Ymir Logo"/>
</p>

Ymir is a modern programming language inspired by Norse mythology, designed to be powerful and efficient for machine learning systems. Ymir combines Python's ease of use with Go's concurrency model, featuring advanced mathematical support with GPU acceleration.

## Features

- **LLVM-Powered Execution:** JIT compilation via LLVM for high-performance native code execution
- **Intuitive Hybrid Syntax:** Clean syntax combining Python's readability with Go's structure
- **Go-Style Concurrency:** Spawn tasks and communicate via channels for easy parallel processing
- **GPU-Accelerated Matrix Operations:** Built-in matrix support powered by JAX with automatic CPU fallback
- **Async HTTP Server & Client:** Built on aiohttp for high-performance web applications
- **Go-Style Package Management:** Install dependencies directly from GitHub/GitLab repos
- **Type Safety:** Strongly typed with type inference and checking
- **Dual Execution Modes:** LLVM compilation (default) or pure interpretation for debugging
- **Standard Library:** Comprehensive stdlib including math, HTTP, server, collections, and more
- **Cross-Platform:** Runs on Linux, macOS, and Windows

## Instalation

```bash
brew tap bjornaer/ymir
brew install ymir
# to add gpu support, also install jax
pip install jax jaxlib
```

## Development

To develop Ymir, use the package manager [Poetry](https://python-poetry.org/):

```bash
pip install poetry
```

Clone the repository and install dependencies:

```bash
git clone https://github.com/bjornaer/ymir.git
cd ymir
poetry install
```

## Quick Start

### 1. Concurrency with Spawn and Channels
```ymr
module example

func worker(id: int, ch: any) {
    result = id * 2
    ch <- result  # Send to channel
}

func main() {
    ch = make_channel(10)
    
    # Spawn concurrent tasks
    spawn worker(1, ch)
    spawn worker(2, ch)
    
    # Receive results
    result1 <- ch
    result2 <- ch
    
    print("Results: " + str(result1) + ", " + str(result2))
}
```

### 2. GPU-Accelerated Matrix Operations
```ymr
module matrix_example

func main() {
    # Check GPU availability
    if matrix_gpu_available() {
        print("GPU available!")
    }
    
    # Matrix operations
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    
    result = a @ b  # Matrix multiplication
    print(str(result))
}
```

### 3. HTTP Server
```ymr
module server_example

import stdlib.server

func handle_hello(request: Request) -> Response {
    return Response(200, "Hello, World!")
}

func main() {
    server = HTTPServer("0.0.0.0", 8080)
    server.route("/hello", handle_hello)
    server.run()
}
```

## Usage

### Running Ymir Scripts

Ymir compiles and executes scripts using LLVM by default for maximum performance:

```bash
# Run with LLVM compilation (default)
poetry run ymir run examples/main.ymr

# Run with interpreter mode (useful for debugging)
poetry run ymir run examples/main.ymr --interpreter
# or shorthand:
poetry run ymir run examples/main.ymr -i

# Skip standard library loading for faster startup
poetry run ymir run examples/main.ymr --no-stdlib

# Set execution mode explicitly
poetry run ymir run examples/main.ymr --mode llvm      # LLVM only (fail if compilation fails)
poetry run ymir run examples/main.ymr --mode interpret # Pure interpretation
poetry run ymir run examples/main.ymr --mode auto      # Try LLVM, fallback to interpreter
```

### Execution Modes

Ymir supports dual execution modes for flexibility and performance:

#### LLVM Mode (Default with Auto Fallback)
- JIT compilation for maximum performance
- Automatically falls back to interpreter for unsupported features
- Best for production use
- Supports: functions, arithmetic, control flow, basic types

#### Interpreter Mode
- Pure Python interpretation
- Full feature support including concurrency, async, networking
- Better error messages for debugging
- Slower but more flexible

#### Choosing a Mode
```bash
ymir run script.ymr              # Auto mode: LLVM with fallback (recommended)
ymir run script.ymr --mode llvm  # LLVM only: fail on unsupported features
ymir run script.ymr -i           # Interpreter only: full feature support
```

See [LLVM_STATUS.md](LLVM_STATUS.md) for detailed feature support and known issues.

### Building Binaries
Build Ymir scripts into standalone executables:
```bash
poetry run ymir build examples/main.ymr --output dist/myapp
```

### Package Management
```bash
# Add a dependency from GitHub/GitLab
poetry run ymir add github.com/user/awesome-lib

# Install all dependencies
poetry run ymir install

# List dependencies
poetry run ymir list

# Remove a dependency
poetry run ymir remove awesome-lib
```

### Contributing
We welcome contributions to Ymir! Please read our CONTRIBUTING.md for guidelines on how to contribute.

### License
Ymir is licensed under the MIT License. See the LICENSE file for more information.

### Contact
For any questions or feedback, please feel free to open an issue or contact us at max.schulkin@gmail.com.

![Ymir Banner](assets/ymir_banner.png)
