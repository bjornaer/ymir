# Ymir VSCode Extension Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Setup](#project-setup)
4. [Syntax Highlighting](#syntax-highlighting)
5. [Language Configuration](#language-configuration)
6. [Autocompletion Provider](#autocompletion-provider)
7. [Diagnostics Provider](#diagnostics-provider)
8. [Testing and Debugging](#testing-and-debugging)
9. [Packaging and Publishing](#packaging-and-publishing)
10. [Future: Language Server Protocol Migration](#future-language-server-protocol-migration)

---

## Overview

This guide provides step-by-step instructions for creating a Visual Studio Code extension for the **Ymir programming language**. The extension will provide:

- **Syntax Highlighting**: Color-coded syntax using TextMate grammar
- **Autocompletion**: Intelligent code completion for keywords, functions, and common patterns
- **Basic Diagnostics**: Real-time error checking for common syntax issues
- **Scalable Architecture**: Designed to migrate to Language Server Protocol (LSP) in the future

### Design Philosophy

This extension uses a **hybrid approach**:
- Start with declarative features (syntax highlighting, language configuration)
- Add provider-based features (completion, diagnostics) using VSCode's extension API
- Use modular architecture that can be refactored to LSP later

This approach allows you to:
1. Get working features quickly (~4-8 hours)
2. Provide value immediately to Ymir developers
3. Upgrade to full LSP when needed without rewriting from scratch

---

## Prerequisites

Before starting, ensure you have:

- **Node.js** (v16 or later): [Download](https://nodejs.org/)
- **npm** or **yarn**: Package manager (comes with Node.js)
- **Visual Studio Code**: [Download](https://code.visualstudio.com/)
- **TypeScript** knowledge: Basic understanding recommended
- **Yeoman and VS Code Extension Generator**:
  ```bash
  npm install -g yo generator-code
  ```

---

## Project Setup

### Step 1: Generate Extension Scaffold

Run the Yeoman generator to create a new VSCode extension:

```bash
yo code
```

You'll be prompted with several questions. Answer as follows:

```
? What type of extension do you want to create? 
  → New Extension (TypeScript)

? What's the name of your extension? 
  → Ymir Language Support

? What's the identifier of your extension? 
  → ymir-language

? What's the description of your extension? 
  → Syntax highlighting, autocompletion, and diagnostics for the Ymir programming language

? Initialize a git repository? 
  → Yes

? Which package manager to use? 
  → npm (or yarn, your choice)
```

This generates a project structure:

```
ymir-language/
├── .vscode/
│   ├── launch.json          # Debug configuration
│   └── tasks.json           # Build tasks
├── src/
│   ├── extension.ts         # Main extension entry point
│   └── test/
│       └── extension.test.ts
├── .gitignore
├── .vscodeignore
├── package.json             # Extension manifest
├── README.md
├── tsconfig.json            # TypeScript config
└── vsc-extension-quickstart.md
```

### Step 2: Navigate to Project Directory

```bash
cd ymir-language
```

### Step 3: Update package.json

Replace the generated `package.json` with this extended version:

```json
{
  "name": "ymir-language",
  "displayName": "Ymir Language Support",
  "description": "Syntax highlighting, autocompletion, and diagnostics for the Ymir programming language",
  "version": "0.1.0",
  "publisher": "your-publisher-name",
  "repository": {
    "type": "git",
    "url": "https://github.com/your-username/ymir-vscode"
  },
  "engines": {
    "vscode": "^1.75.0"
  },
  "categories": [
    "Programming Languages"
  ],
  "keywords": [
    "ymir",
    "programming language",
    "syntax highlighting",
    "autocompletion"
  ],
  "activationEvents": [
    "onLanguage:ymir"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "languages": [
      {
        "id": "ymir",
        "aliases": ["Ymir", "ymir"],
        "extensions": [".ymr"],
        "configuration": "./language-configuration.json",
        "icon": {
          "light": "./icons/ymir-icon.png",
          "dark": "./icons/ymir-icon.png"
        }
      }
    ],
    "grammars": [
      {
        "language": "ymir",
        "scopeName": "source.ymir",
        "path": "./syntaxes/ymir.tmLanguage.json"
      }
    ],
    "configuration": {
      "type": "object",
      "title": "Ymir",
      "properties": {
        "ymir.diagnostics.enabled": {
          "type": "boolean",
          "default": true,
          "description": "Enable/disable diagnostic error checking"
        },
        "ymir.completion.enabled": {
          "type": "boolean",
          "default": true,
          "description": "Enable/disable autocompletion"
        }
      }
    }
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "pretest": "npm run compile && npm run lint",
    "lint": "eslint src --ext ts",
    "test": "node ./out/test/runTest.js"
  },
  "devDependencies": {
    "@types/vscode": "^1.75.0",
    "@types/node": "16.x",
    "@typescript-eslint/eslint-plugin": "^5.45.0",
    "@typescript-eslint/parser": "^5.45.0",
    "eslint": "^8.28.0",
    "typescript": "^4.9.3"
  }
}
```

**Key sections explained:**

- **`activationEvents`**: Extension activates when a `.ymr` file is opened
- **`contributes.languages`**: Registers the `ymir` language
- **`contributes.grammars`**: Links to TextMate grammar file
- **`contributes.configuration`**: User settings for the extension

### Step 4: Create Required Directories

```bash
mkdir -p syntaxes src/providers
```

---

## Syntax Highlighting

Syntax highlighting uses **TextMate grammar**, a declarative JSON format that defines regex patterns for language tokens.

### Step 1: Create TextMate Grammar File

Create `syntaxes/ymir.tmLanguage.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
  "name": "Ymir",
  "scopeName": "source.ymir",
  "patterns": [
    {
      "include": "#comments"
    },
    {
      "include": "#strings"
    },
    {
      "include": "#keywords"
    },
    {
      "include": "#concurrency-keywords"
    },
    {
      "include": "#operators"
    },
    {
      "include": "#numbers"
    },
    {
      "include": "#function-declarations"
    },
    {
      "include": "#class-declarations"
    },
    {
      "include": "#exception-declarations"
    },
    {
      "include": "#type-annotations"
    },
    {
      "include": "#module-declarations"
    },
    {
      "include": "#builtin-functions"
    },
    {
      "include": "#constants"
    },
    {
      "include": "#punctuation"
    }
  ],
  "repository": {
    "comments": {
      "patterns": [
        {
          "name": "comment.line.number-sign.ymir",
          "match": "#.*$"
        }
      ]
    },
    "strings": {
      "patterns": [
        {
          "name": "string.quoted.double.ymir",
          "begin": "\"",
          "end": "\"",
          "patterns": [
            {
              "name": "constant.character.escape.ymir",
              "match": "\\\\(n|t|r|\\\\|\"|')"
            }
          ]
        }
      ]
    },
    "keywords": {
      "patterns": [
        {
          "name": "keyword.control.ymir",
          "match": "\\b(if|else|while|for|return|break|continue|in)\\b"
        },
        {
          "name": "keyword.other.ymir",
          "match": "\\b(func|class|import|export|module|var|as)\\b"
        },
        {
          "name": "keyword.control.exception.ymir",
          "match": "\\b(try|except|finally|throw|exception)\\b"
        }
      ]
    },
    "concurrency-keywords": {
      "patterns": [
        {
          "name": "keyword.control.concurrency.ymir",
          "match": "\\b(spawn|chan|select|async|await)\\b"
        }
      ]
    },
    "operators": {
      "patterns": [
        {
          "name": "keyword.operator.channel.ymir",
          "match": "<-"
        },
        {
          "name": "keyword.operator.matrix.ymir",
          "match": "@"
        },
        {
          "name": "keyword.operator.assignment.ymir",
          "match": ":=|="
        },
        {
          "name": "keyword.operator.comparison.ymir",
          "match": "==|!=|<=|>=|<|>"
        },
        {
          "name": "keyword.operator.logical.ymir",
          "match": "&&|\\|\\||!"
        },
        {
          "name": "keyword.operator.arithmetic.ymir",
          "match": "\\+\\+|\\+=|-=|\\*=|/=|%=|\\+|-|\\*|/|%"
        }
      ]
    },
    "numbers": {
      "patterns": [
        {
          "name": "constant.numeric.scientific.ymir",
          "match": "\\b\\d+(\\.\\d+)?([eE][+-]?\\d+)\\b"
        },
        {
          "name": "constant.numeric.float.ymir",
          "match": "\\b\\d+\\.\\d+\\b"
        },
        {
          "name": "constant.numeric.integer.ymir",
          "match": "\\b\\d+\\b"
        }
      ]
    },
    "function-declarations": {
      "patterns": [
        {
          "name": "meta.function.ymir",
          "match": "\\b(func)\\s+([a-zA-Z_][a-zA-Z0-9_]*)",
          "captures": {
            "1": {
              "name": "keyword.other.ymir"
            },
            "2": {
              "name": "entity.name.function.ymir"
            }
          }
        }
      ]
    },
    "class-declarations": {
      "patterns": [
        {
          "name": "meta.class.ymir",
          "match": "\\b(class)\\s+([A-Z][a-zA-Z0-9_]*)",
          "captures": {
            "1": {
              "name": "keyword.other.ymir"
            },
            "2": {
              "name": "entity.name.type.class.ymir"
            }
          }
        }
      ]
    },
    "exception-declarations": {
      "patterns": [
        {
          "name": "meta.exception.ymir",
          "match": "\\b(exception)\\s+([A-Z][a-zA-Z0-9_]*)(?::\\s*([A-Z][a-zA-Z0-9_]*))?",
          "captures": {
            "1": {
              "name": "keyword.control.exception.ymir"
            },
            "2": {
              "name": "entity.name.type.exception.ymir"
            },
            "3": {
              "name": "entity.other.inherited-class.ymir"
            }
          }
        }
      ]
    },
    "type-annotations": {
      "patterns": [
        {
          "name": "storage.type.ymir",
          "match": "\\b(int|float|str|string|bool|array|matrix|map|tuple|any|error)\\b"
        }
      ]
    },
    "module-declarations": {
      "patterns": [
        {
          "name": "meta.module.ymir",
          "match": "^(module)\\s+([a-zA-Z_][a-zA-Z0-9_\\.]*)",
          "captures": {
            "1": {
              "name": "keyword.other.ymir"
            },
            "2": {
              "name": "entity.name.namespace.ymir"
            }
          }
        }
      ]
    },
    "builtin-functions": {
      "patterns": [
        {
          "name": "support.function.builtin.ymir",
          "match": "\\b(print|len|str|sqrt|sin|cos|tan|pow|abs|round|min|max|range|make_channel|panic|allocate|retain|release|socket|connect|send|recv|close|transpose|det|inverse|shape|matrix_gpu_available|matrix_eye|matrix_zeros|matrix_ones)\\b"
        }
      ]
    },
    "constants": {
      "patterns": [
        {
          "name": "constant.language.ymir",
          "match": "\\b(true|false|nil|self)\\b"
        }
      ]
    },
    "punctuation": {
      "patterns": [
        {
          "name": "punctuation.section.braces.ymir",
          "match": "[{}]"
        },
        {
          "name": "punctuation.section.brackets.ymir",
          "match": "[\\[\\]]"
        },
        {
          "name": "punctuation.section.parens.ymir",
          "match": "[()]"
        },
        {
          "name": "punctuation.separator.comma.ymir",
          "match": ","
        },
        {
          "name": "punctuation.separator.colon.ymir",
          "match": ":"
        },
        {
          "name": "punctuation.accessor.dot.ymir",
          "match": "\\."
        }
      ]
    }
  }
}
```

**Key patterns explained:**

- **Comments**: Matches `#` to end of line
- **Strings**: Double-quoted strings with escape sequences
- **Keywords**: Control flow (`if`, `while`, `for`), declarations (`func`, `class`)
- **Concurrency**: Ymir-specific keywords like `spawn`, `chan`, `select`
- **Operators**: Channel operators (`<-`), matrix multiplication (`@`), arithmetic
- **Numbers**: Integers, floats, and scientific notation
- **Function/Class declarations**: Captures names for special highlighting
- **Type annotations**: Type hint keywords
- **Built-in functions**: Common Ymir built-ins

### Step 2: Test Syntax Highlighting

1. Press `F5` in VSCode to launch Extension Development Host
2. Create a test file: `test.ymr`
3. Add sample code:

```ymr
module test

# This is a comment
func add(a: int, b: int) -> int {
    return a + b
}

class Calculator {
    func __init__(self) {
        self.result = 0
    }
}

func main() {
    # Channel operations
    ch = make_channel(10)
    ch <- 42
    value <- ch
    
    # Matrix multiplication
    matrix_a = [[1.0, 2.0], [3.0, 4.0]]
    result = matrix_a @ matrix_b
    
    spawn worker(1, ch)
}
```

You should see color-coded syntax!

---

## Language Configuration

Language configuration provides smart editor features like auto-closing brackets, comment toggling, and indentation.

### Create language-configuration.json

Create `language-configuration.json` in the project root:

```json
{
  "comments": {
    "lineComment": "#"
  },
  "brackets": [
    ["{", "}"],
    ["[", "]"],
    ["(", ")"]
  ],
  "autoClosingPairs": [
    { "open": "{", "close": "}" },
    { "open": "[", "close": "]" },
    { "open": "(", "close": ")" },
    { "open": "\"", "close": "\"", "notIn": ["string"] }
  ],
  "surroundingPairs": [
    ["{", "}"],
    ["[", "]"],
    ["(", ")"],
    ["\"", "\""]
  ],
  "indentationRules": {
    "increaseIndentPattern": "^.*\\{[^}\"']*$",
    "decreaseIndentPattern": "^\\s*\\}.*$"
  },
  "folding": {
    "markers": {
      "start": "^\\s*#\\s*region\\b",
      "end": "^\\s*#\\s*endregion\\b"
    }
  },
  "wordPattern": "(-?\\d*\\.\\d\\w*)|([^\\`\\~\\!\\@\\#\\%\\^\\&\\*\\(\\)\\-\\=\\+\\[\\{\\]\\}\\\\\\|\\;\\:\\'\\\"\\,\\.\\<\\>\\/\\?\\s]+)"
}
```

**Features provided:**

- **Comments**: `Ctrl+/` toggles `#` comments
- **Brackets**: Matched bracket highlighting
- **Auto-closing**: Automatically closes `{`, `[`, `(`, `"`
- **Indentation**: Auto-indent after `{`, outdent after `}`
- **Folding**: Code folding support
- **Word Pattern**: Defines what constitutes a "word" for selections

---

## Autocompletion Provider

Now we'll implement intelligent autocompletion using TypeScript.

### Step 1: Create Completion Provider

Create `src/providers/completionProvider.ts`:

```typescript
import * as vscode from 'vscode';

export class YmirCompletionProvider implements vscode.CompletionItemProvider {
    
    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): vscode.ProviderResult<vscode.CompletionItem[] | vscode.CompletionList> {
        
        const completionItems: vscode.CompletionItem[] = [];
        
        // Get configuration
        const config = vscode.workspace.getConfiguration('ymir');
        if (!config.get('completion.enabled', true)) {
            return completionItems;
        }
        
        // Add keyword completions
        completionItems.push(...this.getKeywordCompletions());
        
        // Add built-in function completions
        completionItems.push(...this.getBuiltinCompletions());
        
        // Add snippet completions
        completionItems.push(...this.getSnippetCompletions());
        
        // Context-aware completions
        const line = document.lineAt(position).text;
        const prefix = line.substring(0, position.character);
        
        // After "func " suggest function template
        if (prefix.match(/func\s+$/)) {
            completionItems.push(this.getFunctionTemplate());
        }
        
        // After "class " suggest class template
        if (prefix.match(/class\s+$/)) {
            completionItems.push(this.getClassTemplate());
        }
        
        // Type annotations after colon
        if (prefix.match(/:\s*$/)) {
            completionItems.push(...this.getTypeCompletions());
        }
        
        // Concurrency patterns
        if (prefix.includes('spawn') || prefix.includes('chan')) {
            completionItems.push(...this.getConcurrencyCompletions());
        }
        
        return completionItems;
    }
    
    private getKeywordCompletions(): vscode.CompletionItem[] {
        const keywords = [
            'func', 'class', 'if', 'else', 'while', 'for', 'return',
            'break', 'continue', 'in', 'import', 'export', 'module',
            'var', 'try', 'except', 'finally', 'throw', 'exception',
            'spawn', 'chan', 'select', 'async', 'await', 'as'
        ];
        
        return keywords.map(keyword => {
            const item = new vscode.CompletionItem(keyword, vscode.CompletionItemKind.Keyword);
            item.detail = 'Ymir keyword';
            return item;
        });
    }
    
    private getBuiltinCompletions(): vscode.CompletionItem[] {
        const builtins = [
            { name: 'print', signature: 'print(value: any)', doc: 'Print a value to stdout' },
            { name: 'len', signature: 'len(collection: any) -> int', doc: 'Get length of collection' },
            { name: 'str', signature: 'str(value: any) -> string', doc: 'Convert value to string' },
            { name: 'sqrt', signature: 'sqrt(x: float) -> float', doc: 'Square root' },
            { name: 'sin', signature: 'sin(x: float) -> float', doc: 'Sine function' },
            { name: 'cos', signature: 'cos(x: float) -> float', doc: 'Cosine function' },
            { name: 'pow', signature: 'pow(base: float, exp: float) -> float', doc: 'Power function' },
            { name: 'abs', signature: 'abs(x: float) -> float', doc: 'Absolute value' },
            { name: 'min', signature: 'min(values: ...any) -> any', doc: 'Minimum value' },
            { name: 'max', signature: 'max(values: ...any) -> any', doc: 'Maximum value' },
            { name: 'make_channel', signature: 'make_channel(size: int) -> chan', doc: 'Create a channel for concurrency' },
            { name: 'panic', signature: 'panic(message: string)', doc: 'Raise a panic error' },
            { name: 'transpose', signature: 'transpose(matrix: matrix) -> matrix', doc: 'Transpose a matrix' },
            { name: 'det', signature: 'det(matrix: matrix) -> float', doc: 'Matrix determinant' },
            { name: 'inverse', signature: 'inverse(matrix: matrix) -> matrix', doc: 'Matrix inverse' },
            { name: 'shape', signature: 'shape(matrix: matrix) -> tuple', doc: 'Get matrix shape' },
            { name: 'matrix_gpu_available', signature: 'matrix_gpu_available() -> bool', doc: 'Check if GPU is available' },
        ];
        
        return builtins.map(builtin => {
            const item = new vscode.CompletionItem(builtin.name, vscode.CompletionItemKind.Function);
            item.detail = builtin.signature;
            item.documentation = new vscode.MarkdownString(builtin.doc);
            item.insertText = new vscode.SnippetString(`${builtin.name}($1)$0`);
            return item;
        });
    }
    
    private getSnippetCompletions(): vscode.CompletionItem[] {
        const snippets: vscode.CompletionItem[] = [];
        
        // Main function snippet
        const mainSnippet = new vscode.CompletionItem('main', vscode.CompletionItemKind.Snippet);
        mainSnippet.insertText = new vscode.SnippetString(
            'func main() {\n\t$0\n}'
        );
        mainSnippet.documentation = 'Main function template';
        snippets.push(mainSnippet);
        
        // For loop snippet
        const forSnippet = new vscode.CompletionItem('for', vscode.CompletionItemKind.Snippet);
        forSnippet.insertText = new vscode.SnippetString(
            'for ${1:item} in ${2:collection} {\n\t$0\n}'
        );
        forSnippet.documentation = 'For-in loop';
        snippets.push(forSnippet);
        
        // While loop snippet
        const whileSnippet = new vscode.CompletionItem('while', vscode.CompletionItemKind.Snippet);
        whileSnippet.insertText = new vscode.SnippetString(
            'while ${1:condition} {\n\t$0\n}'
        );
        whileSnippet.documentation = 'While loop';
        snippets.push(whileSnippet);
        
        // If-else snippet
        const ifSnippet = new vscode.CompletionItem('if', vscode.CompletionItemKind.Snippet);
        ifSnippet.insertText = new vscode.SnippetString(
            'if ${1:condition} {\n\t$0\n}'
        );
        ifSnippet.documentation = 'If statement';
        snippets.push(ifSnippet);
        
        // Try-except snippet
        const trySnippet = new vscode.CompletionItem('try', vscode.CompletionItemKind.Snippet);
        trySnippet.insertText = new vscode.SnippetString(
            'try {\n\t$1\n} except ${2:Exception} as ${3:error} {\n\t$0\n}'
        );
        trySnippet.documentation = 'Try-except block';
        snippets.push(trySnippet);
        
        return snippets;
    }
    
    private getFunctionTemplate(): vscode.CompletionItem {
        const item = new vscode.CompletionItem('function', vscode.CompletionItemKind.Snippet);
        item.insertText = new vscode.SnippetString(
            '${1:function_name}(${2:params}) -> ${3:type} {\n\t$0\n}'
        );
        item.documentation = 'Function template';
        return item;
    }
    
    private getClassTemplate(): vscode.CompletionItem {
        const item = new vscode.CompletionItem('class', vscode.CompletionItemKind.Snippet);
        item.insertText = new vscode.SnippetString(
            '${1:ClassName} {\n\tfunc __init__(self) {\n\t\t$0\n\t}\n}'
        );
        item.documentation = 'Class template';
        return item;
    }
    
    private getTypeCompletions(): vscode.CompletionItem[] {
        const types = [
            'int', 'float', 'string', 'str', 'bool', 'array', 'matrix',
            'map', 'tuple', 'any', 'error', 'chan'
        ];
        
        return types.map(type => {
            const item = new vscode.CompletionItem(type, vscode.CompletionItemKind.TypeParameter);
            item.detail = 'Ymir type';
            return item;
        });
    }
    
    private getConcurrencyCompletions(): vscode.CompletionItem[] {
        const items: vscode.CompletionItem[] = [];
        
        // Spawn pattern
        const spawnItem = new vscode.CompletionItem('spawn', vscode.CompletionItemKind.Snippet);
        spawnItem.insertText = new vscode.SnippetString('spawn ${1:function}($2)');
        spawnItem.documentation = 'Spawn a concurrent task';
        items.push(spawnItem);
        
        // Channel send
        const sendItem = new vscode.CompletionItem('<- (send)', vscode.CompletionItemKind.Snippet);
        sendItem.insertText = new vscode.SnippetString('${1:channel} <- ${2:value}');
        sendItem.documentation = 'Send value to channel';
        items.push(sendItem);
        
        // Channel receive
        const recvItem = new vscode.CompletionItem('<- (receive)', vscode.CompletionItemKind.Snippet);
        recvItem.insertText = new vscode.SnippetString('${1:value} <- ${2:channel}');
        recvItem.documentation = 'Receive value from channel';
        items.push(recvItem);
        
        return items;
    }
}
```

**Key features:**

- **Keyword completion**: All Ymir keywords
- **Built-in functions**: With signatures and documentation
- **Context-aware**: Different suggestions based on cursor position
- **Snippets**: Multi-line code templates
- **Concurrency support**: Channel operations and spawn patterns

---

## Diagnostics Provider

Diagnostics provide real-time error checking as you type.

### Step 1: Create Diagnostics Provider

Create `src/providers/diagnosticsProvider.ts`:

```typescript
import * as vscode from 'vscode';

export class YmirDiagnosticsProvider {
    private diagnosticCollection: vscode.DiagnosticCollection;
    
    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('ymir');
    }
    
    public updateDiagnostics(document: vscode.TextDocument): void {
        const config = vscode.workspace.getConfiguration('ymir');
        if (!config.get('diagnostics.enabled', true)) {
            this.diagnosticCollection.clear();
            return;
        }
        
        if (document.languageId !== 'ymir') {
            return;
        }
        
        const diagnostics: vscode.Diagnostic[] = [];
        const text = document.getText();
        const lines = text.split('\n');
        
        // Check for missing module declaration
        this.checkModuleDeclaration(lines, diagnostics);
        
        // Check for common syntax errors
        this.checkBracketMatching(text, document, diagnostics);
        this.checkFunctionSyntax(lines, document, diagnostics);
        this.checkChannelOperators(lines, document, diagnostics);
        this.checkTypeAnnotations(lines, document, diagnostics);
        
        this.diagnosticCollection.set(document.uri, diagnostics);
    }
    
    private checkModuleDeclaration(lines: string[], diagnostics: vscode.Diagnostic[]): void {
        // First non-comment, non-empty line should be module declaration
        let foundModule = false;
        
        for (let i = 0; i < Math.min(10, lines.length); i++) {
            const line = lines[i].trim();
            
            // Skip comments and empty lines
            if (line === '' || line.startsWith('#')) {
                continue;
            }
            
            if (line.startsWith('module ')) {
                foundModule = true;
                break;
            } else {
                // Found non-module statement
                break;
            }
        }
        
        if (!foundModule && lines.length > 0) {
            const range = new vscode.Range(0, 0, 0, lines[0].length);
            const diagnostic = new vscode.Diagnostic(
                range,
                'Ymir files should start with a module declaration (e.g., "module main")',
                vscode.DiagnosticSeverity.Warning
            );
            diagnostic.code = 'missing-module';
            diagnostics.push(diagnostic);
        }
    }
    
    private checkBracketMatching(text: string, document: vscode.TextDocument, diagnostics: vscode.Diagnostic[]): void {
        const brackets = [
            { open: '{', close: '}', name: 'brace' },
            { open: '[', close: ']', name: 'bracket' },
            { open: '(', close: ')', name: 'parenthesis' }
        ];
        
        for (const bracket of brackets) {
            const stack: number[] = [];
            
            for (let i = 0; i < text.length; i++) {
                if (text[i] === bracket.open) {
                    stack.push(i);
                } else if (text[i] === bracket.close) {
                    if (stack.length === 0) {
                        const position = document.positionAt(i);
                        const range = new vscode.Range(position, position.translate(0, 1));
                        const diagnostic = new vscode.Diagnostic(
                            range,
                            `Unmatched closing ${bracket.name} '${bracket.close}'`,
                            vscode.DiagnosticSeverity.Error
                        );
                        diagnostics.push(diagnostic);
                    } else {
                        stack.pop();
                    }
                }
            }
            
            // Unclosed brackets
            for (const pos of stack) {
                const position = document.positionAt(pos);
                const range = new vscode.Range(position, position.translate(0, 1));
                const diagnostic = new vscode.Diagnostic(
                    range,
                    `Unclosed ${bracket.name} '${bracket.open}'`,
                    vscode.DiagnosticSeverity.Error
                );
                diagnostics.push(diagnostic);
            }
        }
    }
    
    private checkFunctionSyntax(lines: string[], document: vscode.TextDocument, diagnostics: vscode.Diagnostic[]): void {
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // Check function declarations
            const funcMatch = line.match(/^\s*func\s+(\w+)\s*\(/);
            if (funcMatch) {
                // Check if function has opening brace
                if (!line.includes('{') && (i + 1 >= lines.length || !lines[i + 1].includes('{'))) {
                    const range = new vscode.Range(i, 0, i, line.length);
                    const diagnostic = new vscode.Diagnostic(
                        range,
                        'Function declaration should be followed by opening brace {',
                        vscode.DiagnosticSeverity.Error
                    );
                    diagnostics.push(diagnostic);
                }
                
                // Check for return type annotation
                if (!line.includes('->') && !line.includes('{')) {
                    const range = new vscode.Range(i, 0, i, line.length);
                    const diagnostic = new vscode.Diagnostic(
                        range,
                        'Consider adding return type annotation with ->',
                        vscode.DiagnosticSeverity.Hint
                    );
                    diagnostic.code = 'missing-return-type';
                    diagnostics.push(diagnostic);
                }
            }
            
            // Check for missing colons in parameters
            const paramMatch = line.match(/func\s+\w+\s*\(([^)]+)\)/);
            if (paramMatch) {
                const params = paramMatch[1];
                // Check if parameters have type annotations
                const paramList = params.split(',');
                for (const param of paramList) {
                    if (param.trim() && !param.includes(':')) {
                        const range = new vscode.Range(i, 0, i, line.length);
                        const diagnostic = new vscode.Diagnostic(
                            range,
                            'Function parameters should have type annotations (e.g., name: type)',
                            vscode.DiagnosticSeverity.Warning
                        );
                        diagnostic.code = 'missing-type-annotation';
                        diagnostics.push(diagnostic);
                        break;
                    }
                }
            }
        }
    }
    
    private checkChannelOperators(lines: string[], document: vscode.TextDocument, diagnostics: vscode.Diagnostic[]): void {
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // Check for channel operations
            if (line.includes('<-')) {
                // Check for proper spacing
                if (line.match(/<\s+-/) || line.match(/-\s+>/)) {
                    const index = line.indexOf('<-');
                    const range = new vscode.Range(i, index, i, index + 2);
                    const diagnostic = new vscode.Diagnostic(
                        range,
                        'Channel operator should be <- without spaces',
                        vscode.DiagnosticSeverity.Warning
                    );
                    diagnostics.push(diagnostic);
                }
            }
        }
    }
    
    private checkTypeAnnotations(lines: string[], document: vscode.TextDocument, diagnostics: vscode.Diagnostic[]): void {
        const validTypes = new Set([
            'int', 'float', 'string', 'str', 'bool', 'array', 'matrix',
            'map', 'tuple', 'any', 'error', 'chan'
        ]);
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // Find type annotations (after colons)
            const typeMatches = line.matchAll(/:\s*([a-zA-Z_]\w*)/g);
            
            for (const match of typeMatches) {
                const typeName = match[1];
                
                // Skip if it's a valid type or looks like a custom class
                if (validTypes.has(typeName) || typeName[0] === typeName[0].toUpperCase()) {
                    continue;
                }
                
                // Potential typo or unknown type
                const index = match.index! + match[0].indexOf(typeName);
                const range = new vscode.Range(i, index, i, index + typeName.length);
                const diagnostic = new vscode.Diagnostic(
                    range,
                    `Unknown type '${typeName}'. Did you mean: ${this.suggestType(typeName)}?`,
                    vscode.DiagnosticSeverity.Warning
                );
                diagnostic.code = 'unknown-type';
                diagnostics.push(diagnostic);
            }
        }
    }
    
    private suggestType(typeName: string): string {
        const suggestions: { [key: string]: string } = {
            'integer': 'int',
            'number': 'int or float',
            'String': 'string',
            'boolean': 'bool',
            'Boolean': 'bool',
            'dict': 'map',
            'list': 'array',
            'List': 'array',
        };
        
        return suggestions[typeName] || 'int, float, string, bool, array, etc.';
    }
    
    public dispose(): void {
        this.diagnosticCollection.dispose();
    }
}
```

**Diagnostic checks:**

- **Module declaration**: Warns if file doesn't start with `module`
- **Bracket matching**: Detects unmatched `{`, `[`, `(`
- **Function syntax**: Checks for proper function structure
- **Channel operators**: Validates `<-` spacing
- **Type annotations**: Warns about unknown types with suggestions

---

## Main Extension File

Now we'll wire everything together in the main extension file.

### Update src/extension.ts

Replace the generated `src/extension.ts` with:

```typescript
import * as vscode from 'vscode';
import { YmirCompletionProvider } from './providers/completionProvider';
import { YmirDiagnosticsProvider } from './providers/diagnosticsProvider';

let diagnosticsProvider: YmirDiagnosticsProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('Ymir language extension is now active');
    
    // Register completion provider
    const completionProvider = vscode.languages.registerCompletionItemProvider(
        { language: 'ymir', scheme: 'file' },
        new YmirCompletionProvider(),
        '.', // Trigger on dot for method completion
        ' '  // Trigger on space for keyword completion
    );
    
    // Initialize diagnostics provider
    diagnosticsProvider = new YmirDiagnosticsProvider();
    
    // Update diagnostics on document changes
    const diagnosticsSubscription = vscode.workspace.onDidChangeTextDocument(event => {
        if (event.document.languageId === 'ymir') {
            diagnosticsProvider.updateDiagnostics(event.document);
        }
    });
    
    // Update diagnostics on document open
    const openSubscription = vscode.workspace.onDidOpenTextDocument(document => {
        if (document.languageId === 'ymir') {
            diagnosticsProvider.updateDiagnostics(document);
        }
    });
    
    // Update diagnostics for all open Ymir files
    vscode.workspace.textDocuments.forEach(document => {
        if (document.languageId === 'ymir') {
            diagnosticsProvider.updateDiagnostics(document);
        }
    });
    
    // Register commands
    const formatCommand = vscode.commands.registerCommand('ymir.format', () => {
        vscode.window.showInformationMessage('Ymir formatting coming soon!');
    });
    
    const runCommand = vscode.commands.registerCommand('ymir.run', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === 'ymir') {
            const terminal = vscode.window.createTerminal('Ymir');
            terminal.show();
            terminal.sendText(`ymir run ${editor.document.uri.fsPath}`);
        } else {
            vscode.window.showErrorMessage('No active Ymir file to run');
        }
    });
    
    // Add to subscriptions for cleanup
    context.subscriptions.push(
        completionProvider,
        diagnosticsSubscription,
        openSubscription,
        formatCommand,
        runCommand
    );
    
    // Show welcome message
    vscode.window.showInformationMessage('Ymir language support activated!');
}

export function deactivate() {
    if (diagnosticsProvider) {
        diagnosticsProvider.dispose();
    }
}
```

**Key components:**

- **Completion provider**: Registered for `.ymr` files
- **Diagnostics**: Updates on file changes and opens
- **Commands**: Optional `ymir.run` command to execute files
- **Cleanup**: Proper disposal on deactivation

---

## Testing and Debugging

### Step 1: Compile TypeScript

```bash
npm run compile
```

Or for continuous compilation:

```bash
npm run watch
```

### Step 2: Launch Extension Development Host

1. Press `F5` in VSCode
2. A new VSCode window opens with your extension loaded
3. Create or open a `.ymr` file

### Step 3: Test Features

Create a test file `test.ymr`:

```ymr
module test

func add(a: int, b: int) -> int {
    return a + b
}

func main() {
    result = add(10, 20)
    print("Result: " + str(result))
    
    # Test channel operations
    ch = make_channel(5)
    spawn worker(ch)
    value <- ch
}
```

**Test checklist:**

- [ ] Syntax highlighting works correctly
- [ ] Keywords autocomplete when typing
- [ ] Built-in functions show documentation
- [ ] Bracket auto-closing works
- [ ] Comment toggling (`Ctrl+/`) works
- [ ] Diagnostics show for syntax errors
- [ ] Red squiggles appear for mismatched brackets

### Step 4: Debug Extension

To debug your extension code:

1. Set breakpoints in `.ts` files
2. Press `F5` to launch debugger
3. Trigger the code path in the Extension Development Host
4. Debugger pauses at breakpoints

### Step 5: View Extension Logs

- Open Debug Console in the main VSCode window
- Look for `console.log()` output
- Check for errors or warnings

### Common Issues and Solutions

**Problem**: Syntax highlighting doesn't work
- **Solution**: Check that `syntaxes/ymir.tmLanguage.json` path is correct in `package.json`
- Reload the Extension Development Host with `Ctrl+R`

**Problem**: Completion doesn't trigger
- **Solution**: Verify `activationEvents` includes `"onLanguage:ymir"` in `package.json`
- Check that file has `.ymr` extension

**Problem**: Diagnostics not updating
- **Solution**: Ensure `diagnostics.enabled` is `true` in settings
- Check console for errors in diagnostics provider

---

## Packaging and Publishing

### Step 1: Install vsce (Visual Studio Code Extensions)

```bash
npm install -g @vscode/vsce
```

### Step 2: Update README.md

Create a comprehensive README for users:

```markdown
# Ymir Language Support for Visual Studio Code

Provides rich language support for the Ymir programming language.

## Features

- **Syntax Highlighting**: Full syntax highlighting for Ymir files (`.ymr`)
- **Autocompletion**: Intelligent code completion for keywords, built-in functions, and snippets
- **Diagnostics**: Real-time error checking for common syntax issues
- **Code Snippets**: Quick templates for functions, classes, loops, and more
- **Bracket Matching**: Auto-closing and matching for brackets, parens, and braces

## Usage

1. Install the extension
2. Open or create a `.ymr` file
3. Start coding with full language support!

## Configuration

Settings available in VSCode settings:

- `ymir.diagnostics.enabled`: Enable/disable diagnostic error checking (default: `true`)
- `ymir.completion.enabled`: Enable/disable autocompletion (default: `true`)

## Requirements

- Visual Studio Code 1.75.0 or higher
- Ymir compiler installed (optional, for running files)

## Keyboard Shortcuts

- `Ctrl+Space`: Trigger autocompletion
- `Ctrl+/`: Toggle line comment
- `F5`: Run current Ymir file (requires Ymir compiler)

## Known Issues

- Full LSP features (go-to-definition, refactoring) coming in future versions
- Matrix operations syntax highlighting may be limited in complex expressions

## Release Notes

### 0.1.0

Initial release with:
- Syntax highlighting
- Autocompletion
- Basic diagnostics

## Contributing

Found a bug or have a feature request? Open an issue on GitHub!

## License

MIT
```

### Step 3: Package Extension

```bash
vsce package
```

This creates a `.vsix` file (e.g., `ymir-language-0.1.0.vsix`).

### Step 4: Test Installation

Install the packaged extension locally:

```bash
code --install-extension ymir-language-0.1.0.vsix
```

### Step 5: Publish to Marketplace (Optional)

To publish to the VSCode Marketplace:

1. Create a publisher account at [Visual Studio Marketplace](https://marketplace.visualstudio.com/manage)

2. Create a Personal Access Token (PAT) in Azure DevOps

3. Login with vsce:
   ```bash
   vsce login your-publisher-name
   ```

4. Publish:
   ```bash
   vsce publish
   ```

### Alternative: Distribute .vsix File

You can share the `.vsix` file directly:
- Users install with: `code --install-extension ymir-language-0.1.0.vsix`
- Or through VSCode UI: Extensions → ... → Install from VSIX

---

## Future: Language Server Protocol Migration

Your extension is designed with a **hybrid architecture** that can be upgraded to a full LSP implementation.

### Why Migrate to LSP?

**Current limitations of provider-based approach:**
- Limited semantic understanding (regex-based parsing)
- No cross-file analysis (imports, exports)
- Can't leverage existing Ymir parser/type checker
- Performance issues with large files

**LSP benefits:**
- Reuse Ymir's Python parser, type checker, and semantic analyzer
- Cross-file intelligence (imports, go-to-definition across modules)
- Advanced features: rename refactoring, find all references, workspace symbols
- Better performance (separate process)
- Consistency with Ymir's actual behavior

### Migration Architecture

**Current Architecture:**
```
VSCode Extension (TypeScript)
├── Completion Provider (simple patterns)
├── Diagnostics Provider (regex-based)
└── Syntax Highlighting (TextMate grammar)
```

**LSP Architecture:**
```
VSCode Extension (TypeScript)
├── Language Client
│   └── Communicates via LSP over stdio
└── Syntax Highlighting (keep TextMate)

Language Server (Python)
├── Uses existing Ymir lexer, parser, type checker
├── Provides diagnostics from actual compilation
├── Provides completions based on semantic analysis
└── Runs in separate process
```

### Migration Steps

#### 1. Install LSP Dependencies

In your extension:
```bash
npm install vscode-languageclient
```

For the server (Python):
```bash
pip install pygls  # Python Generic Language Server
```

#### 2. Create Language Server (Python)

Create `ymir-language-server/server.py`:

```python
from pygls.server import LanguageServer
from pygls.lsp.methods import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    COMPLETION,
)
from pygls.lsp.types import (
    CompletionItem,
    CompletionList,
    CompletionParams,
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)

# Import Ymir's existing components
from ymir.core.lexer import Lexer
from ymir.core.parser import Parser
from ymir.core.type_checker import TypeChecker

server = LanguageServer('ymir-language-server', 'v0.1')

@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params):
    """Validate document on open"""
    validate_document(ls, params.text_document.uri)

@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls, params):
    """Validate document on change"""
    validate_document(ls, params.text_document.uri)

def validate_document(ls: LanguageServer, uri: str):
    """Run Ymir compiler and report diagnostics"""
    document = ls.workspace.get_document(uri)
    
    try:
        # Use Ymir's actual lexer and parser
        lexer = Lexer(document.source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        type_checker = TypeChecker()
        type_checker.check(ast)
        
        # No errors - clear diagnostics
        ls.publish_diagnostics(uri, [])
        
    except Exception as e:
        # Convert Ymir errors to LSP diagnostics
        diagnostic = Diagnostic(
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=10)
            ),
            message=str(e),
            severity=DiagnosticSeverity.Error
        )
        ls.publish_diagnostics(uri, [diagnostic])

@server.feature(COMPLETION)
async def completions(ls: LanguageServer, params: CompletionParams):
    """Provide completions based on semantic analysis"""
    document = ls.workspace.get_document(params.text_document.uri)
    
    # Use Ymir's symbol table to provide accurate completions
    items = []
    
    # Example: Get available functions in scope
    # This would use Ymir's semantic analyzer
    
    return CompletionList(is_incomplete=False, items=items)

if __name__ == '__main__':
    server.start_io()
```

#### 3. Update Extension to Language Client

Update `src/extension.ts`:

```typescript
import * as path from 'path';
import { workspace, ExtensionContext } from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: ExtensionContext) {
    // Server options - launch Python language server
    const serverOptions: ServerOptions = {
        command: 'python',
        args: [path.join(context.extensionPath, 'server', 'server.py')],
        transport: TransportKind.stdio
    };
    
    // Client options - what files to observe
    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'ymir' }],
        synchronize: {
            fileEvents: workspace.createFileSystemWatcher('**/.ymr')
        }
    };
    
    // Create and start language client
    client = new LanguageClient(
        'ymirLanguageServer',
        'Ymir Language Server',
        serverOptions,
        clientOptions
    );
    
    client.start();
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
```

#### 4. Benefits After Migration

Once migrated to LSP:

**Accurate diagnostics**: Errors from actual Ymir compiler
```ymr
func divide(a: int, b: string) -> int {  # Type error caught!
    return a / b
}
```

**Go-to-definition**: Jump to function definitions across files
```ymr
import stdlib.math
result = stdlib.math.sqrt(16.0)  # Ctrl+Click jumps to sqrt definition
```

**Find references**: See all usages of a function
```ymr
func calculate() { }  # Find all references finds every call site
```

**Rename refactoring**: Safely rename symbols across entire project

**Hover information**: Rich tooltips with type information and docs

### When to Migrate?

Migrate when:
- User base grows and demands advanced features
- Regex-based diagnostics become insufficient
- You want cross-file analysis and imports
- Performance becomes an issue with large codebases

Keep current approach if:
- Features are sufficient for now
- Want to avoid Python dependency management
- User base is small and experimental

---

## Advanced Tips and Best Practices

### Tip 1: Add Icon for Better UX

Create a 128x128 PNG icon and add to `package.json`:

```json
{
  "icon": "images/ymir-icon.png"
}
```

### Tip 2: Add Hover Provider

Enhance your extension with hover tooltips:

```typescript
class YmirHoverProvider implements vscode.HoverProvider {
    provideHover(document: vscode.TextDocument, position: vscode.Position): vscode.Hover | null {
        const range = document.getWordRangeAtPosition(position);
        const word = document.getText(range);
        
        // Provide hover info for built-ins
        const builtins: { [key: string]: string } = {
            'print': '**print**(value: any)\n\nPrint a value to stdout',
            'spawn': '**spawn** function(args...)\n\nSpawn a concurrent task',
            // Add more...
        };
        
        if (builtins[word]) {
            return new vscode.Hover(new vscode.MarkdownString(builtins[word]));
        }
        
        return null;
    }
}

// Register in activate():
vscode.languages.registerHoverProvider('ymir', new YmirHoverProvider());
```

### Tip 3: Add Definition Provider (Basic)

Simple go-to-definition within single file:

```typescript
class YmirDefinitionProvider implements vscode.DefinitionProvider {
    provideDefinition(document: vscode.TextDocument, position: vscode.Position): vscode.Location | null {
        const word = document.getText(document.getWordRangeAtPosition(position));
        const text = document.getText();
        
        // Find function definition
        const regex = new RegExp(`func\\s+${word}\\s*\\(`, 'g');
        const match = regex.exec(text);
        
        if (match) {
            const pos = document.positionAt(match.index);
            return new vscode.Location(document.uri, pos);
        }
        
        return null;
    }
}
```

### Tip 4: Performance Optimization

For large files, debounce diagnostics:

```typescript
let diagnosticsTimeout: NodeJS.Timeout;

vscode.workspace.onDidChangeTextDocument(event => {
    clearTimeout(diagnosticsTimeout);
    diagnosticsTimeout = setTimeout(() => {
        diagnosticsProvider.updateDiagnostics(event.document);
    }, 500); // Wait 500ms after typing stops
});
```

### Tip 5: Add File Templates

Create command to generate new Ymir files:

```typescript
vscode.commands.registerCommand('ymir.newFile', async () => {
    const fileName = await vscode.window.showInputBox({
        prompt: 'Enter module name'
    });
    
    if (fileName) {
        const template = `module ${fileName}

func main() {
    print("Hello from ${fileName}!")
}

main()
`;
        const doc = await vscode.workspace.openTextDocument({
            content: template,
            language: 'ymir'
        });
        vscode.window.showTextDocument(doc);
    }
});
```

---

## Appendix: Complete File Structure

Final extension structure:

```
ymir-language/
├── .vscode/
│   ├── launch.json
│   └── tasks.json
├── src/
│   ├── extension.ts
│   ├── providers/
│   │   ├── completionProvider.ts
│   │   └── diagnosticsProvider.ts
│   └── test/
│       └── extension.test.ts
├── syntaxes/
│   └── ymir.tmLanguage.json
├── images/
│   └── ymir-icon.png
├── language-configuration.json
├── package.json
├── tsconfig.json
├── README.md
├── CHANGELOG.md
├── LICENSE
└── .vscodeignore
```

---

## Summary

You've now created a full-featured VSCode extension for Ymir with:

✅ **Syntax Highlighting**: TextMate grammar with all Ymir features
✅ **Autocompletion**: Context-aware suggestions and snippets
✅ **Diagnostics**: Real-time error checking
✅ **Language Configuration**: Brackets, comments, indentation
✅ **Extensible Architecture**: Ready for LSP migration

### Next Steps

1. **Test thoroughly** with real Ymir codebases
2. **Gather feedback** from Ymir users
3. **Iterate** on completion and diagnostic rules
4. **Consider LSP migration** when ready for advanced features
5. **Publish** to VSCode Marketplace

### Resources

- [VSCode Extension API](https://code.visualstudio.com/api)
- [TextMate Grammar Guide](https://macromates.com/manual/en/language_grammars)
- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
- [Ymir Documentation](https://github.com/bjornaer/ymir)

Happy coding! 🎉

