# Ymir Language Support for Visual Studio Code

> **OUTDATED.** This extension targets the legacy Python implementation's syntax and
> does not match [`/docs/spec/`](../../docs/spec/). It is retargeted in **Phase 9**
> ([`/PLAN.md`](../../PLAN.md)), where it becomes a thin client for `ymir lsp` rather
> than a standalone grammar. Do not extend it before then.

Provides rich language support for the Ymir programming language.

## Features

- **Syntax Highlighting**: Full syntax highlighting for Ymir files (`.ymr`)
- **Autocompletion**: Intelligent code completion for keywords, built-in functions, and snippets
- **Diagnostics**: Real-time error checking for common syntax issues
- **Code Snippets**: Quick templates for functions, classes, loops, and more
- **Bracket Matching**: Auto-closing and matching for brackets, parens, and braces
- **Concurrency Support**: Special highlighting and completion for Ymir's concurrency features (channels, spawn, select)
- **Matrix Operations**: Support for Ymir's matrix operations and GPU acceleration features

## Installation

### From VSIX File

1. Download the latest `.vsix` file from the releases
2. Open VSCode
3. Go to Extensions (Ctrl+Shift+X)
4. Click the "..." menu at the top
5. Select "Install from VSIX..."
6. Choose the downloaded `.vsix` file

### From Marketplace

Search for "Ymir Language Support" in the VSCode Extensions marketplace.

## Usage

1. Install the extension
2. Open or create a `.ymr` file
3. Start coding with full language support!

## Configuration

Settings available in VSCode settings (File > Preferences > Settings):

- `ymir.diagnostics.enabled`: Enable/disable diagnostic error checking (default: `true`)
- `ymir.completion.enabled`: Enable/disable autocompletion (default: `true`)

## Keyboard Shortcuts

- `Ctrl+Space`: Trigger autocompletion
- `Ctrl+/`: Toggle line comment
- `F5`: Run current Ymir file (requires Ymir compiler installed)

## Language Features

### Syntax Highlighting

All Ymir language constructs are properly highlighted:
- Keywords: `func`, `class`, `if`, `while`, `for`, `return`, etc.
- Concurrency keywords: `spawn`, `chan`, `select`, `async`, `await`
- Operators: Channel operators (`<-`), matrix multiplication (`@`)
- Built-in functions and types
- Comments, strings, numbers

### Autocompletion

Smart completions for:
- All Ymir keywords
- Built-in functions with signatures and documentation
- Type annotations
- Code snippets for common patterns
- Context-aware suggestions (e.g., function templates after `func`)

### Diagnostics

Real-time error detection for:
- Missing module declarations
- Unmatched brackets and parentheses
- Function syntax issues
- Type annotation problems
- Channel operator spacing

### Code Snippets

Quick templates available:
- `main` - Main function template
- `for` - For-in loop
- `while` - While loop
- `if` - If statement
- `try` - Try-except block
- Function and class templates

## Requirements

- Visual Studio Code 1.75.0 or higher
- Ymir compiler (optional, for running files)

## Example Code

```ymir
module example

func fibonacci(n: int) -> int {
    if n <= 1 {
        return n
    }
    return fibonacci(n - 1) + fibonacci(n - 2)
}

func main() {
    # Channel-based concurrency
    ch = make_channel(10)
    spawn worker(ch)
    
    # Matrix operations
    matrix_a = [[1.0, 2.0], [3.0, 4.0]]
    matrix_b = transpose(matrix_a)
    result = matrix_a @ matrix_b
    
    print("Fibonacci(10): " + str(fibonacci(10)))
}

main()
```

## Known Issues

- Full LSP features (go-to-definition across files, refactoring) are planned for future versions
- Cross-file import analysis is limited

## Roadmap

Future enhancements planned:
- Full Language Server Protocol (LSP) implementation
- Go-to-definition across files
- Find all references
- Rename refactoring
- Code formatting
- Integration with Ymir's type checker for advanced diagnostics

## Contributing

Found a bug or have a feature request? Please open an issue on the [Ymir GitHub repository](https://github.com/bjornaer/ymir).

## Release Notes

### 0.1.0

Initial release with:
- Syntax highlighting
- Autocompletion for keywords and built-in functions
- Basic diagnostics
- Code snippets
- Language configuration (brackets, comments, indentation)

## License

MIT

## Learn More

- [Ymir Language Documentation](https://github.com/bjornaer/ymir)
- [Ymir Concurrency Guide](https://github.com/bjornaer/ymir/blob/main/docs/concurrency.md)
- [VSCode Extension Development](https://code.visualstudio.com/api)

