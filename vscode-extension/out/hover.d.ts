/**
 * Hover Provider — rich tooltips when hovering over hallucinated code.
 *
 * Displays:
 * - Hallucination type
 * - Natural-language explanation
 * - Risk score
 * - Correction suggestion
 */
import * as vscode from "vscode";
import { Analyzer } from "./analyzer";
export declare class HalluGuardHoverProvider implements vscode.HoverProvider {
    private readonly analyzer;
    constructor(analyzer: Analyzer);
    provideHover(document: vscode.TextDocument, position: vscode.Position, _token: vscode.CancellationToken): vscode.Hover | null;
}
//# sourceMappingURL=hover.d.ts.map