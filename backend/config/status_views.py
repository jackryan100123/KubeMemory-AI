"""
Aggregated system status for the /status UI page.
"""
from __future__ import annotations

import os

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from apps.agents.ollama_health import get_ollama_ready_from_redis, verify_ollama_models
from apps.clusters.models import ClusterConnection
from apps.clusters.watcher_manager import watcher_status
from apps.monitoring.models import TaskLog
from apps.watcher.heartbeat import get_heartbeat_age_seconds


@api_view(["GET"])
def system_status(request: Request) -> Response:
    """
    Combined health: Ollama, Chroma, watcher heartbeats, recent task failures.
    """
    ollama_ready = get_ollama_ready_from_redis()
    if ollama_ready is None:
        ollama_ready = verify_ollama_models()

    chroma_count: int | None = None
    try:
        import chromadb

        persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "/app/chroma_data")
        collection_name = os.environ.get("CHROMA_COLLECTION_NAME", "kubememory_incidents")
        client = chromadb.PersistentClient(path=persist_dir)
        coll = client.get_or_create_collection(name=collection_name)
        chroma_count = coll.count()
    except Exception:
        pass

    watcher = watcher_status()
    cluster_id = watcher.get("cluster_id")
    heartbeat_age = get_heartbeat_age_seconds(cluster_id) if watcher.get("running") else None
    watcher_healthy = (
        watcher.get("running") is True
        and heartbeat_age is not None
        and heartbeat_age < 45
    )

    watching_clusters = []
    for cluster in ClusterConnection.objects.filter(status=ClusterConnection.Status.WATCHING):
        age = get_heartbeat_age_seconds(cluster.id)
        watching_clusters.append(
            {
                "cluster_id": cluster.id,
                "name": cluster.name,
                "heartbeat_age_seconds": age,
                "healthy": age is not None and age < 45,
            }
        )

    failed_tasks = TaskLog.objects.filter(
        status__in=[TaskLog.Status.FAILURE, TaskLog.Status.RETRY]
    ).order_by("-created_at")[:50]

    model = os.environ.get("OLLAMA_REASONING_MODEL") or os.environ.get(
        "OLLAMA_CHAT_MODEL", "mistral:7b"
    )

    return Response(
        {
            "ollama_ready": ollama_ready,
            "ollama_ok": ollama_ready,
            "model": model,
            "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            "chroma_doc_count": chroma_count,
            "watcher": watcher,
            "watcher_healthy": watcher_healthy,
            "watcher_heartbeat_age_seconds": heartbeat_age,
            "watching_clusters": watching_clusters,
            "failed_tasks": [
                {
                    "id": t.id,
                    "task_id": t.task_id,
                    "task_name": t.task_name,
                    "status": t.status,
                    "error_message": t.error_message,
                    "created_at": t.created_at.isoformat(),
                }
                for t in failed_tasks
            ],
        }
    )
