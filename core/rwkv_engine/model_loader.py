"""
RWKV Model Loader.

Handles lazy loading of the RWKV model with configurable model path
(via environment variable or explicit argument), and graceful fallback
when the model file is absent.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Environment variable for model path ────────────────────────────
_ENV_MODEL_PATH = "HALLUGUARD_RWKV_MODEL"
_ENV_TOKENIZER_PATH = "HALLUGUARD_RWKV_TOKENIZER"

# ── Global singleton ──────────────────────────────────────────────
_model: Any | None = None
_pipeline: Any | None = None
_loaded: bool = False


def _default_model_path() -> Path:
    """Return the default model file path."""
    return Path(os.environ.get(_ENV_MODEL_PATH, "models/rwkv-4-1.5b.pth"))


def _default_tokenizer_path() -> str:
    """Return the default tokenizer path / name."""
    return os.environ.get(_ENV_TOKENIZER_PATH, "20B_tokenizer.json")


def is_available() -> bool:
    """Return ``True`` if a model file exists at the configured path."""
    return _default_model_path().is_file()


def load(model_path: str | Path | None = None, strategy: str = "cpu fp32") -> bool:
    """
    Lazily load the RWKV model into memory.

    Args:
        model_path: Explicit path to the ``.pth`` file.  Defaults to
                     the ``HALLUGUARD_RWKV_MODEL`` env-var or
                     ``models/rwkv-4-1.5b.pth``.
        strategy:    RWKV inference strategy (e.g. ``"cpu fp32"``).

    Returns:
        ``True`` if the model was loaded successfully, ``False`` otherwise.
    """
    global _model, _pipeline, _loaded

    if _loaded and _model is not None:
        return True

    path = Path(model_path) if model_path else _default_model_path()

    if not path.is_file():
        logger.warning(
            "RWKV model not found at '%s'. "
            "RWKV scoring will be disabled (fallback to heuristics only).",
            path,
        )
        _loaded = True  # mark as "attempted"
        return False

    try:
        from rwkv.model import RWKV  # type: ignore[import-untyped]
        from rwkv.utils import PIPELINE  # type: ignore[import-untyped]

        logger.info("Loading RWKV model from '%s' with strategy '%s'...", path, strategy)
        _model = RWKV(model=str(path), strategy=strategy)
        _pipeline = PIPELINE(_model, _default_tokenizer_path())
        _loaded = True
        logger.info("RWKV model loaded successfully.")
        return True
    except ImportError:
        logger.warning(
            "rwkv package is not installed. "
            "Install with: pip install rwkv"
        )
        _loaded = True
        return False
    except Exception as exc:
        logger.error("Failed to load RWKV model: %s", exc)
        _loaded = True
        return False


def get_model() -> Any | None:
    """Return the loaded RWKV model instance, or ``None``."""
    if not _loaded:
        load()
    return _model


def get_pipeline() -> Any | None:
    """Return the loaded RWKV pipeline instance, or ``None``."""
    if not _loaded:
        load()
    return _pipeline


def reset() -> None:
    """Unload the model and reset state (useful for testing)."""
    global _model, _pipeline, _loaded
    _model = None
    _pipeline = None
    _loaded = False
