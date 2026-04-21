"""
npm Registry Knowledge Verifier.

For each JavaScript/TypeScript import or require(), verifies existence
against the npm registry API.
Implements:
- TTL-based in-memory cache (default 24 h)
- Node.js built-in detection
"""
from __future__ import annotations

import time
import requests
from dataclasses import dataclass, field
from typing import Any

# ── Default TTL for cache entries (seconds) ────────────────────────
_DEFAULT_TTL: int = 86_400  # 24 hours


@dataclass
class _CacheEntry:
    """Single cache record for an npm lookup."""
    exists: bool
    latest_version: str | None = None
    timestamp: float = field(default_factory=time.time)

    def is_expired(self, ttl: int = _DEFAULT_TTL) -> bool:
        return (time.time() - self.timestamp) > ttl


# ── Module-level cache ─────────────────────────────────────────────
_cache: dict[str, _CacheEntry] = {}


# ── Node.js built-in modules ──────────────────────────────────────
_NODE_BUILTINS: frozenset[str] = frozenset({
    "assert", "buffer", "child_process", "cluster", "console", "constants",
    "crypto", "dgram", "dns", "domain", "events", "fs", "http", "http2",
    "https", "module", "net", "os", "path", "perf_hooks", "process",
    "punycode", "querystring", "readline", "repl", "stream", "string_decoder",
    "sys", "timers", "tls", "tty", "url", "util", "v8", "vm", "wasi",
    "worker_threads", "zlib",
})


def is_node_builtin(module_name: str) -> bool:
    """Return ``True`` if *module_name* is a Node.js built-in module."""
    # Strip optional node: prefix
    clean = module_name.removeprefix("node:")
    return clean in _NODE_BUILTINS


def _extract_package_name(specifier: str) -> str:
    """
    Normalize an npm specifier to its top-level package name.

    - ``@scope/pkg/sub`` -> ``@scope/pkg``
    - ``lodash/fp`` -> ``lodash``
    - Relative paths (``./``, ``../``) are returned as-is.
    """
    specifier = specifier.strip("'\"")
    if specifier.startswith(".") or specifier.startswith("/"):
        return specifier  # local import, skip
    if specifier.startswith("@"):
        parts = specifier.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else specifier
    return specifier.split("/")[0]


# ── Single-package lookup ──────────────────────────────────────────
def check_package(module_specifier: str) -> dict[str, Any]:
    """
    Verify whether an npm package exists on the registry.

    Args:
        module_specifier: The raw import/require string.

    Returns:
        A dict with keys ``package``, ``exists``, ``type``,
        and optionally ``latest_version`` or ``error``.
    """
    pkg = _extract_package_name(module_specifier)
    result: dict[str, Any] = {"package": pkg, "exists": False}

    # Skip relative imports
    if pkg.startswith(".") or pkg.startswith("/"):
        result.update(exists=True, type="local")
        return result

    # Node built-in
    if is_node_builtin(pkg):
        result.update(exists=True, type="node_builtin")
        return result

    # TTL cache hit
    cached = _cache.get(pkg)
    if cached is not None and not cached.is_expired():
        result.update(
            exists=cached.exists,
            type="npm_cached",
            latest_version=cached.latest_version,
        )
        return result

    # Live npm registry call
    url = f"https://registry.npmjs.org/{pkg}"
    try:
        resp = requests.get(url, timeout=5)
        exists = resp.status_code == 200
        latest_version: str | None = None
        if exists:
            data = resp.json()
            dist_tags = data.get("dist-tags", {})
            latest_version = dist_tags.get("latest")

        _cache[pkg] = _CacheEntry(exists=exists, latest_version=latest_version)
        result.update(exists=exists, type="npm_api", latest_version=latest_version)
    except requests.RequestException as exc:
        result.update(exists=False, type="error", error=str(exc))

    return result


# ── Batch check (called by the pipeline) ───────────────────────────
def check(tokens: dict[str, Any]) -> dict[str, Any]:
    """
    Verify all imports / require() calls found in *tokens* against npm.

    Args:
        tokens: Output of ``js_parser.extract()``.

    Returns:
        ``{"verified_imports": {name: check_result, ...}}``
    """
    verified: dict[str, dict[str, Any]] = {}

    all_modules: list[str] = []
    all_modules.extend(tokens.get("imports", []))
    all_modules.extend(tokens.get("require_calls", []))

    for mod in all_modules:
        pkg = _extract_package_name(mod)
        if pkg not in verified:
            verified[pkg] = check_package(mod)

    return {"verified_imports": verified}
