"""
Shared cluster tools for MCP server and in-app chat agent.
Execute tools in-process; used by both stdio MCP and WebSocket chat.
"""
from typing import Any


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """
    Run a cluster tool by name with the given arguments.
    Returns tool output as string. Raises on unknown tool; catches and returns errors for known tools.
    """
    try:
        if name == "analyze_incident":
            return _tool_analyze_incident(
                pod_name=arguments.get("pod_name", ""),
                namespace=arguments.get("namespace", ""),
                incident_type=arguments.get("incident_type", ""),
                description=arguments.get("description", ""),
                logs_excerpt=arguments.get("logs_excerpt", ""),
            )
        if name == "search_incident_history":
            return _tool_search_incident_history(
                query=arguments.get("query", ""),
                namespace=arguments.get("namespace"),
                limit=int(arguments.get("limit", 5)),
            )
        if name == "get_blast_radius":
            return _tool_get_blast_radius(
                pod_name=arguments.get("pod_name", ""),
                namespace=arguments.get("namespace", ""),
            )
        if name == "get_cluster_patterns":
            return _tool_get_cluster_patterns(
                namespace=arguments.get("namespace"),
                limit=int(arguments.get("limit", 10)),
            )
        if name == "get_pod_history":
            pod_name = (arguments.get("pod_name") or "").strip()
            namespace = (arguments.get("namespace") or "").strip()
            if not pod_name or pod_name.lower() in ("all", "any", "?"):
                return (
                    "get_pod_history requires a specific pod name and namespace. "
                    "For broad questions like 'all incidents' or 'incident history', use search_incident_history instead."
                )
            return _tool_get_pod_history(pod_name=pod_name, namespace=namespace)
        return f"Unknown tool: {name}"
    except Exception as e:
        return (
            f"Error executing {name}: {str(e)}\n"
            "Ensure KubeMemory services are running (Django, ChromaDB, Neo4j, Ollama)."
        )


