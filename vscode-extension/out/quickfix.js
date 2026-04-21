"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.HalluGuardCodeActionProvider = void 0;
/**
 * Quick Fix (Code Actions) — auto-correction for hallucinated code.
 *
 * Provides three actions for each HalluGuard diagnostic:
 * 1. **Apply fix** — replace the hallucinated token with the suggestion.
 * 2. **Ignore this warning** — insert a `halluguard-ignore` comment.
 * 3. **Show full report** — open the webview report panel.
 */
const vscode = __importStar(require("vscode"));
class HalluGuardCodeActionProvider {
    diagnosticCollection;
    static providedKinds = [
        vscode.CodeActionKind.QuickFix,
    ];
    constructor(diagnosticCollection) {
        this.diagnosticCollection = diagnosticCollection;
    }
    provideCodeActions(document, range, context, _token) {
        const actions = [];
        for (const diag of context.diagnostics) {
            if (diag.source !== "HalluGuard AI") {
                continue;
            }
            const h = diag._halluguard;
            if (!h) {
                continue;
            }
            // ── 1. Apply fix ────────────────────────────────────
            if (h.suggestion && h.suggestion !== "—") {
                const fixAction = new vscode.CodeAction(`HalluGuard: Apply fix → ${h.suggestion}`, vscode.CodeActionKind.QuickFix);
                fixAction.diagnostics = [diag];
                fixAction.isPreferred = true;
                const edit = new vscode.WorkspaceEdit();
                if (h.type === "unknown_import") {
                    // Replace the import name
                    edit.replace(document.uri, diag.range, h.suggestion);
                }
                else {
                    // Replace the function/method call token
                    edit.replace(document.uri, diag.range, h.suggestion);
                }
                fixAction.edit = edit;
                actions.push(fixAction);
            }
            // ── 2. Ignore this warning ──────────────────────────
            const ignoreAction = new vscode.CodeAction("HalluGuard: Ignore this warning", vscode.CodeActionKind.QuickFix);
            ignoreAction.diagnostics = [diag];
            const ignoreEdit = new vscode.WorkspaceEdit();
            const lineNum = diag.range.start.line;
            const lineText = document.lineAt(lineNum).text;
            const indent = lineText.match(/^(\s*)/)?.[1] ?? "";
            // Determine the comment prefix based on language
            const langId = document.languageId;
            const commentPrefix = langId === "python" ? "# halluguard-ignore" : "// halluguard-ignore";
            ignoreEdit.insert(document.uri, new vscode.Position(lineNum, 0), `${indent}${commentPrefix}\n`);
            ignoreAction.edit = ignoreEdit;
            actions.push(ignoreAction);
            // ── 3. Show full report ─────────────────────────────
            const reportAction = new vscode.CodeAction("HalluGuard: Show full report", vscode.CodeActionKind.QuickFix);
            reportAction.diagnostics = [diag];
            reportAction.command = {
                command: "halluguard.showReport",
                title: "Show HalluGuard Report",
            };
            actions.push(reportAction);
        }
        return actions;
    }
}
exports.HalluGuardCodeActionProvider = HalluGuardCodeActionProvider;
//# sourceMappingURL=quickfix.js.map