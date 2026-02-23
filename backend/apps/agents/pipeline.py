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

    initial_state: AgentState = {
        "incident_id": incident_id,
        "incident_type": incident.incident_type or "",
        "pod_name": incident.pod_name or "",
        "namespace": incident.namespace or "",
        "description": incident.description or "",
        "raw_logs": (incident.raw_logs or "")[:500],
        "severity": incident.severity or "",
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

    start = time.time()
    pipeline = get_pipeline()
    final_state = pipeline.invoke(initial_state)
    final_state["processing_time_ms"] = int((time.time() - start) * 1000)

    # Save analysis back to Postgres
    incident.ai_analysis = final_state.get("recommendation", "")
    incident.save(update_fields=["ai_analysis"])

    return final_state