def get_ollama_tools() -> list[dict[str, Any]]:
    """Return tool definitions in Ollama /api/chat format (type: function, function: { name, description, parameters })."""
    return [
        {
            "type": "function",
            "function": {
                "name": "analyze_incident",
                "description": "Analyze a Kubernetes incident using this cluster's full history. Returns root cause, recommendation, and blast radius grounded in actual past incidents.",
                "parameters": {
                    "type": "object",
                    "required": ["pod_name", "namespace"],
                    "properties": {
                        "pod_name": {"type": "string", "description": "Pod name"},
                        "namespace": {"type": "string", "description": "Namespace"},
                        "incident_type": {"type": "string", "description": "Optional incident type (e.g. CrashLoopBackOff, OOMKill)"},
                        "description": {"type": "string", "description": "Optional incident description"},
                        "logs_excerpt": {"type": "string", "description": "Optional logs excerpt"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_incident_history",
                "description": "Semantic search over this cluster's incident history. Use natural language: 'OOMKill incidents in production' or 'payment service crashes after deploy'",
                "parameters": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Natural language query"},
                        "namespace": {"type": "string", "description": "Filter by namespace"},
                        "limit": {"type": "integer", "description": "Max results", "default": 5},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_blast_radius",
                "description": "Find which services are historically affected when a specific pod fails. Useful for understanding incident scope before responding.",
                "parameters": {
                    "type": "object",
                    "required": ["pod_name", "namespace"],
                    "properties": {
                        "pod_name": {"type": "string"},
                        "namespace": {"type": "string"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_cluster_patterns",
                "description": "Get the top recurring incident patterns in this cluster. Shows which pods fail most often and what fixes have worked.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string", "description": "Filter by namespace"},
                        "limit": {"type": "integer", "description": "Max patterns", "default": 10},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pod_history",
                "description": "Get the full incident history for a specific pod. Shows all past incidents, resolutions, and timeline.",
                "parameters": {
                    "type": "object",
                    "required": ["pod_name", "namespace"],
                    "properties": {
                        "pod_name": {"type": "string"},
                        "namespace": {"type": "string"},
                    },
                },
            },
        },
    ]


# --- Tool implementations (same as MCP server) ---

def _tool_analyze_incident(
    pod_name: str,
    namespace: str,
    incident_type: str = "",
    description: str = "",
    logs_excerpt: str = "",
) -> str:
    from apps.agents.pipeline import analyze_incident_in_memory
    state = analyze_incident_in_memory(
        pod_name=pod_name,
        namespace=namespace,
        incident_type=incident_type or "Unknown",
        description=description,
        logs_excerpt=logs_excerpt,
    )
    errs = state.get("errors") or []
    if errs:
        err_text = "Errors: " + "; ".join(errs) + "\n\n"
    else:
        err_text = ""
    return (
        f"{err_text}"
        f"ROOT_CAUSE: {state.get('root_cause', '')}\n\n"
        f"RECOMMENDATION: {state.get('recommendation', '')}\n\n"
        f"BLAST_RADIUS_WARNING: {state.get('blast_radius', [])}\n\n"
        f"PREVENTION: {state.get('prevention_advice', '')}\n\n"
        f"CONFIDENCE: {state.get('confidence', 0.0)}"
    )


def _tool_search_incident_history(
    query: str,
    namespace: str | None = None,
    limit: int = 5,
) -> str:
    from apps.memory.vector_store import IncidentVectorStore
    store = IncidentVectorStore()
    results = store.search_similar(
        query,
        n_results=limit,
        filter_namespace=namespace,
    )
    lines = []
    for r in results:
        meta = r.get("metadata") or {}
        doc = r.get("document", "")
        score = r.get("similarity_score", 0)
        ts = meta.get("occurred_at", "unknown")
        it = meta.get("incident_type", "")
        pn = meta.get("pod_name", "")
        lines.append(f"- [{ts}] {it} on {pn} (score={score:.2f}): {doc[:200]}...")
    return "\n".join(lines) if lines else "No similar incidents found in cluster history."


def _tool_get_blast_radius(pod_name: str, namespace: str) -> str:
    from apps.memory.graph_builder import KubeGraphBuilder
    graph = KubeGraphBuilder()
    try:
        blast = graph.find_blast_radius(pod_name, namespace)
    finally:
        graph.close()
    if not blast:
        return f"No co-occurring services found for {pod_name}/{namespace}."
    lines = []
    for b in blast:
        lines.append(f"- {b.get('affected_pod', '')} (namespace={b.get('namespace', '')}): co-occurred {b.get('co_occurrence', 0)}x — {b.get('incident_types', [])}")
    return "\n".join(lines)


def _tool_get_cluster_patterns(namespace: str | None = None, limit: int = 10) -> str:
    from apps.incidents.models import ClusterPattern
    from apps.memory.graph_builder import KubeGraphBuilder
    qs = ClusterPattern.objects.all().order_by("-frequency")
    if namespace:
        qs = qs.filter(namespace=namespace)
    patterns = list(qs[:limit])
    graph = KubeGraphBuilder()
    try:
        deploy_crash = graph.find_deploy_to_crash_correlation()
    finally:
        graph.close()
    lines = ["=== Top recurring incident patterns ==="]
    for p in patterns:
        lines.append(f"- {p.pod_name} ({p.namespace}): {p.incident_type} x{p.frequency}; best_fix: {(p.best_fix or '')[:100]}...")
    lines.append("\n=== Deploy → crash correlation ===")
    for d in deploy_crash[:5]:
        lines.append(f"- {d.get('service')}: {d.get('crash_count')} crashes after deploy, avg {d.get('avg_minutes_to_crash')} min")
    return "\n".join(lines)


def _tool_get_pod_history(pod_name: str, namespace: str) -> str:
    from apps.incidents.models import Incident
    from django.db.models import Prefetch
    incidents = (
        Incident.objects.filter(pod_name=pod_name, namespace=namespace)
        .prefetch_related(Prefetch("fixes"))
        .order_by("-occurred_at")[:20]
    )
    lines = [f"Incident history for {pod_name} in {namespace}:"]
    for inc in incidents:
        ts = inc.occurred_at.isoformat() if inc.occurred_at else "unknown"
        lines.append(f"\n- [{ts}] {inc.incident_type} — {(inc.description or '')[:150]}...")
        for fix in inc.fixes.all():
            status = "✓" if fix.worked else "✗"
            lines.append(f"  Fix {status}: {fix.description[:100]}...")
    return "\n".join(lines) if len(lines) > 1 else f"No incident history found for {pod_name}/{namespace}."
