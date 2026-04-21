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
exports.Analyzer = void 0;
/**
 * Analyzer — communicates with the HalluGuard Python server.
 *
 * Manages:
 * - Spawning / stopping the FastAPI server process.
 * - HTTP calls to POST /analyze and GET /health.
 * - Timeout + fallback when the server is unreachable.
 */
const vscode = __importStar(require("vscode"));
const http = __importStar(require("http"));
const child_process_1 = require("child_process");
class Analyzer {
    serverProcess = null;
    baseUrl;
    constructor() {
        const config = vscode.workspace.getConfiguration("halluguard");
        const port = config.get("serverPort", 7432);
        this.baseUrl = `http://127.0.0.1:${port}`;
    }
    // ── Server lifecycle ─────────────────────────────────────────
    /** Spawn the FastAPI Python server as a child process. */
    startServer() {
        if (this.serverProcess) {
            return; // already running
        }
        const config = vscode.workspace.getConfiguration("halluguard");
        const pythonPath = config.get("pythonPath", "python");
        const port = config.get("serverPort", 7432);
        // Determine the project root (parent of vscode-extension/)
        const extRoot = vscode.extensions.getExtension("halluguard.halluguard-ai")?.extensionPath;
        // The server module lives one level up from the extension
        const cwd = extRoot
            ? vscode.Uri.joinPath(vscode.Uri.file(extRoot), "..").fsPath
            : undefined;
        console.log(`[HalluGuard] Starting server: ${pythonPath} -m uvicorn api.server:app --port ${port}`);
        this.serverProcess = (0, child_process_1.spawn)(pythonPath, ["-m", "uvicorn", "api.server:app", "--host", "127.0.0.1", "--port", String(port)], { cwd, stdio: "pipe" });
        this.serverProcess.stdout?.on("data", (data) => console.log(`[HalluGuard Server] ${data}`));
        this.serverProcess.stderr?.on("data", (data) => console.log(`[HalluGuard Server] ${data}`));
        this.serverProcess.on("exit", (code) => console.log(`[HalluGuard Server] exited with code ${code}`));
    }
    /** Kill the Python server process. */
    stopServer() {
        if (this.serverProcess) {
            this.serverProcess.kill();
            this.serverProcess = null;
            console.log("[HalluGuard] Server stopped.");
        }
    }
    // ── Analysis ─────────────────────────────────────────────────
    /**
     * Send code to the analysis server and return the report.
     * Times out after 10 seconds.
     */
    async analyze(code, language, fileName) {
        const payload = JSON.stringify({
            code,
            language,
            file_name: fileName ?? null,
        });
        return new Promise((resolve, reject) => {
            const config = vscode.workspace.getConfiguration("halluguard");
            const port = config.get("serverPort", 7432);
            const options = {
                hostname: "127.0.0.1",
                port,
                path: "/analyze",
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(payload),
                },
                timeout: 10_000,
            };
            const req = http.request(options, (res) => {
                let body = "";
                res.on("data", (chunk) => (body += chunk));
                res.on("end", () => {
                    try {
                        const report = JSON.parse(body);
                        resolve(report);
                    }
                    catch {
                        reject(new Error("Failed to parse server response."));
                    }
                });
            });
            req.on("error", (err) => reject(err));
            req.on("timeout", () => {
                req.destroy();
                reject(new Error("Analysis request timed out (10 s)."));
            });
            req.write(payload);
            req.end();
        });
    }
    // ── Health ───────────────────────────────────────────────────
    /** Check if the server is reachable. */
    async isServerHealthy() {
        return new Promise((resolve) => {
            const config = vscode.workspace.getConfiguration("halluguard");
            const port = config.get("serverPort", 7432);
            const req = http.get(`http://127.0.0.1:${port}/health`, { timeout: 3_000 }, (res) => {
                resolve(res.statusCode === 200);
            });
            req.on("error", () => resolve(false));
            req.on("timeout", () => {
                req.destroy();
                resolve(false);
            });
        });
    }
    /** Return the latest report stored by the analyzer (for hover). */
    _cachedReports = new Map();
    cacheReport(uri, report) {
        this._cachedReports.set(uri, report);
    }
    getCachedReport(uri) {
        return this._cachedReports.get(uri);
    }
}
exports.Analyzer = Analyzer;
//# sourceMappingURL=analyzer.js.map