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

