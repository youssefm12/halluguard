"""
Hallucination Scorer — combined scoring algorithm.

Blends three signal sources with configurable weights:
- **AST Score** : unknown functions / methods incur penalties.
- **Knowledge Score** : PyPI / npm verification failures.
- **RWKV Score** : local model confidence (when available).

Outputs a ``HallucinationReport`` dataclass with severity thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Severity thresholds ────────────────────────────────────────────
_THRESHOLDS: dict[str, tuple[int, int]] = {
    "LOW":      (1, 25),
    "MEDIUM":   (26, 50),
    "HIGH":     (51, 75),
    "CRITICAL": (76, 100),
}


# ── Configurable weight defaults ────────────────────────────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "knowledge": 0.50,
    "ast":       0.30,
    "rwkv":      0.20,
}


@dataclass
class HallucinationIssue:
    """A single detected hallucination."""
    line: int
    issue_type: str
    token: str
    explanation: str
    suggestion: str
    severity: str


@dataclass
class HallucinationReport:
    """Full analysis report returned by the scorer."""
    file: str = ""
    risk_score: int = 0
    confidence: str = "HIGH"
    hallucinations: list[HallucinationIssue] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)

    # Internal scores kept for debugging / benchmarks
    _knowledge_raw: float = 0.0
    _ast_raw: float = 0.0
    _rwkv_raw: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the universal JSON format."""
        return {
            "file": self.file,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "hallucinations": [
                {
                    "line": h.line,
                    "type": h.issue_type,
                    "token": h.token,
                    "explanation": h.explanation,
                    "suggestion": h.suggestion,
                    "severity": h.severity,
                }
                for h in self.hallucinations
            ],
            "suggestions": self.suggestions,
        }


def _severity_label(score: int) -> str:
    """Map a 0-100 score to a severity string."""
    for label, (lo, hi) in _THRESHOLDS.items():
        if lo <= score <= hi:
            return label
    return "CRITICAL" if score > 0 else "LOW"


def compute(
    tokens: dict[str, Any],
    knowledge: dict[str, Any],
    rwkv_score: float | None = None,
    weights: dict[str, float] | None = None,
) -> HallucinationReport:
    """
    Compute a hallucination report by blending multiple signal sources.

    Args:
        tokens:     Output of the AST parser (``extract()``).
        knowledge:  Output of the knowledge verifier (``check()``).
        rwkv_score: RWKV confidence (0-100) or ``-1`` / ``None``
                    when unavailable.
        weights:    Optional weight overrides (keys: knowledge, ast, rwkv).

    Returns:
        A fully populated ``HallucinationReport``.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    issues: list[HallucinationIssue] = []

    # ── Knowledge penalties ────────────────────────────────────
    knowledge_penalty = 0.0
    verified = knowledge.get("verified_imports", {})
    total_imports = max(len(verified), 1)

    for pkg_name, info in verified.items():
        if not info.get("exists", False):
            knowledge_penalty += 100.0 / total_imports
            issues.append(HallucinationIssue(
                line=0,
                issue_type="unknown_import",
                token=pkg_name,
                explanation=f"Package '{pkg_name}' was not found on the package registry.",
                suggestion="Verify package spelling or find a valid alternative.",
                severity="HIGH",
            ))

    knowledge_score = min(100.0, knowledge_penalty)

    # ── AST penalties ──────────────────────────────────────────
    # Penalize unresolved function calls that look suspicious
    # (e.g., non-builtin, non-imported function identifiers)
    ast_penalty = 0.0
    imported_names: set[str] = set()
    for fi in tokens.get("from_imports", []):
        imported_names.update(fi.get("names", []))

    # Known Python builtins we should never flag
    _builtins: frozenset[str] = frozenset({
        "print", "len", "range", "type", "int", "str", "float", "list",
        "dict", "set", "tuple", "bool", "input", "open", "super", "isinstance",
        "issubclass", "hasattr", "getattr", "setattr", "delattr", "enumerate",
        "zip", "map", "filter", "sorted", "reversed", "min", "max", "sum",
        "abs", "round", "any", "all", "next", "iter", "id", "repr", "hash",
        "staticmethod", "classmethod", "property", "vars", "dir", "globals",
        "locals", "exec", "eval", "compile", "breakpoint", "exit", "quit",
    })

    function_calls = tokens.get("function_calls", [])
    for fn in function_calls:
        if fn not in _builtins and fn not in imported_names:
            ast_penalty += 15.0
            issues.append(HallucinationIssue(
                line=0,
                issue_type="unknown_function",
                token=fn,
                explanation=f"Function '{fn}()' is not a known builtin or imported name.",
                suggestion=f"Check if '{fn}' should be imported or if it exists.",
                severity="MEDIUM",
            ))

    ast_score = min(100.0, ast_penalty)

    # ── RWKV integration ──────────────────────────────────────
    rwkv_effective = 0.0
    rwkv_weight_active = w["rwkv"]
    if rwkv_score is not None and rwkv_score >= 0:
        rwkv_effective = rwkv_score
    else:
        # Redistribute RWKV weight equally among the other two sources
        rwkv_weight_active = 0.0
        remaining = w["rwkv"]
        w["knowledge"] += remaining / 2
        w["ast"] += remaining / 2

    # ── Weighted blend ────────────────────────────────────────
    raw = (
        knowledge_score * w["knowledge"]
        + ast_score * w["ast"]
        + rwkv_effective * rwkv_weight_active
    )
    risk_score = int(max(0, min(100, round(raw))))

    severity = _severity_label(risk_score)
    confidence = "HIGH" if risk_score >= 70 or risk_score == 0 else "MEDIUM"

    report = HallucinationReport(
        risk_score=risk_score,
        confidence=confidence,
        hallucinations=issues,
        _knowledge_raw=knowledge_score,
        _ast_raw=ast_score,
        _rwkv_raw=rwkv_effective,
    )
    return report
