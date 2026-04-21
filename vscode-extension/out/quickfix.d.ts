/**
 * Quick Fix (Code Actions) — auto-correction for hallucinated code.
 *
 * Provides three actions for each HalluGuard diagnostic:
 * 1. **Apply fix** — replace the hallucinated token with the suggestion.
 * 2. **Ignore this warning** — insert a `halluguard-ignore` comment.
 * 3. **Show full report** — open the webview report panel.
 */
import * as vscode from "vscode";
export declare class HalluGuardCodeActionProvider implements vscode.CodeActionProvider {
    private readonly diagnosticCollection;
    static readonly providedKinds: vscode.CodeActionKind[];
    constructor(diagnosticCollection: vscode.DiagnosticCollection);
    provideCodeActions(document: vscode.TextDocument, range: vscode.Range | vscode.Selection, context: vscode.CodeActionContext, _token: vscode.CancellationToken): vscode.CodeAction[];
}
//# sourceMappingURL=quickfix.d.ts.map