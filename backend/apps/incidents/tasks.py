"""Celery tasks for incident ingestion and corrective RAG."""
import logging
import os
from typing import Any

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.clusters.models import ClusterConnection
from .fingerprint import compute_incident_fingerprint
from .models import Incident
from .serializers import IncidentListSerializer

logger = logging.getLogger(__name__)


def estimate_waste_usd(incident_data: dict) -> float:
    """
    Rough monthly cost of a repeatedly crashing pod.
    Based on: restarts * avg engineer time (30min) * $100/hr
    + wasted compute (requests * restart_count * 0.001 USD/hr * 730 hrs/month).
    """
    restarts = int(incident_data.get("restart_count", 0) or 0)
    if restarts <= 0:
        restarts = 1
    engineer_cost = restarts * 0.5 * 100
    compute_waste = restarts * 0.001 * 730
    return round(engineer_cost + compute_waste, 2)


def _broadcast_incident(event_type: str, incident: Incident) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    channel_type = "incident.alert" if event_type == "new_incident" else "incident.updated"
    payload = {
        "type": channel_type,
        "incident": IncidentListSerializer(incident).data,
    }
    async_to_sync(channel_layer.group_send)("incidents", payload)


@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue="ingest")
def ingest_incident_task(self, incident_data: dict) -> dict[str, Any]:
    """
    Full incident ingestion pipeline with fingerprint deduplication.
    """
    try:
        from django.utils.dateparse import parse_datetime

        from apps.memory.graph_builder import KubeGraphBuilder
        from apps.memory.vector_store import IncidentVectorStore
        from apps.monitoring.tasks import send_notification

        occurred_at = incident_data.get("occurred_at")
        if isinstance(occurred_at, str):
            occurred_at = parse_datetime(occurred_at) or timezone.now()
        elif occurred_at is None:
            occurred_at = timezone.now()

        incident_type = incident_data.get("incident_type", "Unknown")
        severity = incident_data.get("severity", "medium")
        if incident_type not in dict(Incident.IncidentType.choices):
            incident_type = Incident.IncidentType.UNKNOWN
        if severity not in dict(Incident.Severity.choices):
            severity = Incident.Severity.MEDIUM

        cluster_obj: ClusterConnection | None = None
        cluster_id_val = incident_data.get("cluster_id")
        cluster_id_int: int | None = None
        if cluster_id_val is not None:
            try:
                cluster_id_int = int(cluster_id_val)
                cluster_obj = ClusterConnection.objects.filter(id=cluster_id_int).first()
            except (TypeError, ValueError):
                cluster_obj = None

        pod_name = incident_data.get("pod_name", "") or ""
        namespace = incident_data.get("namespace", "") or ""
        fp = compute_incident_fingerprint(
            namespace, pod_name, incident_type, occurred_at, cluster_id_int
        )

        existing = Incident.objects.filter(fingerprint=fp).first()
        if existing:
            existing.occurrence_count += 1
            existing.last_seen_at = occurred_at
            existing.save(update_fields=["occurrence_count", "last_seen_at", "updated_at"])
            _broadcast_incident("incident_updated", existing)
            return {
                "status": "duplicate",
                "incident_id": existing.id,
                "occurrence_count": existing.occurrence_count,
            }

        embed_version = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        incident = Incident.objects.create(
            cluster=cluster_obj,
            pod_name=pod_name,
            namespace=namespace,
            incident_type=incident_type,
            occurred_at=occurred_at,
            last_seen_at=occurred_at,
            fingerprint=fp,
            occurrence_count=1,
            embedding_model_version=embed_version,
            node_name=incident_data.get("node_name", ""),
            service_name=incident_data.get("service_name", ""),
            severity=severity,
            status=Incident.Status.OPEN,
            description=incident_data.get("description", ""),
            raw_logs=incident_data.get("raw_logs", ""),
            estimated_waste_usd=estimate_waste_usd(incident_data),
        )

        vector_store = IncidentVectorStore()
        chroma_id = vector_store.embed_incident(incident)

        graph = KubeGraphBuilder()
        neo4j_id = graph.ingest_incident(incident)
        graph.close()

        incident.chroma_id = chroma_id
        incident.neo4j_id = neo4j_id
        incident.save(update_fields=["chroma_id", "neo4j_id"])

        _broadcast_incident("new_incident", incident)
        send_notification.delay(incident.id)

        logger.info(
            "Ingested incident id=%s pod=%s namespace=%s chroma=%s neo4j=%s",
            incident.id,
            incident.pod_name,
            incident.namespace,
            chroma_id,
            neo4j_id,
        )
        run_ai_analysis_task.delay(incident.id)
        return {"status": "created", "incident_id": incident.id}

    except Exception as exc:
        logger.exception("ingest_incident_task failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60, queue="llm")
def run_ai_analysis_task(self, incident_id: int) -> dict[str, Any]:
    """Runs the LangGraph pipeline; pushes analysis to WebSocket clients."""
    try:
        from apps.agents.pipeline import analyze_incident

        final_state = analyze_incident(incident_id)

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "incidents",
                {
                    "type": "analysis.complete",
                    "incident_id": incident_id,
                    "analysis": final_state.get("recommendation", ""),
                    "root_cause": final_state.get("root_cause", ""),
                    "confidence": final_state.get("confidence", 0.0),
                    "sources": final_state.get("sources", []),
                    "analysis_result": final_state.get("analysis_result", {}),
                },
            )

        return {
            "status": "done",
            "incident_id": incident_id,
            "confidence": final_state.get("confidence", 0.0),
        }
    except Exception as exc:
        logger.exception("run_ai_analysis_task failed for incident_id=%s: %s", incident_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=15, queue="ingest")
def update_corrective_rag_task(self, fix_id: int) -> None:
    """Update corrective RAG when a fix is submitted."""
    try:
        from apps.incidents.models import Fix
        from apps.memory.graph_builder import KubeGraphBuilder
        from apps.memory.vector_store import IncidentVectorStore

        fix = Fix.objects.filter(id=fix_id).select_related("incident", "correction_of").first()
        if not fix:
            logger.warning("update_corrective_rag_task: fix_id=%s not found", fix_id)
            return

        vector_store = IncidentVectorStore()
        if fix.correction_of_id:
            vector_store.update_with_correction(fix.correction_of, fix)

        if fix.worked and fix.incident.neo4j_id:
            graph = KubeGraphBuilder()
            try:
                graph.resolve_incident(fix.incident.neo4j_id, fix.description)
            finally:
                graph.close()

        logger.info("Corrective RAG updated for fix_id=%s", fix_id)
    except Exception as exc:
        logger.exception("update_corrective_rag_task failed for fix_id=%s: %s", fix_id, exc)
        raise self.retry(exc=exc)
