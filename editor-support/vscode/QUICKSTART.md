# Ymir VSCode Extension - Quick Start Guide

## Testing the Extension Locally

### Method 1: Extension Development Host (Recommended for Development)

1. Open the extension folder in VSCode:
   ```bash
   cd /Users/max/personal/ymir/editor-support/vscode
   code .
   ```

2. Press `F5` to launch the Extension Development Host
   - A new VSCode window will open with the extension loaded

3. In the new window, create or open a `.ymr` file to test:
   ```bash
   # Create a test file
   echo 'module test

func main() {
    print("Hello, Ymir!")
}' > test.ymr
   ```

4. Observe:
   - Syntax highlighting
   - Autocompletion (press Ctrl+Space)
   - Diagnostics (red squiggles for errors)

### Method 2: Install from .vsix File

1. Install the packaged extension:
   ```bash
   code --install-extension ymir-language-0.1.0.vsix
   ```

2. Restart VSCode

3. Open or create a `.ymr` file

4. The extension should be active automatically

### Method 3: VSCode UI Installation

1. Open VSCode
2. Go to Extensions (Ctrl+Shift+X)
3. Click the "..." menu at the top
4. Select "Install from VSIX..."
5. Navigate to and select `ymir-language-0.1.0.vsix`
6. Restart VSCode when prompted

## Testing Checklist

Use this checklist to verify all features work:

### ✅ Syntax Highlighting
- [ ] Keywords are highlighted (func, class, if, while, for, etc.)
- [ ] Concurrency keywords are highlighted (spawn, chan, select, async, await)
- [ ] Strings are highlighted
- [ ] Comments are highlighted
- [ ] Numbers are highlighted
- [ ] Operators are highlighted (including <- and @)

### ✅ Autocompletion
- [ ] Type `func` and space - should suggest function template
- [ ] Type `class` and space - should suggest class template
- [ ] Type `pri` - should suggest `print()`
- [ ] Type `:` after parameter - should suggest types
- [ ] Press Ctrl+Space - should show all available completions

### ✅ Code Snippets
- [ ] Type `main` - should suggest main function snippet
- [ ] Type `for` - should suggest for-loop snippet
- [ ] Type `while` - should suggest while-loop snippet
- [ ] Type `try` - should suggest try-except snippet

### ✅ Diagnostics
- [ ] Missing module declaration shows warning
- [ ] Unmatched brackets show errors
- [ ] Unknown types show warnings with suggestions

### ✅ Editor Features
- [ ] Auto-closing brackets works
- [ ] Ctrl+/ toggles comments
- [ ] Bracket matching highlights
- [ ] Code folding works for functions/classes

### ✅ Commands
- [ ] `ymir.run` command is available (Ctrl+Shift+P → "Ymir: Run")

## Sample Test File

Create `test.ymr` with this content:

```ymir
module test

# This is a comment
func fibonacci(n: int) -> int {
    if n <= 1 {
        return n
    }
    return fibonacci(n - 1) + fibonacci(n - 2)
}

class Calculator {
    func __init__(self) {
        self.result = 0
    }
    
    func add(self, a: int, b: int) -> int {
        return a + b
    }
}

func main() {
    # Test basic operations
    result = fibonacci(10)
    print("Fibonacci(10): " + str(result))
    
    # Test channel operations
    ch = make_channel(5)
    spawn worker(ch)
    value <- ch
    
    # Test matrix operations
    matrix_a = [[1.0, 2.0], [3.0, 4.0]]
    matrix_b = transpose(matrix_a)
    product = matrix_a @ matrix_b
    
    # Test exception handling
    try {
        risky_operation()
    } except Error as e {
        print("Error: " + str(e))
    }
}

func worker(ch: chan) {
    ch <- 42
}

main()
```

## Debugging the Extension

If you encounter issues:

1. **Check the Output Panel**:
   - View → Output → Select "Ymir" from dropdown

2. **Check Extension Logs**:
   - In Extension Development Host: Help → Toggle Developer Tools
   - Check Console for errors

3. **Verify Compilation**:
   ```bash
   cd editor-support/vscode
   npm run compile
   ```

4. **Check Configuration**:
   - File → Preferences → Settings
   - Search for "ymir"
   - Verify settings are enabled

## Uninstalling

### From Command Line
```bash
code --uninstall-extension ymir.ymir-language
```

### From VSCode UI
1. Go to Extensions (Ctrl+Shift+X)
2. Find "Ymir Language Support"
3. Click gear icon → Uninstall

## Next Steps

Once testing is complete:

1. **Report Issues**: If you find bugs, report them at https://github.com/bjornaer/ymir/issues
2. **Publish**: Follow `PUBLISHING.md` to publish to the marketplace
3. **Contribute**: See `CONTRIBUTING.md` for development guidelines

## Development Workflow

For making changes to the extension:

1. Make changes to TypeScript files in `src/`
2. Run `npm run compile` or `npm run watch`
3. Press `F5` to test in Extension Development Host
4. Reload the extension host (Ctrl+R in the development window)
5. Test your changes

## Useful Commands

```bash
# Watch mode (auto-compile on save)
npm run watch

# Lint the code
npm run lint

# Package extension
vsce package

# Increment version and publish
vsce publish patch
vsce publish minor
vsce publish major
```

## Getting Help

- **Ymir Documentation**: https://github.com/bjornaer/ymir
- **VSCode Extension API**: https://code.visualstudio.com/api
- **Extension Development**: https://code.visualstudio.com/api/get-started/your-first-extension

