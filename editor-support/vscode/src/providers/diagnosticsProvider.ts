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

