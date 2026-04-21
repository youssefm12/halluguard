"""
PyPI Knowledge Verifier.

For each Python import, verifies existence against the PyPI JSON API.
Implements:
- Stdlib detection (never queries PyPI for ``os``, ``sys``, etc.)
- TTL-based in-memory cache (default 24 h)
- Version validation when available
"""
from __future__ import annotations

import sys
import time
import requests
from dataclasses import dataclass, field
from typing import Any

# ── Default TTL for cache entries (seconds) ────────────────────────
_DEFAULT_TTL: int = 86_400  # 24 hours


@dataclass
class _CacheEntry:
    """Single cache record for a PyPI lookup."""
    exists: bool
    latest_version: str | None = None
    timestamp: float = field(default_factory=time.time)

    def is_expired(self, ttl: int = _DEFAULT_TTL) -> bool:
        return (time.time() - self.timestamp) > ttl


# ── Module-level cache ─────────────────────────────────────────────
_cache: dict[str, _CacheEntry] = {}


# ── Stdlib detection ───────────────────────────────────────────────
def _stdlib_modules() -> frozenset[str]:
    """Return a frozen set of all known stdlib module names."""
    if hasattr(sys, "stdlib_module_names"):
        return frozenset(sys.stdlib_module_names)
    # Fallback for Python < 3.10
    return frozenset(sys.builtin_module_names)

_STDLIB: frozenset[str] = _stdlib_modules()


def is_standard_library(package_name: str) -> bool:
    """Return ``True`` if *package_name* is a Python standard library module."""
    return package_name in _STDLIB


# ── Single-package lookup ──────────────────────────────────────────
def check_package(package_name: str) -> dict[str, Any]:
    """
    Verify whether a Python package exists on PyPI.

    Args:
        package_name: Top-level module / package name.

    Returns:
        A dict with keys ``package``, ``exists``, ``type``,
        and optionally ``latest_version`` or ``error``.
    """
    result: dict[str, Any] = {"package": package_name, "exists": False}

    # 1. Standard library — always valid
    if is_standard_library(package_name):
        result.update(exists=True, type="stdlib")
        return result

    # 2. TTL cache hit
    cached = _cache.get(package_name)
    if cached is not None and not cached.is_expired():
        result.update(
            exists=cached.exists,
            type="pypi_cached",
            latest_version=cached.latest_version,
        )
        return result

    # 3. Live PyPI API call
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        resp = requests.get(url, timeout=5)
        exists = resp.status_code == 200
        latest_version: str | None = None
        if exists:
            data = resp.json()
            latest_version = data.get("info", {}).get("version")

        _cache[package_name] = _CacheEntry(
            exists=exists, latest_version=latest_version
        )
        result.update(exists=exists, type="pypi_api", latest_version=latest_version)
    except requests.RequestException as exc:
        result.update(exists=False, type="error", error=str(exc))

    return result


# ── Batch check (called by the pipeline) ───────────────────────────
def check(tokens: dict[str, Any]) -> dict[str, Any]:
    """
    Verify all imports found in *tokens* against PyPI.

    Args:
        tokens: Output of ``python_parser.extract()``.

    Returns:
        ``{"verified_imports": {name: check_result, ...}}``
    """
    verified: dict[str, dict[str, Any]] = {}
    for imp in tokens.get("imports", []):
        verified[imp] = check_package(imp)
    return {"verified_imports": verified}
