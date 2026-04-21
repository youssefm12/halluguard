"""
Correction / Suggestion Engine.

For each detected hallucination, generates actionable suggestions:
- Unknown import   -> fuzzy-match the closest real package.
- Unknown function -> suggest an equivalent from a known library.
- Deprecated API   -> propose the modern replacement.

Includes a static dictionary of common hallucination patterns
observed in LLM-generated code.
"""
from __future__ import annotations

import difflib
from typing import Any


# ── Common hallucination patterns dictionary ──────────────────────
# Maps frequently hallucinated tokens to their correct equivalents.
COMMON_PATTERNS: dict[str, dict[str, str]] = {
    # Fake packages -> real ones
    "requests2":         {"replacement": "requests",      "note": "No 'requests2' package; use 'requests'."},
    "beautifulsoup":     {"replacement": "beautifulsoup4", "note": "Package is named 'beautifulsoup4' on PyPI."},
    "sklearn":           {"replacement": "scikit-learn",  "note": "Install as 'scikit-learn', import as 'sklearn'."},
    "cv2":               {"replacement": "opencv-python", "note": "Install as 'opencv-python', import as 'cv2'."},
    "yaml":              {"replacement": "pyyaml",        "note": "Install as 'pyyaml', import as 'yaml'."},
    "PIL":               {"replacement": "Pillow",        "note": "Install as 'Pillow', import as 'PIL'."},
    "dotenv":            {"replacement": "python-dotenv", "note": "Install as 'python-dotenv', import as 'dotenv'."},
    # Fake functions -> real equivalents
    "fetchUserData":     {"replacement": "requests.get(url)", "note": "Common LLM hallucination; use requests.get()."},
    "getData":           {"replacement": "requests.get(url)", "note": "Generic hallucinated name; specify real API call."},
    "sendRequest":       {"replacement": "requests.post(url, data=...)", "note": "Use requests.post() explicitly."},
    "connectDB":         {"replacement": "sqlalchemy.create_engine(url)", "note": "Use SQLAlchemy or a real DB driver."},
    "fetchFromAPI":      {"replacement": "requests.get(url)", "note": "Non-existent convenience function."},
    # npm equivalents
    "node-fetch":        {"replacement": "node-fetch",    "note": "Valid package (>=3.x is ESM-only)."},
    "axios":             {"replacement": "axios",         "note": "Valid, popular HTTP client."},
}

# Known valid packages for fuzzy matching
_KNOWN_PYPI: list[str] = [
    "requests", "flask", "django", "fastapi", "numpy", "pandas",
    "scipy", "matplotlib", "torch", "tensorflow", "scikit-learn",
    "beautifulsoup4", "lxml", "aiohttp", "httpx", "pydantic",
    "sqlalchemy", "celery", "redis", "pymongo", "psycopg2",
    "pillow", "opencv-python", "pytest", "click", "typer",
    "pyyaml", "python-dotenv", "uvicorn", "gunicorn",
]

_KNOWN_NPM: list[str] = [
    "express", "axios", "lodash", "react", "next", "typescript",
    "webpack", "vite", "eslint", "prettier", "jest", "mocha",
    "mongoose", "sequelize", "prisma", "socket.io", "cors",
    "dotenv", "jsonwebtoken", "bcrypt", "nodemon", "chalk",
]


def _fuzzy_match(name: str, candidates: list[str], cutoff: float = 0.5) -> str | None:
    """Return the closest match from *candidates*, or ``None``."""
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def suggest(report: Any, language: str = "python") -> list[dict[str, Any]]:
    """
    Generate correction suggestions for each hallucination in *report*.

    Args:
        report: A ``HallucinationReport`` instance (from the scorer).
        language: ``"python"`` or ``"javascript"``/``"typescript"``.

    Returns:
        A list of suggestion dicts, each containing:
        ``token``, ``suggestion``, ``explanation``, ``confidence``.
    """
    suggestions: list[dict[str, Any]] = []
    candidates = _KNOWN_PYPI if language == "python" else _KNOWN_NPM

    for issue in report.hallucinations:
        token = issue.token
        suggestion: dict[str, Any] = {
            "token": token,
            "original_type": issue.issue_type,
        }

        # 1. Check static pattern dictionary
        if token in COMMON_PATTERNS:
            pattern = COMMON_PATTERNS[token]
            suggestion["suggestion"] = pattern["replacement"]
            suggestion["explanation"] = pattern["note"]
            suggestion["confidence"] = "HIGH"
            suggestions.append(suggestion)
            continue

        # 2. Fuzzy match against known packages
        if issue.issue_type == "unknown_import":
            match = _fuzzy_match(token, candidates)
            if match:
                suggestion["suggestion"] = match
                suggestion["explanation"] = (
                    f"Did you mean '{match}'? "
                    f"'{token}' is not a known package."
                )
                suggestion["confidence"] = "MEDIUM"
            else:
                suggestion["suggestion"] = None
                suggestion["explanation"] = (
                    f"No close match found for '{token}'. "
                    "Verify the package name manually."
                )
                suggestion["confidence"] = "LOW"

        # 3. Unknown function suggestions
        elif issue.issue_type == "unknown_function":
            match = _fuzzy_match(token, list(COMMON_PATTERNS.keys()))
            if match and match in COMMON_PATTERNS:
                pattern = COMMON_PATTERNS[match]
                suggestion["suggestion"] = pattern["replacement"]
                suggestion["explanation"] = pattern["note"]
                suggestion["confidence"] = "MEDIUM"
            else:
                suggestion["suggestion"] = None
                suggestion["explanation"] = (
                    f"Function '{token}()' not recognized. "
                    "Ensure it is imported or defined locally."
                )
                suggestion["confidence"] = "LOW"

        else:
            suggestion["suggestion"] = None
            suggestion["explanation"] = "No automatic suggestion available."
            suggestion["confidence"] = "LOW"

        suggestions.append(suggestion)

    return suggestions
