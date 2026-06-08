"""
Ollama model routing: fast vs reasoning models by task type.
"""
from __future__ import annotations

import os

from .ollama_models import get_working_chat_model


def get_fast_model_name() -> str:
    """Small/fast model for suggestions, classification, light chat."""
    return os.environ.get("OLLAMA_FAST_MODEL", "qwen2.5:0.5b").strip()


def get_reasoning_model_name() -> str:
    """Larger model for analysis, runbooks, risk reasoning."""
    return os.environ.get("OLLAMA_REASONING_MODEL", "mistral:7b").strip()


def resolve_fast_model(base_url: str | None = None) -> str | None:
    """Return a working fast model name on the Ollama server."""
    return get_working_chat_model(
        base_url=base_url,
        preferred=get_fast_model_name(),
    )


def resolve_reasoning_model(base_url: str | None = None) -> str | None:
    """Return a working reasoning model name on the Ollama server."""
    return get_working_chat_model(
        base_url=base_url,
        preferred=get_reasoning_model_name(),
    )
