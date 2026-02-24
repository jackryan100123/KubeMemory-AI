"""API views for agents: trigger analysis, get analysis, status."""
import logging

from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.incidents.models import Incident
from apps.incidents.tasks import run_ai_analysis_task

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["POST"])
def trigger_analyze(request, incident_id: int) -> Response:
    """
    Trigger analysis for an incident.
    By default runs synchronously so the result is available immediately (no Celery).
    Add ?async=1 to queue the task in Celery instead.
    """
    if not Incident.objects.filter(id=incident_id).exists():
        return Response(
            {"error": "Incident not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    run_async = request.query_params.get("async") in ("1", "true", "yes")
    if run_async:
        run_ai_analysis_task.delay(incident_id)
        return Response({"status": "queued", "incident_id": incident_id})
    # Run synchronously so the UI gets results without depending on Celery
    try:
        from apps.agents.pipeline import analyze_incident
        final_state = analyze_incident(incident_id)
        return Response({
            "status": "ok",
            "incident_id": incident_id,
            "confidence": final_state.get("confidence", 0.0),
        })
    except Exception as exc:
        logger.exception("trigger_analyze sync failed for incident_id=%s", incident_id)
        return Response(
            {"status": "error", "incident_id": incident_id, "error": str(exc)},
            status=status.HTTP_200_OK,
        )


@api_view(["GET"])
def get_analysis(request, incident_id: int) -> Response:
    """
    Return stored analysis for an incident.
    Includes recommendation, root_cause, confidence, sources, prevention_advice.
    If no analysis yet: {status: "pending"}.
    """
    incident = Incident.objects.filter(id=incident_id).first()
    if not incident:
        return Response(
            {"error": "Incident not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not (incident.ai_analysis or incident.ai_analysis.strip()):
        return Response({"status": "pending"})
    return Response({
        "status": "ok",
        "recommendation": incident.ai_analysis,
        "root_cause": getattr(incident, "ai_root_cause", "") or "",
        "confidence": getattr(incident, "ai_confidence", None) or 0.0,
        "sources": getattr(incident, "ai_sources", None) or [],
        "prevention_advice": getattr(incident, "ai_prevention_advice", "") or "",
    })


@api_view(["GET"])
def pipeline_status(request) -> Response:
    """
    Pipeline status: LLM model, Ollama connectivity, ChromaDB doc count.
    For dashboard health panel.
    """
    import os

    model = os.environ.get("OLLAMA_CHAT_MODEL") or "mistral:7b"
    ollama_url = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    chroma_count: int | None = None
    ollama_ok = False

    try:
        import chromadb

        persist_dir = os.environ.get("CHROMA_PERSIST_DIR") or "/app/chroma_data"
        collection_name = os.environ.get("CHROMA_COLLECTION_NAME") or "kubememory_incidents"
        client = chromadb.PersistentClient(path=persist_dir)
        coll = client.get_or_create_collection(name=collection_name)
        chroma_count = coll.count()
    except Exception:
        pass

    try:
        from langchain_ollama import ChatOllama

        llm = ChatOllama(model=model, base_url=ollama_url, timeout=5)
        llm.invoke("Hi")
        ollama_ok = True
    except Exception:
        pass

    return Response({
        "model": model,
        "ollama_base_url": ollama_url,
        "ollama_ok": ollama_ok,
        "chroma_doc_count": chroma_count,
    })


@api_view(["POST"])
def generate_runbook(request, incident_id: int) -> Response:
    """
    Run full pipeline then runbook_agent; return generated runbook Markdown.
    """
    incident = Incident.objects.filter(id=incident_id).first()
    if not incident:
        return Response(
            {"error": "Incident not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        from apps.agents.pipeline import analyze_incident
        from apps.agents.agents import runbook_agent

        final_state = analyze_incident(incident_id)
        final_state = runbook_agent(final_state)
        runbook_md = final_state.get("runbook_md") or ""
        return Response({"runbook_md": runbook_md})
    except Exception as exc:
        logger.exception("generate_runbook failed for incident_id=%s", incident_id)
        return Response(
            {"error": str(exc), "runbook_md": ""},
            status=status.HTTP_200_OK,
        )


@api_view(["GET"])
def risk_check(request) -> Response:
    """
    GET /api/agents/risk-check/?service=<name>&namespace=<name>
    Returns risk_level, risk_score, open_incidents, blast_radius_unstable, deploy_crash_history, recommendation.
    """
    service_name = (request.query_params.get("service") or "").strip()
    namespace = (request.query_params.get("namespace") or "").strip()
    if not service_name or not namespace:
        return Response(
            {"error": "Query params 'service' and 'namespace' are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    from apps.incidents.models import Incident
    from apps.memory.graph_builder import KubeGraphBuilder

    open_incidents = list(
        Incident.objects.filter(
            service_name=service_name,
            namespace=namespace,
            status__in=["open", "investigating"],
        )
    )
    critical_count = sum(1 for i in open_incidents if i.severity == "critical")
    high_count = sum(1 for i in open_incidents if i.severity == "high")

    blast: list = []
    deploy_history: list = []
    try:
        graph = KubeGraphBuilder()
        try:
            blast = graph.find_blast_radius(service_name, namespace)
            deploy_history = graph.find_deploy_to_crash_correlation()
        finally:
            graph.close()
    except Exception as e:
        logger.exception("risk_check graph failed: %s", e)
    deploy_history = [d for d in deploy_history if d.get("service") == service_name][:3]

    risk_score = critical_count * 40 + high_count * 20 + len([b for b in blast if (b.get("co_occurrence") or 0) > 2]) * 10
    risk_level = "high" if risk_score > 60 else "medium" if risk_score > 20 else "low"
    recommendation = (
        "Do not deploy" if risk_level == "high"
        else "Proceed with caution" if risk_level == "medium"
        else "Safe to deploy"
    )

    return Response({
        "risk_level": risk_level,
        "risk_score": risk_score,
        "open_incidents": len(open_incidents),
        "blast_radius_unstable": [b for b in blast if (b.get("co_occurrence") or 0) > 2],
        "deploy_crash_history": deploy_history,
        "recommendation": recommendation,
    })
