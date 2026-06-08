"""
Ollama model readiness checks and Redis status keys.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request

import redis

logger = logging.getLogger(__name__)

OLLAMA_READY_KEY = "ollama:ready"


def _redis_client() -> redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True)


def list_ollama_models(base_url: str | None = None) -> list[str]:
    """Return model names from Ollama /api/tags."""
    base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip(
        "/"
    )
    try:
        req = urllib.request.Request(
            f"{base_url}/api/tags",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception as exc:
        logger.warning("Could not list Ollama models: %s", exc)
        return []


def _model_available(models: list[str], expected: str) -> bool:
    expected = expected.strip()
    if not expected:
        return False
    for name in models:
        if name == expected or name.startswith(expected + ":") or expected.startswith(name + ":"):
            return True
    return False


def verify_ollama_models() -> bool:
    """
    Check OLLAMA_CHAT_MODEL and OLLAMA_EMBED_MODEL exist on Ollama server.
    Sets Redis key ollama:ready to true/false. Logs critical warning if missing.
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    chat_model = os.environ.get("OLLAMA_CHAT_MODEL", "qwen2.5:0.5b")
    embed_model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    models = list_ollama_models(base_url)
    chat_ok = _model_available(models, chat_model)
    embed_ok = _model_available(models, embed_model)
    ready = chat_ok and embed_ok
    try:
        client = _redis_client()
        client.set(OLLAMA_READY_KEY, "true" if ready else "false", ex=300)
    except Exception as exc:
        logger.warning("Could not set ollama:ready in Redis: %s", exc)
    if not ready:
        logger.critical(
            "Ollama models missing: chat=%s (%s) embed=%s (%s). Available: %s",
            chat_model,
            chat_ok,
            embed_model,
            embed_ok,
            models,
        )
    return ready


def get_ollama_ready_from_redis() -> bool | None:
    """Read cached ollama:ready flag from Redis."""
    try:
        val = _redis_client().get(OLLAMA_READY_KEY)
        if val is None:
            return None
        return val.lower() == "true"
    except Exception:
        return None
