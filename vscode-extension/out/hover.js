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
exports.HalluGuardHoverProvider = void 0;
/**
 * Hover Provider — rich tooltips when hovering over hallucinated code.
 *
 * Displays:
 * - Hallucination type
 * - Natural-language explanation
 * - Risk score
 * - Correction suggestion
 */
const vscode = __importStar(require("vscode"));
class HalluGuardHoverProvider {
    analyzer;
    constructor(analyzer) {
        this.analyzer = analyzer;
    }
    provideHover(document, position, _token) {
        // Check existing diagnostics for this position
        const diags = vscode.languages.getDiagnostics(document.uri);
        const matching = diags.filter((d) => d.source === "HalluGuard AI" && d.range.contains(position));
        if (matching.length === 0) {
            return null;
        }
        const parts = [];
        for (const diag of matching) {
            const h = diag._halluguard;
            if (!h) {
                continue;
            }
            const md = new vscode.MarkdownString();
            md.isTrusted = true;
            md.supportThemeIcons = true;
            md.appendMarkdown(`### $(shield) HalluGuard AI\n\n`);
            md.appendMarkdown(`| | |\n|---|---|\n`);
            md.appendMarkdown(`| **Type** | \`${h.type}\` |\n`);
            md.appendMarkdown(`| **Token** | \`${h.token}\` |\n`);
            md.appendMarkdown(`| **Severity** | ${severityBadge(h.severity)} |\n`);
            md.appendMarkdown(`| **Explanation** | ${h.explanation} |\n`);
            md.appendMarkdown(`| **Suggestion** | ${h.suggestion || "—"} |\n`);
            parts.push(md);
        }
        return parts.length > 0 ? new vscode.Hover(parts) : null;
    }
}
exports.HalluGuardHoverProvider = HalluGuardHoverProvider;
function severityBadge(severity) {
    switch ((severity ?? "").toUpperCase()) {
        case "CRITICAL":
            return "$(error) CRITICAL";
        case "HIGH":
            return "$(error) HIGH";
        case "MEDIUM":
            return "$(warning) MEDIUM";
        default:
            return "$(info) LOW";
    }
}
//# sourceMappingURL=hover.js.map