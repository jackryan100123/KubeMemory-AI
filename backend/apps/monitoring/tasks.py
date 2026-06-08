"""
Celery tasks for monitoring: watcher health checks, vector pruning, backups.
"""
from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def check_watcher_health(self) -> dict[str, Any]:
    """
    If a cluster is WATCHING but heartbeat key is missing, ingest WATCHER_DOWN incident.
    Runs every 60s via Celery beat.
    """
    from apps.clusters.models import ClusterConnection
    from apps.incidents.tasks import ingest_incident_task
    from apps.watcher.heartbeat import get_heartbeat_age_seconds

    down_clusters: list[int] = []
    for cluster in ClusterConnection.objects.filter(status=ClusterConnection.Status.WATCHING):
        age = get_heartbeat_age_seconds(cluster.id)
        if age is None or age > 45:
            occurred = timezone.now().isoformat()
            ingest_incident_task.delay(
                {
                    "pod_name": "kubememory-watcher",
                    "namespace": "kubememory-system",
                    "incident_type": "WatcherDown",
                    "severity": "critical",
                    "description": (
                        f"Watcher heartbeat missing for cluster '{cluster.name}' "
                        f"(id={cluster.id}). Last seen: {age!s}s ago."
                    ),
                    "raw_logs": "",
                    "occurred_at": occurred,
                    "cluster_id": cluster.id,
                }
            )
            down_clusters.append(cluster.id)
            logger.critical(
                "Watcher down for cluster %s (%s); ingested WATCHER_DOWN incident",
                cluster.id,
                cluster.name,
            )
    return {"checked": True, "down_clusters": down_clusters}


_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@shared_task(bind=True, max_retries=2, default_retry_delay=30, queue="ingest")
def send_notification(self, incident_id: int) -> dict[str, Any]:
    """POST incident summary to configured Slack/webhook sinks."""
    import json
    import urllib.request

    from apps.incidents.models import Incident
    from apps.monitoring.models import NotificationConfig

    incident = Incident.objects.filter(id=incident_id).select_related("cluster").first()
    if not incident:
        return {"sent": 0}

    rank = _SEVERITY_RANK.get(incident.severity, 0)
    sent = 0
    frontend_base = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173")

    for cfg in NotificationConfig.objects.filter(enabled=True):
        min_rank = _SEVERITY_RANK.get(cfg.min_severity, 2)
        if rank < min_rank:
            continue
        detail_url = f"{frontend_base}/incidents/{incident.id}"
        try:
            if cfg.type == NotificationConfig.NotificationType.SLACK:
                payload = {
                    "text": (
                        f"*KubeMemory* — {incident.severity.upper()} incident\n"
                        f"*{incident.incident_type}* on `{incident.pod_name}` "
                        f"({incident.namespace})\n"
                        f"{incident.description[:300]}\n"
                        f"<{detail_url}|View incident>"
                    )
                }
            else:
                payload = {
                    "id": incident.id,
                    "severity": incident.severity,
                    "incident_type": incident.incident_type,
                    "pod_name": incident.pod_name,
                    "namespace": incident.namespace,
                    "description": incident.description,
                    "cluster": incident.cluster.name if incident.cluster else None,
                    "detail_url": detail_url,
                }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                cfg.url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15):
                sent += 1
        except Exception as exc:
            logger.warning("Notification failed for config %s: %s", cfg.id, exc)
    return {"sent": sent}


@shared_task(bind=True, max_retries=1, default_retry_delay=120, queue="ingest")
def prune_old_vectors(self) -> dict[str, Any]:
    """Delete Chroma embeddings and stale Neo4j nodes older than CHROMA_RETENTION_DAYS."""
    from datetime import timedelta

    from apps.incidents.models import Incident
    from apps.memory.graph_builder import KubeGraphBuilder
    from apps.memory.vector_store import IncidentVectorStore

    days = int(os.environ.get("CHROMA_RETENTION_DAYS", "90"))
    cutoff = timezone.now() - timedelta(days=days)

    old_incidents = Incident.objects.filter(occurred_at__lt=cutoff).exclude(chroma_id="")
    chroma_removed = 0
    vs = IncidentVectorStore()
    for inc in old_incidents:
        if vs.delete_incident(inc):
            chroma_removed += 1
            inc.chroma_id = ""
            inc.save(update_fields=["chroma_id"])

    graph = KubeGraphBuilder()
    neo4j_removed = graph.prune_stale_incidents(cutoff)
    graph.close()

    logger.info(
        "prune_old_vectors: chroma_removed=%s neo4j_removed=%s retention_days=%s",
        chroma_removed,
        neo4j_removed,
        days,
    )
    return {"chroma_removed": chroma_removed, "neo4j_removed": neo4j_removed, "days": days}


@shared_task(bind=True, max_retries=1, default_retry_delay=300, queue="ingest")
def backup_databases(self) -> dict[str, Any]:
    """Daily Postgres dump and Neo4j admin backup with retention pruning."""
    import gzip
    import shutil
    import subprocess
    from datetime import date, timedelta
    from pathlib import Path

    backup_root = Path(os.environ.get("BACKUP_DIR", "/backups"))
    retention = int(os.environ.get("BACKUP_RETENTION_DAYS", "7"))
    today = date.today().isoformat()
    pg_dir = backup_root / "postgres"
    pg_dir.mkdir(parents=True, exist_ok=True)
    pg_file = pg_dir / f"{today}.sql.gz"

    pg_host = os.environ.get("POSTGRES_HOST", "postgres")
    pg_db = os.environ.get("POSTGRES_DB", "kubememory")
    pg_user = os.environ.get("POSTGRES_USER", "kubememory")
    pg_password = os.environ.get("POSTGRES_PASSWORD", "")

    env = {**os.environ, "PGPASSWORD": pg_password}
    try:
        proc = subprocess.run(
            [
                "pg_dump",
                "-h",
                pg_host,
                "-U",
                pg_user,
                "-d",
                pg_db,
            ],
            capture_output=True,
            check=True,
            env=env,
            timeout=600,
        )
        with gzip.open(pg_file, "wb") as fh:
            fh.write(proc.stdout)
    except Exception as exc:
        logger.exception("Postgres backup failed: %s", exc)
        raise self.retry(exc=exc)

    neo4j_dir = backup_root / "neo4j"
    neo4j_dir.mkdir(parents=True, exist_ok=True)
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
    try:
        subprocess.run(
            [
                "neo4j-admin",
                "database",
                "dump",
                "neo4j",
                f"--to-path={neo4j_dir / today}",
            ],
            check=False,
            timeout=600,
            capture_output=True,
        )
    except FileNotFoundError:
        logger.warning("neo4j-admin not in PATH; skipping Neo4j backup")

    cutoff = date.today() - timedelta(days=retention)
    for path in pg_dir.glob("*.sql.gz"):
        try:
            file_date = date.fromisoformat(path.stem.replace(".sql", ""))
            if file_date < cutoff:
                path.unlink(missing_ok=True)
        except ValueError:
            pass
    for path in neo4j_dir.iterdir():
        if path.is_dir():
            try:
                if date.fromisoformat(path.name) < cutoff:
                    shutil.rmtree(path, ignore_errors=True)
            except ValueError:
                pass

    return {"postgres": str(pg_file), "retention_days": retention}
