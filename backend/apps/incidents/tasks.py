"""Celery tasks for incident ingestion and corrective RAG."""
import logging
from typing import Any

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import Incident
from .serializers import IncidentListSerializer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def ingest_incident_task(self, incident_data: dict) -> dict[str, Any]:
    """
    Full incident ingestion pipeline:
    1. Save Incident to Postgres (avoid duplicates)
    2. Embed in ChromaDB
    3. Write to Neo4j graph
    4. Update Postgres with memory IDs
    5. Push to WebSocket clients
    Returns incident ID and status.
    """
    try:
        from django.utils.dateparse import parse_datetime

        from apps.memory.graph_builder import KubeGraphBuilder
        from apps.memory.vector_store import IncidentVectorStore

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

        defaults = {
            "node_name": incident_data.get("node_name", ""),
            "service_name": incident_data.get("service_name", ""),
            "severity": severity,
            "status": Incident.Status.OPEN,
            "description": incident_data.get("description", ""),
            "raw_logs": incident_data.get("raw_logs", ""),
        }

        incident, created = Incident.objects.get_or_create(
            pod_name=incident_data.get("pod_name", ""),
            namespace=incident_data.get("namespace", ""),
            occurred_at=occurred_at,
            incident_type=incident_type,
            defaults=defaults,
        )

        if not created:
            return {"status": "duplicate", "incident_id": incident.id}

        # Step 2: Embed in ChromaDB
        vector_store = IncidentVectorStore()
        chroma_id = vector_store.embed_incident(incident)

        # Step 3: Write to Neo4j
        graph = KubeGraphBuilder()
        neo4j_id = graph.ingest_incident(incident)
        graph.close()

        # Step 4: Update Postgres with memory IDs
        incident.chroma_id = chroma_id
        incident.neo4j_id = neo4j_id
        incident.save(update_fields=["chroma_id", "neo4j_id"])

        # Step 5: Push to WebSocket clients
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "incidents",
                {
                    "type": "incident.alert",
                    "incident": IncidentListSerializer(incident).data,
                },
            )

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


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_ai_analysis_task(self, incident_id: int) -> dict[str, Any]:
    """
    Runs the full LangGraph 3-agent pipeline for an incident.
    Called after ingest_incident_task completes.
    Pushes analysis result to WebSocket clients.
    """
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


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def update_corrective_rag_task(self, fix_id: int) -> None:
    """
    Update corrective RAG when a fix is submitted.
    If fix.correction_of is set: add correction document in ChromaDB.
    If fix.worked is True: resolve incident in Neo4j.
    """
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
