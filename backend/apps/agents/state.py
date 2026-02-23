"""
LangGraph agent state definition.
All state is passed through the pipeline — agents are stateless functions.
"""
from typing import List, Optional, TypedDict


class AgentState(TypedDict):
    """State passed through the Retriever → Correlator → Recommender pipeline."""

    # INPUT (set before pipeline starts)
    incident_id: int
    incident_type: str
    pod_name: str
    namespace: str
    description: str
    raw_logs: str
    severity: str

    # RETRIEVER OUTPUT
    similar_incidents: List[dict]
    past_fixes: List[dict]
    corrections: List[dict]

    # CORRELATOR OUTPUT
    causal_patterns: List[dict]
    blast_radius: List[dict]
    deploy_correlation: Optional[dict]

    # RECOMMENDER OUTPUT
    recommendation: str
    root_cause: str
    confidence: float
    sources: List[str]
    prevention_advice: str

    # PIPELINE META
    errors: List[str]
    processing_time_ms: int
