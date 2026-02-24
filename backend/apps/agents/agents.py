"""
LangGraph agents: Retriever, Correlator, Recommender.
Stateless functions that read/write AgentState.
"""
import json
import logging
import os
import re
import urllib.request
from typing import Any

from langchain_ollama import ChatOllama

from apps.memory.graph_builder import KubeGraphBuilder
from apps.memory.vector_store import IncidentVectorStore

from .state import AgentState

logger = logging.getLogger(__name__)

# Fallback chat models to try if OLLAMA_CHAT_MODEL is not available (small, fast).
OLLAMA_CHAT_FALLBACKS = ("qwen2.5:0.5b", "phi3:mini", "llama3.2:3b", "llama3.2:1b", "mistral:7b")


def _get_available_ollama_models(base_url: str) -> list[str]:
    """Return list of model names available on the Ollama server."""
    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/tags",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception as e:
        logger.warning("Could not list Ollama models at %s: %s", base_url, e)
        return []


def get_working_chat_model(
    base_url: str | None = None,
    preferred: str | None = None,
) -> str | None:
    """
    Return a chat model name that exists on the Ollama server.
    Uses /api/tags: preferred first if available, then fallbacks, then any listed model.
    """
    base_url = base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    preferred = (preferred or os.environ.get("OLLAMA_CHAT_MODEL") or "mistral:7b").strip()
    available = _get_available_ollama_models(base_url)
    if not available:
        logger.warning("No models listed at Ollama %s; ensure Ollama is running and models are pulled.", base_url)
        return None
    # Ollama tags can return "name" or "name:tag"; match by prefix or exact.
    def name_matches(a: str, b: str) -> bool:
        return a == b or a.startswith(b + ":") or b.startswith(a + ":")
    if any(name_matches(m, preferred) for m in available):
        return preferred
    for fallback in OLLAMA_CHAT_FALLBACKS:
        if any(name_matches(m, fallback) for m in available):
            logger.info("Using fallback Ollama chat model: %s (preferred %s not available)", fallback, preferred)
            return fallback
    # Prefer names that don't look like embed-only models
    chat_like = [m for m in available if "embed" not in m.lower()]
    first = (chat_like[0] if chat_like else available[0])
    logger.info("Using first available Ollama chat model: %s (preferred %s not in list)", first, preferred)
    return first


def _to_similar_item(row: dict[str, Any]) -> dict[str, Any]:
    """Map vector store result to {content, score, metadata} for state."""
    return {
        "content": row.get("document", "") or "",
        "score": row.get("similarity_score", 0.0),
        "metadata": row.get("metadata", {}),
    }


def retriever_agent(state: AgentState) -> AgentState:
    """
    Semantic search in ChromaDB: similar incidents, past fixes, corrections.
    Never raises; appends any exception to state["errors"].
    """
    errors = list(state.get("errors") or [])
    similar_incidents: list[dict] = []
    past_fixes: list[dict] = []
    corrections: list[dict] = []

    try:
        query = (
            f"{state.get('incident_type', '')} {state.get('pod_name', '')} "
            f"{state.get('namespace', '')} {state.get('description', '')}"
        ).strip() or "Kubernetes incident"

        store = IncidentVectorStore()

        # Similar incidents: namespace filter; exclude fix/correction by filtering results
        raw_similar = store.search_similar(
            query,
            n_results=5,
            filter_namespace=state.get("namespace"),
        )
        for r in raw_similar:
            doc_type = (r.get("metadata") or {}).get("doc_type")
            if doc_type not in ("fix", "correction"):
                similar_incidents.append(_to_similar_item(r))

        # Past fixes
        raw_fixes = store.search_similar(
            query,
            n_results=3,
            doc_type="fix",
        )
        past_fixes = [_to_similar_item(r) for r in raw_fixes]

        # Corrections
        raw_corrections = store.search_similar(
            query,
            n_results=5,
            doc_type="correction",
        )
        corrections = [_to_similar_item(r) for r in raw_corrections]

    except Exception as e:
        logger.exception("retriever_agent failed: %s", e)
        errors.append(f"Retriever: {e!s}")

    state["similar_incidents"] = similar_incidents
    state["past_fixes"] = past_fixes
    state["corrections"] = corrections
    state["errors"] = errors
    return state


def correlator_agent(state: AgentState) -> AgentState:
    """
    Traverse Neo4j: causal patterns, blast radius, deploy correlation.
    Never raises; always returns state.
    """
    errors = list(state.get("errors") or [])
    causal_patterns: list[dict] = []
    blast_radius: list[dict] = []
    deploy_correlation: dict | None = None

    try:
        graph = KubeGraphBuilder()
        try:
            pod_name = state.get("pod_name", "")
            namespace = state.get("namespace", "")
            causal_patterns = graph.find_causal_patterns(pod_name, namespace)
            blast_radius = graph.find_blast_radius(pod_name, namespace)

            incident_id = state.get("incident_id")
            if incident_id is not None:
                deploy_correlation = graph.get_deploy_correlation_for_incident(incident_id)
        finally:
            graph.close()
    except Exception as e:
        logger.exception("correlator_agent failed: %s", e)
        errors.append(f"Correlator: {e!s}")

    state["causal_patterns"] = causal_patterns
    state["blast_radius"] = blast_radius
    state["deploy_correlation"] = deploy_correlation
    state["errors"] = errors
    return state


