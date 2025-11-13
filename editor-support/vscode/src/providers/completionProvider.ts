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

