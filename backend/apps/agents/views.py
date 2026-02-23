"""API views for agents: trigger analysis, get analysis, status."""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.incidents.models import Incident
from apps.incidents.tasks import run_ai_analysis_task


@api_view(["POST"])
def trigger_analyze(request, incident_id: int) -> Response:
    """
    Trigger analysis manually (e.g. re-analysis after corrections).
    Returns {status: "queued", incident_id}.
    """
    if not Incident.objects.filter(id=incident_id).exists():
        return Response(
            {"error": "Incident not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    run_ai_analysis_task.delay(incident_id)
    return Response({"status": "queued", "incident_id": incident_id})


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
