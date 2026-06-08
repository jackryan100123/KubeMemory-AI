"""
Ollama model discovery and fallback selection for chat workloads.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)

OLLAMA_CHAT_FALLBACKS = ("qwen2.5:0.5b", "phi3:mini", "llama3.2:3b", "llama3.2:1b", "mistral:7b")


def _get_available_ollama_models(base_url: str) -> list[str]:
    """Return list of model names available on the Ollama server."""
    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/tags",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception as e:
        logger.warning("Could not list Ollama models at %s: %s", base_url, e)
        return []


def get_working_chat_model(
    base_url: str | None = None,
    preferred: str | None = None,
) -> str | None:
    """
    Return a chat model name that exists on the Ollama server.
    Uses /api/tags: preferred first if available, then fallbacks, then any listed model.
    """
    base_url = base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    preferred = (preferred or os.environ.get("OLLAMA_CHAT_MODEL") or "mistral:7b").strip()
    available = _get_available_ollama_models(base_url)
    if not available:
        logger.warning(
            "No models listed at Ollama %s; ensure Ollama is running and models are pulled.",
            base_url,
        )
        return None

    def name_matches(a: str, b: str) -> bool:
        return a == b or a.startswith(b + ":") or b.startswith(a + ":")

    if any(name_matches(m, preferred) for m in available):
        return preferred
    for fallback in OLLAMA_CHAT_FALLBACKS:
        if any(name_matches(m, fallback) for m in available):
            logger.info(
                "Using fallback Ollama chat model: %s (preferred %s not available)",
                fallback,
                preferred,
            )
            return fallback
    chat_like = [m for m in available if "embed" not in m.lower()]
    first = chat_like[0] if chat_like else available[0]
    logger.info(
        "Using first available Ollama chat model: %s (preferred %s not in list)",
        first,
        preferred,
    )
    return first
