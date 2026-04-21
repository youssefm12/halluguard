"""
Hybrid Routing — RWKV + Cloud LLM.

Decides whether local RWKV inference is sufficient or a cloud LLM
should be consulted for deeper verification.

Routing logic:
- RWKV score < 60 : escalate to cloud LLM for second opinion.
- RWKV score >= 60 : local response is confident enough.
- RWKV unavailable : fall back directly to cloud (if configured).

Cloud LLM support is **optional** and gated by an API key
(``HALLUGUARD_CLOUD_API_KEY`` env-var).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from core.rwkv_engine import inference as rwkv_inference

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
_LOCAL_THRESHOLD: float = 60.0
_ENV_CLOUD_KEY = "HALLUGUARD_CLOUD_API_KEY"
_ENV_CLOUD_URL = "HALLUGUARD_CLOUD_URL"

# ── Routing decision log (kept in memory for benchmarks) ──────────
_routing_log: list[dict[str, Any]] = []


@dataclass
class RoutingDecision:
    """Immutable record of a single routing decision."""
    rwkv_score: float
    route: str  # "local", "cloud", "cloud_fallback", "heuristic_only"
    cloud_score: float | None = None
    final_score: float = 0.0
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


def _cloud_available() -> bool:
    """Return True if a cloud LLM API key is configured."""
    return bool(os.environ.get(_ENV_CLOUD_KEY))


def _call_cloud_llm(code: str) -> float:
    """
    Placeholder for cloud LLM inference.

    In production this would call an external API (e.g., OpenAI,
    Anthropic, or Groq) with the same prompt template used by
    the RWKV engine. For now it returns ``-1.0``.
    """
    api_key = os.environ.get(_ENV_CLOUD_KEY)
    cloud_url = os.environ.get(_ENV_CLOUD_URL, "https://api.openai.com/v1/chat/completions")

    if not api_key:
        return -1.0

    # ── Future implementation ──────────────────────────────────
    # import requests
    # resp = requests.post(cloud_url, headers={...}, json={...})
    # return _parse(resp)
    logger.info("Cloud LLM call stub invoked (key present, endpoint: %s)", cloud_url)
    return -1.0


def score(code: str) -> RoutingDecision:
    """
    Score a code snippet using the hybrid routing strategy.

    Args:
        code: Raw source code string.

    Returns:
        A ``RoutingDecision`` recording the scores and route taken.
    """
    start = time.perf_counter()

    # ── Step 1: local RWKV inference ───────────────────────────
    rwkv_score = rwkv_inference.score_code_snippet(code)

    decision: RoutingDecision

    if rwkv_score < 0:
        # RWKV not available
        if _cloud_available():
            cloud_score = _call_cloud_llm(code)
            final = cloud_score if cloud_score >= 0 else 0.0
            decision = RoutingDecision(
                rwkv_score=rwkv_score,
                route="cloud_fallback",
                cloud_score=cloud_score,
                final_score=final,
            )
        else:
            decision = RoutingDecision(
                rwkv_score=rwkv_score,
                route="heuristic_only",
                final_score=0.0,
            )
    elif rwkv_score >= _LOCAL_THRESHOLD:
        # High local confidence — no need for cloud
        decision = RoutingDecision(
            rwkv_score=rwkv_score,
            route="local",
            final_score=rwkv_score,
        )
    else:
        # Low local confidence — escalate to cloud if possible
        if _cloud_available():
            cloud_score = _call_cloud_llm(code)
            final = cloud_score if cloud_score >= 0 else rwkv_score
            decision = RoutingDecision(
                rwkv_score=rwkv_score,
                route="cloud",
                cloud_score=cloud_score,
                final_score=final,
            )
        else:
            decision = RoutingDecision(
                rwkv_score=rwkv_score,
                route="local",
                final_score=rwkv_score,
            )

    decision.latency_ms = (time.perf_counter() - start) * 1000

    # Log the decision for later benchmarking
    _routing_log.append({
        "rwkv_score": decision.rwkv_score,
        "route": decision.route,
        "cloud_score": decision.cloud_score,
        "final_score": decision.final_score,
        "latency_ms": round(decision.latency_ms, 2),
        "timestamp": decision.timestamp,
    })
    logger.info(
        "Routing decision: route=%s  rwkv=%.1f  final=%.1f  (%.1f ms)",
        decision.route, decision.rwkv_score, decision.final_score, decision.latency_ms,
    )

    return decision


def get_routing_log() -> list[dict[str, Any]]:
    """Return a copy of the accumulated routing decision log."""
    return list(_routing_log)


def clear_routing_log() -> None:
    """Clear the routing decision log."""
    _routing_log.clear()
