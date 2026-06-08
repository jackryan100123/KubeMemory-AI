"""
Redis heartbeat for the K8s watcher process.
Key: watcher:heartbeat:<cluster_id> with 45s TTL, refreshed every 30s.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Callable

import redis

logger = logging.getLogger(__name__)

HEARTBEAT_TTL_SECONDS = 45
HEARTBEAT_INTERVAL_SECONDS = 30


def heartbeat_key(cluster_id: int | None) -> str:
    """Redis key for a cluster watcher heartbeat."""
    suffix = str(cluster_id) if cluster_id is not None else "default"
    return f"watcher:heartbeat:{suffix}"


def _redis_client() -> redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True)


def write_heartbeat(cluster_id: int | None) -> None:
    """Write a single heartbeat timestamp with TTL."""
    try:
        client = _redis_client()
        client.setex(heartbeat_key(cluster_id), HEARTBEAT_TTL_SECONDS, str(time.time()))
    except Exception as exc:
        logger.warning("Failed to write watcher heartbeat: %s", exc)


def get_heartbeat_age_seconds(cluster_id: int | None) -> float | None:
    """Return seconds since last heartbeat, or None if key missing."""
    try:
        client = _redis_client()
        raw = client.get(heartbeat_key(cluster_id))
        if not raw:
            return None
        return max(0.0, time.time() - float(raw))
    except Exception as exc:
        logger.warning("Failed to read watcher heartbeat: %s", exc)
        return None


def start_heartbeat_thread(
    cluster_id: int | None,
    should_stop: Callable[[], bool],
) -> threading.Thread:
    """Background thread that refreshes heartbeat until should_stop returns True."""

    def _loop() -> None:
        while not should_stop():
            write_heartbeat(cluster_id)
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)

    thread = threading.Thread(target=_loop, name="watcher-heartbeat", daemon=True)
    thread.start()
    return thread
