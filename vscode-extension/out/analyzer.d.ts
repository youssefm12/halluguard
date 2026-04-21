/** Shape of a single hallucination returned by the server. */
export interface HallucinationItem {
    line: number;
    type: string;
    token: string;
    explanation: string;
    suggestion: string;
    severity: string;
}
/** Shape of a correction suggestion. */
export interface SuggestionItem {
    token: string;
    original_type?: string;
    suggestion?: string;
    explanation?: string;
    confidence?: string;
}
/** Full analysis report returned by the server. */
export interface AnalysisReport {
    file: string;
    risk_score: number;
    confidence: string;
    hallucinations: HallucinationItem[];
    suggestions: SuggestionItem[];
}
export declare class Analyzer {
    private serverProcess;
    private baseUrl;
    constructor();
    /** Spawn the FastAPI Python server as a child process. */
    startServer(): void;
    /** Kill the Python server process. */
    stopServer(): void;
    /**
     * Send code to the analysis server and return the report.
     * Times out after 10 seconds.
     */
    analyze(code: string, language: string, fileName?: string): Promise<AnalysisReport>;
    /** Check if the server is reachable. */
    isServerHealthy(): Promise<boolean>;
    /** Return the latest report stored by the analyzer (for hover). */
    private _cachedReports;
    cacheReport(uri: string, report: AnalysisReport): void;
    getCachedReport(uri: string): AnalysisReport | undefined;
}
//# sourceMappingURL=analyzer.d.ts.map