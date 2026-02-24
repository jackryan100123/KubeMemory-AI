"""
LangGraph pipeline orchestration.
Wires the three agents into a compiled graph.
"""
import time
from typing import Any

from langgraph.graph import END, StateGraph

from .agents import correlator_agent, recommender_agent, retriever_agent
from .state import AgentState

_pipeline: Any = None


def build_pipeline() -> Any:
    """Build and compile the LangGraph pipeline."""
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retriever_agent)
    graph.add_node("correlate", correlator_agent)
    graph.add_node("recommend", recommender_agent)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "correlate")
    graph.add_edge("correlate", "recommend")
    graph.add_edge("recommend", END)

    return graph.compile()


def get_pipeline() -> Any:
    """Return singleton compiled pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


def analyze_incident(incident_id: int) -> dict[str, Any]:
    """
    Main entry point. Loads incident from DB, runs full pipeline,
    saves analysis back to DB, returns final state.
    """
    from apps.incidents.models import Incident

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        raise ValueError(f"Incident id={incident_id} not found")

    initial_state = _state_from_incident(incident_id, incident)
    start = time.time()
    pipeline = get_pipeline()
    final_state = pipeline.invoke(initial_state)
    final_state["processing_time_ms"] = int((time.time() - start) * 1000)

    # Save analysis back to Postgres
    incident.ai_analysis = final_state.get("recommendation", "")
    incident.save(update_fields=["ai_analysis"])

    return final_state


def _state_from_incident(
    incident_id: int | None,
    incident: Any,
) -> AgentState:
    """Build initial AgentState from an incident-like object (model or dict)."""
    if hasattr(incident, "incident_type"):
        it = incident.incident_type or ""
        pn = incident.pod_name or ""
        ns = incident.namespace or ""
        desc = incident.description or ""
        raw = (getattr(incident, "raw_logs", None) or "")[:500]
        sev = incident.severity or ""
    else:
        it = incident.get("incident_type", "")
        pn = incident.get("pod_name", "")
        ns = incident.get("namespace", "")
        desc = incident.get("description", "")
        raw = (incident.get("raw_logs") or "")[:500]
        sev = incident.get("severity", "medium")

    return {
        "incident_id": incident_id,
        "incident_type": it,
        "pod_name": pn,
        "namespace": ns,
        "description": desc,
        "raw_logs": raw,
        "severity": sev,
        "similar_incidents": [],
        "past_fixes": [],
        "corrections": [],
        "causal_patterns": [],
        "blast_radius": [],
        "deploy_correlation": None,
        "recommendation": "",
        "root_cause": "",
        "confidence": 0.0,
        "sources": [],
        "prevention_advice": "",
        "errors": [],
        "processing_time_ms": 0,
    }


def analyze_incident_in_memory(
    pod_name: str,
    namespace: str,
    incident_type: str = "Unknown",
    description: str = "",
    logs_excerpt: str = "",
) -> dict[str, Any]:
    """
    Run the LangGraph pipeline for an in-memory incident (no DB save).
    Used by MCP tool analyze_incident. Returns final state with recommendation,
    root_cause, blast_radius, etc.
    """
    incident = {
        "pod_name": pod_name,
        "namespace": namespace,
        "incident_type": incident_type,
        "description": description,
        "raw_logs": logs_excerpt,
        "severity": "medium",
    }
    initial_state = _state_from_incident(None, incident)
    start = time.time()
    pipeline = get_pipeline()
    final_state = pipeline.invoke(initial_state)
    final_state["processing_time_ms"] = int((time.time() - start) * 1000)
    return final_state
