"""
HalluGuard AI — Lightweight FastAPI Server.

Exposes the core analysis pipeline over HTTP so the VSCode extension
(and any other client) can call ``POST /analyze``.

Start with::

    uvicorn api.server:app --host 127.0.0.1 --port 7432
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.pipeline import analyze
from core.rwkv_engine import model_loader

logger = logging.getLogger(__name__)

# ── FastAPI application ────────────────────────────────────────────
app = FastAPI(
    title="HalluGuard AI",
    version="1.0.0",
    description="Detect, explain, and correct hallucinations in AI-generated code.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────
class AnalyzeRequest(BaseModel):
    """Payload sent by the VSCode extension or any client."""
    code: str = Field(..., description="Source code to analyze.")
    language: str = Field("python", description="python | javascript | typescript")
    file_name: str | None = Field(None, description="Optional file name.")


class HallucinationItem(BaseModel):
    line: int
    type: str
    token: str
    explanation: str
    suggestion: str
    severity: str


class SuggestionItem(BaseModel):
    token: str
    original_type: str | None = None
    suggestion: str | None = None
    explanation: str | None = None
    confidence: str | None = None


class AnalyzeResponse(BaseModel):
    """JSON payload returned to the client."""
    file: str
    risk_score: int
    confidence: str
    hallucinations: list[HallucinationItem]
    suggestions: list[SuggestionItem]


class HealthResponse(BaseModel):
    status: str
    rwkv_available: bool
    version: str


# ── Endpoints ──────────────────────────────────────────────────────
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_code(req: AnalyzeRequest) -> dict[str, Any]:
    """Analyze a code snippet for hallucinations."""
    report = analyze(req.code, language=req.language, file_name=req.file_name)
    return report.to_dict()


@app.get("/health", response_model=HealthResponse)
async def health_check() -> dict[str, Any]:
    """Server health and RWKV model status."""
    return {
        "status": "ok",
        "rwkv_available": model_loader.is_available(),
        "version": "1.0.0",
    }