def _build_prompt(state: AgentState) -> str:
    """Build the SRE analysis prompt from pipeline state."""
    similar = state.get("similar_incidents") or []
    similar_text = "\n".join([
        f"- [{s.get('metadata', {}).get('occurred_at', 'unknown')}] "
        f"{s.get('metadata', {}).get('incident_type', '')} on "
        f"{s.get('metadata', {}).get('pod_name', '')}: {s.get('content', '')[:200]}"
        for s in similar
    ])

    fixes = state.get("past_fixes") or []
    fixes_text = "\n".join([f"- {f.get('content', '')[:200]}" for f in fixes])

    corrections_list = state.get("corrections") or []
    corrections_text = (
        "\n".join([f"- CORRECTION OVERRIDE: {c.get('content', '')[:200]}" for c in corrections_list])
        if corrections_list
        else "No corrections recorded."
    )

    patterns = state.get("causal_patterns") or []
    patterns_text = (
        "\n".join([
            f"- {p.get('incident_type', '')}: occurred {p.get('frequency', 0)} times. "
            f"Fixes that worked: {p.get('fixes_that_worked', [])}"
            for p in patterns
        ])
        if patterns
        else "No historical patterns found."
    )

    blast = state.get("blast_radius") or []
    blast_text = (
        ", ".join([
            f"{b.get('affected_pod', '')} (co-occurred {b.get('co_occurrence', 0)}x)"
            for b in blast
        ])
        if blast
        else "No blast radius detected."
    )

    deploy = state.get("deploy_correlation")
    if deploy:
        deploy_text = (
            f"⚠️ DEPLOY DETECTED: {deploy.get('service', '')} "
            f"v{deploy.get('version', '')} was deployed "
            f"{deploy.get('minutes_before_crash', 0):.0f} minutes before this crash."
        )
    else:
        deploy_text = "No recent deployment detected."

    return f"""You are a senior SRE analyzing a Kubernetes incident.
You have access to THIS CLUSTER'S actual incident history.
Base your analysis ENTIRELY on the provided cluster history — do not give generic advice.

=== CURRENT INCIDENT ===
Type: {state.get('incident_type', '')}
Pod: {state.get('pod_name', '')} in {state.get('namespace', '')}
Severity: {state.get('severity', '')}
Description: {state.get('description', '')}
Logs (excerpt): {(state.get('raw_logs') or '')[:300]}

=== SIMILAR INCIDENTS FROM THIS CLUSTER (semantic search) ===
{similar_text if similar_text else "No similar incidents found in history."}

=== FIXES THAT WORKED IN THIS CLUSTER ===
{fixes_text if fixes_text else "No fix history available."}

=== ENGINEER CORRECTIONS (AI was wrong, actual fixes) ===
{corrections_text}

=== CAUSAL PATTERNS (how often this happens + what fixed it) ===
{patterns_text}

=== BLAST RADIUS (services historically affected at same time) ===
{blast_text}

=== DEPLOYMENT CORRELATION ===
{deploy_text}

Based ONLY on the above cluster-specific data, provide your analysis in this EXACT format:

ROOT_CAUSE: [one sentence, reference specific cluster history]
RECOMMENDATION: [specific fix steps, reference what worked before in this cluster]
BLAST_RADIUS_WARNING: [which services to check, based on history]
PREVENTION: [specific preventive action based on recurring patterns]
CONFIDENCE: [0.0-1.0, higher if similar incidents found in history]
"""


def _parse_llm_response(text: str) -> dict[str, Any]:
    """Parse ROOT_CAUSE, RECOMMENDATION, PREVENTION, CONFIDENCE from LLM output."""
    out: dict[str, Any] = {
        "root_cause": "",
        "recommendation": "",
        "prevention_advice": "",
        "confidence": 0.0,
    }
    if not text:
        return out

    labels = ["ROOT_CAUSE", "RECOMMENDATION", "BLAST_RADIUS_WARNING", "PREVENTION", "CONFIDENCE"]
    for i, label in enumerate(labels):
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:\s]*(.*?)(?=\n(?:{'|'.join(labels[i+1:])})\s*:|\Z)",
            re.DOTALL | re.IGNORECASE,
        )
        m = pattern.search(text)
        if m:
            val = m.group(1).strip()
            if label == "ROOT_CAUSE":
                out["root_cause"] = val
            elif label == "RECOMMENDATION":
                out["recommendation"] = val
            elif label == "PREVENTION":
                out["prevention_advice"] = val
            elif label == "CONFIDENCE":
                try:
                    out["confidence"] = max(0.0, min(1.0, float(val)))
                except ValueError:
                    pass

    conf_m = re.search(r"CONFIDENCE:\s*([0-9.]+)", text, re.IGNORECASE)
    if conf_m:
        try:
            out["confidence"] = max(0.0, min(1.0, float(conf_m.group(1))))
        except ValueError:
            pass
    return out


