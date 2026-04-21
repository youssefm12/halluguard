"""
HalluGuard AI — End-to-End Analysis Pipeline.

This is the single entry point for the entire core engine.
It orchestrates:

1. AST parsing  (Python or JS/TS)
2. Knowledge verification  (PyPI or npm)
3. RWKV hybrid scoring  (local model + optional cloud)
4. Hallucination scoring  (weighted blend)
5. Correction suggestions

Usage::

    from core.pipeline import analyze
    report = analyze(code, language="python")
    print(report.to_dict())
"""
from __future__ import annotations

from typing import Any

from core.parser import python_parser
from core.parser import js_parser
from core.verifier import pypi_verifier
from core.verifier import npm_verifier
from core.scorer.hallucination_scorer import HallucinationReport, compute
from core.corrector import suggestion_engine
from core.rwkv_engine import router as rwkv_router


# ── Supported languages ───────────────────────────────────────────
_PYTHON_ALIASES = frozenset({"python", "py"})
_JS_ALIASES = frozenset({"javascript", "js"})
_TS_ALIASES = frozenset({"typescript", "ts"})


def analyze(
    code: str,
    language: str = "python",
    file_name: str | None = None,
    weights: dict[str, float] | None = None,
) -> HallucinationReport:
    """
    Run the full hallucination detection pipeline on *code*.

    Args:
        code:      Source code string to analyse.
        language:  ``"python"``, ``"javascript"`` or ``"typescript"``.
        file_name: Optional file name attached to the report.
        weights:   Optional weight overrides for the scorer
                   (keys: ``knowledge``, ``ast``, ``rwkv``).

    Returns:
        A fully populated ``HallucinationReport``.
    """
    lang = language.lower()

    # ── 1. Parse ───────────────────────────────────────────────
    if lang in _PYTHON_ALIASES:
        tokens = python_parser.extract(code, "python")
    elif lang in _JS_ALIASES:
        tokens = js_parser.extract(code, "javascript")
    elif lang in _TS_ALIASES:
        tokens = js_parser.extract(code, "typescript")
    else:
        raise ValueError(
            f"Unsupported language '{language}'. "
            "Choose from: python, javascript, typescript."
        )

    # ── 2. Verify knowledge ────────────────────────────────────
    if lang in _PYTHON_ALIASES:
        knowledge = pypi_verifier.check(tokens)
    else:
        knowledge = npm_verifier.check(tokens)

    # ── 3. RWKV hybrid scoring ─────────────────────────────────
    routing = rwkv_router.score(code)
    rwkv_score: float | None = None
    if routing.final_score > 0 or routing.route != "heuristic_only":
        rwkv_score = routing.final_score

    # ── 4. Compute risk score ──────────────────────────────────
    report = compute(tokens, knowledge, rwkv_score=rwkv_score, weights=weights)

    # ── 5. Generate corrections ────────────────────────────────
    suggestions = suggestion_engine.suggest(report, language=lang)
    report.suggestions = suggestions

    # ── 6. Attach file metadata ────────────────────────────────
    if file_name:
        report.file = file_name
    else:
        ext_map = {"python": "py", "py": "py", "javascript": "js",
                   "js": "js", "typescript": "ts", "ts": "ts"}
        report.file = f"snippet.{ext_map.get(lang, 'txt')}"

    return report
