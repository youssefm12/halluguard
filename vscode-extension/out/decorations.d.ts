/**
 * Decorations & Diagnostics — visual feedback in the editor.
 *
 * Creates:
 * - Colored underlines (red / orange / yellow) in the active editor.
 * - VSCode Diagnostics pushed to the "Problems" panel.
 */
import * as vscode from "vscode";
import { AnalysisReport } from "./analyzer";
export declare class DecorationManager {
    private readonly highDecoration;
    private readonly mediumDecoration;
    private readonly lowDecoration;
    constructor();
    /**
     * Build an array of `vscode.Diagnostic` objects from the analysis report.
     */
    createDiagnostics(doc: vscode.TextDocument, report: AnalysisReport): vscode.Diagnostic[];
    /**
     * Apply coloured underlines in the active editor for each hallucination.
     */
    applyDecorations(editor: vscode.TextEditor, report: AnalysisReport): void;
    /**
     * Locate the token in the document. Falls back to its declared line
     * (or line 0) if not found.
     */
    private findTokenRange;
    private mapSeverity;
}
//# sourceMappingURL=decorations.d.ts.map