def recommender_agent(state: AgentState) -> AgentState:
    """
    Synthesis agent: call Ollama with cluster-grounded prompt, parse response.
    Handles timeout (60s) and parse failures; never raises.
    """
    errors = list(state.get("errors") or [])
    root_cause = ""
    recommendation = ""
    prevention_advice = ""
    confidence = 0.0
    sources: list[str] = []

    similar = state.get("similar_incidents") or []
    for s in similar:
        inc_id = (s.get("metadata") or {}).get("incident_id")
        if inc_id is not None:
            sources.append(str(inc_id))

    try:
        ollama_url = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        model = get_working_chat_model(base_url=ollama_url)
        if not model:
            raise RuntimeError(
                "No Ollama chat model available. Pull a model, e.g.: ollama pull qwen2.5:0.5b"
            )
        llm = ChatOllama(model=model, base_url=ollama_url, timeout=60)
        prompt = _build_prompt(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", None) or str(response)
        parsed = _parse_llm_response(content)
        root_cause = parsed.get("root_cause", "")
        recommendation = parsed.get("recommendation", "")
        prevention_advice = parsed.get("prevention_advice", "")
        confidence = parsed.get("confidence", 0.0)
    except Exception as e:
        logger.exception("recommender_agent failed: %s", e)
        errors.append(f"Recommender: {e!s}")
        recommendation = "Analysis unavailable (LLM error or timeout)."
        root_cause = "Could not determine (pipeline error)."

    state["root_cause"] = root_cause
    state["recommendation"] = recommendation
    state["prevention_advice"] = prevention_advice
    state["confidence"] = confidence
    state["sources"] = sources
    state["errors"] = errors
    return state


def runbook_agent(state: AgentState) -> AgentState:
    """
    Generates a reusable runbook in Markdown from the incident analysis.
    Output can be pasted into Confluence, Notion, GitHub.
    """
    runbook_md = ""
    incident_type = state.get("incident_type", "Unknown")
    pod_name = state.get("pod_name", "unknown")
    service_name = state.get("pod_name", pod_name)
    root_cause = state.get("root_cause", "")
    past_fixes = state.get("past_fixes") or []
    blast_radius = state.get("blast_radius") or []
    recommendation = state.get("recommendation", "")

    past_fixes_text = "\n".join(
        [f"- {f.get('content', '')[:300]}" for f in past_fixes[:5]]
    ) if past_fixes else "No fixes recorded yet."
    blast_text = ", ".join(
        [f"{b.get('affected_pod', '')} ({b.get('co_occurrence', 0)}x)" for b in blast_radius[:5]]
    ) if blast_radius else "None identified."

    prompt = f"""Generate a production runbook for this incident type.
Base it on this cluster's actual history, not generic advice.

Incident: {incident_type} on {pod_name}
Root Cause (from analysis): {root_cause}
Fixes that worked in this cluster: {past_fixes_text}
Blast radius (co-occurring services): {blast_text}

Write the runbook in this EXACT Markdown format:

# Runbook: {incident_type} on {service_name}

## Symptoms
- [what the on-call engineer will see]

## Immediate Actions (< 5 minutes)
1. [first thing to do]
2. [second thing]

## Root Cause Investigation
- Check: [specific command]
- Check: [specific command]

## Fix Steps
1. [step with actual commands]
2. [step with actual commands]

## Blast Radius — Check These Services
- [service]: [what to check]

## Prevention
- [specific preventive action]

## Escalation
- If unresolved after 30 min: [who to page]

---
*Auto-generated by KubeMemory from cluster history*
"""
    try:
        ollama_url = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        model = get_working_chat_model(base_url=ollama_url)
        if model:
            llm = ChatOllama(model=model, base_url=ollama_url, timeout=90)
            response = llm.invoke(prompt)
            runbook_md = getattr(response, "content", None) or str(response) or ""
        else:
            runbook_md = f"# Runbook: {incident_type} on {service_name}\n\n## Symptoms\n- {root_cause or 'See incident description.'}\n\n## Fix Steps\n{recommendation or 'No recommendation available.'}\n\n---\n*Runbook stub (Ollama not available for full generation)*"
    except Exception as e:
        logger.exception("runbook_agent failed: %s", e)
        runbook_md = f"# Runbook: {incident_type} on {service_name}\n\n## Error\nRunbook generation failed: {e}\n\n## Recommendation from analysis\n{recommendation or 'N/A'}"
    state["runbook_md"] = runbook_md
    return state
