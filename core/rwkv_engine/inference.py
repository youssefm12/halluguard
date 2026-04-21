"""
RWKV Inference Engine.

Provides ``score_code_snippet()`` which returns a hallucination
confidence score (0-100) using the locally loaded RWKV model.
Falls back to a heuristic score when no model is available.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from core.rwkv_engine import model_loader

logger = logging.getLogger(__name__)

# ── Prompt template ────────────────────────────────────────────────
PROMPT_TEMPLATE = """\
Analyze this code snippet for potential hallucinations.
For each function call or API usage, rate its validity (0-100).
Code:
{code}
Output JSON only."""


def _build_prompt(code: str) -> str:
    """Build the inference prompt for the given code snippet."""
    return PROMPT_TEMPLATE.format(code=code.strip())


def score_code_snippet(code: str) -> float:
    """
    Score a code snippet for hallucination risk using the RWKV model.

    A score of **0** means fully trusted (no hallucination suspected).
    A score of **100** means maximum hallucination risk.

    When no RWKV model is available the function returns ``-1.0`` to
    signal that the caller should rely on other scoring sources.

    Args:
        code: Raw source code string.

    Returns:
        A float in ``[0, 100]``, or ``-1.0`` if inference is unavailable.
    """
    pipeline = model_loader.get_pipeline()

    if pipeline is None:
        logger.debug("RWKV model not available; returning -1.0 sentinel.")
        return -1.0

    prompt = _build_prompt(code)
    start = time.perf_counter()

    try:
        # Use the pipeline's generate method
        result = pipeline.generate(
            prompt,
            token_count=256,
            args=_default_gen_args(),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("RWKV inference completed in %.1f ms", elapsed_ms)

        return _parse_score(result)
    except Exception as exc:
        logger.error("RWKV inference failed: %s", exc)
        return -1.0


def _default_gen_args() -> Any:
    """Return default RWKV generation arguments."""
    try:
        from rwkv.utils import PIPELINE_ARGS  # type: ignore[import-untyped]
        return PIPELINE_ARGS(
            temperature=0.2,
            top_p=0.1,
            alpha_frequency=0.25,
            alpha_presence=0.25,
        )
    except ImportError:
        return None


def _parse_score(raw_output: str) -> float:
    """
    Attempt to extract a numeric hallucination score from raw RWKV output.

    Tries JSON parsing first, then falls back to scanning for numbers.
    """
    # Try to parse as JSON
    try:
        data = json.loads(raw_output.strip())
        if isinstance(data, dict):
            # Look for common keys
            for key in ("risk_score", "score", "hallucination_score", "validity"):
                if key in data:
                    val = float(data[key])
                    # Invert "validity" (high validity = low risk)
                    if key == "validity":
                        val = 100.0 - val
                    return max(0.0, min(100.0, val))
        elif isinstance(data, (int, float)):
            return max(0.0, min(100.0, float(data)))
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fallback: look for a bare number in the output
    for token in raw_output.split():
        try:
            val = float(token.strip(",:."))
            if 0 <= val <= 100:
                return val
        except ValueError:
            continue

    logger.warning("Could not parse RWKV score from output; defaulting to 50.0")
    return 50.0
