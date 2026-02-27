"""
Tool definitions for the chat engine.
Same capabilities as MCP tools; structured as LangChain tools for in-app chat.
ALL logic delegates to apps/memory/ and apps/agents/ — no duplication.
"""
from langchain_core.tools import tool

from apps.incidents.models import ClusterPattern, Incident
from apps.memory.graph_builder import KubeGraphBuilder
from apps.memory.vector_store import IncidentVectorStore


@tool
def search_incidents(
    query: str, namespace: str | None = None, limit: int = 5
) -> str:
    """
    Semantic search over this cluster's incident history.
    Use for: 'show me OOMKill incidents', 'payment service crashes',
    'what happened last week', 'database timeout errors'
    """
    vs = IncidentVectorStore()
    results = vs.search_similar(
        query, n_results=limit, filter_namespace=namespace
    )
    if not results:
        return "No similar incidents found in cluster history."

    lines = [f"Found {len(results)} similar incidents:\n"]
    for r in results:
        m = r.get("metadata") or {}
        doc = r.get("document") or ""
        score = r.get("similarity_score") or 0.0
        lines.append(
            f"• [{str(m.get('occurred_at', '?'))[:10]}] {m.get('incident_type')} "
            f"on {m.get('pod_name')} ({m.get('namespace')}) "
            f"— severity: {m.get('severity')} "
            f"— similarity: {score:.0%}\n"
            f"  {doc[:120]}"
        )
    return "\n".join(lines)


@tool
def analyze_pod(
    pod_name: str, namespace: str, incident_type: str = "Unknown"
) -> str:
    """
    Deep AI analysis of a specific pod using the full LangGraph pipeline.
    Use for: 'analyze payment-service', 'why does auth-service keep crashing',
    'give me a full analysis of worker pod'
    """
    from apps.agents.pipeline import analyze_incident

    incident = (
        Incident.objects.filter(pod_name=pod_name, namespace=namespace)
        .order_by("-occurred_at")
        .first()
    )

    if not incident:
        return (
            f"No incidents found for {pod_name} in {namespace}. "
            "The pod may be healthy or not yet tracked."
        )

    if not incident.ai_analysis:
        state = analyze_incident(incident.id)
        return (
            f"ANALYSIS for {pod_name}:\n\n"
            f"ROOT CAUSE: {state.get('root_cause', 'unknown')}\n\n"
            f"RECOMMENDATION: {state.get('recommendation', 'none')}\n\n"
            f"CONFIDENCE: {state.get('confidence', 0):.0%}\n\n"
            f"PREVENTION: {state.get('prevention_advice', 'none')}"
        )

    return f"STORED ANALYSIS for {pod_name}:\n\n{incident.ai_analysis}"


@tool
def get_blast_radius(pod_name: str, namespace: str) -> str:
    """
    Find which services historically crash when this pod fails.
    Use for: 'blast radius of payment-service', 'what breaks when X goes down',
    'downstream impact of auth-service failure'
    """
    graph = KubeGraphBuilder()
    try:
        results = graph.find_blast_radius(pod_name, namespace)
    finally:
        graph.close()

    if not results:
        return (
            f"No blast radius data found for {pod_name}. "
            "It may not have co-occurring incidents in history."
        )

    lines = [
        f"Blast radius for {pod_name} (from {len(results)} co-occurrence patterns):\n"
    ]
    for r in results:
        co = r.get("co_occurrence") or 0
        risk = (
            "🔴 HIGH"
            if co > 5
            else "🟡 MEDIUM"
            if co > 2
            else "🟢 LOW"
        )
        lines.append(
            f"  {risk} {r.get('affected_pod')} ({r.get('namespace')}) "
            f"— co-occurred {co}x"
        )
    return "\n".join(lines)


@tool
def get_top_blast_radius_services(namespace: str = "default", limit: int = 10) -> str:
    """
    List which pods/services have the LARGEST blast radius (when they fail, the most
    other pods tend to fail too). Use for: 'which services cause the most blast radius',
    'what has the biggest impact when it goes down', 'highest blast radius services'.
    Does NOT require a specific pod name — use this for cluster-wide blast radius ranking.
    """
    graph = KubeGraphBuilder()
    try:
        results = graph.find_top_blast_radius_pods(namespace=namespace, limit=limit)
    finally:
        graph.close()

    if not results:
        return (
            "No blast radius data in the graph yet. "
            "Ingest more incidents so co-occurrence patterns can be computed."
        )

    lines = [
        f"Top {len(results)} services by blast radius (namespace: {namespace}):\n"
    ]
    for i, r in enumerate(results, 1):
        size = r.get("blast_size") or 0
        risk = "🔴 HIGH" if size > 5 else "🟡 MEDIUM" if size > 2 else "🟢 LOW"
        lines.append(
            f"  {i}. {risk} {r.get('pod_name')} — when it fails, ~{size} other pod(s) tend to co-fail"
        )
    return "\n".join(lines)


@tool
def get_patterns(namespace: str | None = None, limit: int = 8) -> str:
    """
    Get the top recurring incident patterns in this cluster.
    Use for: 'what keeps breaking', 'most common incidents',
    'recurring problems', 'cluster patterns'
    """
    qs = ClusterPattern.objects.all()
    if namespace:
        qs = qs.filter(namespace=namespace)
    patterns = list(qs.order_by("-frequency")[:limit])

    if not patterns:
        return "No recurring patterns found yet. More incidents need to be processed."

    lines = [f"Top {len(patterns)} recurring patterns:\n"]
    for p in patterns:
        best = (p.best_fix or "")[:100] if p.best_fix else "none recorded"
        rate = getattr(p, "fix_success_rate", 0.0) or 0.0
        lines.append(
            f"• {p.pod_name} ({p.namespace}) — {p.incident_type} "
            f"× {p.frequency} times | fix success: {rate:.0%}\n"
            f"  Best fix: {best}"
        )
    return "\n".join(lines)


@tool
def get_pod_timeline(
    pod_name: str, namespace: str, limit: int = 10
) -> str:
    """
    Get the full incident timeline for a specific pod.
    Use for: 'history of payment-service', 'timeline of auth crashes',
    'all incidents for worker pod', 'what happened to X pod'
    """
    incidents = (
        Incident.objects.filter(pod_name=pod_name, namespace=namespace)
        .order_by("-occurred_at")[:limit]
    )

    if not incidents:
        return f"No incident history found for {pod_name} in {namespace}."

    lines = [
        f"Incident timeline for {pod_name} ({len(incidents)} incidents):\n"
    ]
    for i in incidents:
        fixes = i.fixes.filter(worked=True)
        fix_str = (
            f"✓ fixed: {fixes.first().description[:60]}"
            if fixes.exists()
            else "✗ no fix recorded"
        )
        lines.append(
            f"  [{i.occurred_at.strftime('%Y-%m-%d %H:%M')}] "
            f"{i.incident_type} — {i.severity.upper()} — {i.status}\n"
            f"  {fix_str}"
        )
    return "\n".join(lines)


@tool
def risk_check(service_name: str, namespace: str) -> str:
    """
    Pre-deploy risk assessment. Should we deploy right now?
    Use for: 'is it safe to deploy payment-service',
    'risk of deploying to production', 'should I deploy now'
    """
    from apps.agents.views import compute_risk_check

    result = compute_risk_check(service_name, namespace)
    level = (result.get("risk_level") or "low").upper()
    emoji = "🔴" if level == "HIGH" else "🟡" if level == "MEDIUM" else "🟢"
    lines = [
        f"{emoji} RISK LEVEL: {level} (score: {result.get('risk_score', 0)})",
        f"Open incidents: {result.get('open_incidents', 0)}",
        f"Recommendation: {result.get('recommendation', '')}",
    ]
    if result.get("blast_radius_unstable"):
        pods = [
            b.get("pod") or b.get("affected_pod")
            for b in result["blast_radius_unstable"]
        ]
        lines.append(f"Unstable services in blast radius: {pods}")
    if result.get("deploy_crash_history"):
        lines.append(
            "Recent deploy→crash history found — proceed with caution"
        )
    return "\n".join(lines)


@tool
def get_graph_context(namespace: str) -> str:
    """
    Get a summary of the knowledge graph for a namespace.
    Use for: 'what does the graph look like', 'show me the cluster topology',
    'what services are in production'
    """
    graph = KubeGraphBuilder()
    try:
        data = graph.get_graph_data_for_namespace(namespace)
    finally:
        graph.close()

    nodes = data.get("nodes") or []
    links = data.get("links") or []
    pods = [n for n in nodes if n.get("type") == "Pod"]
    services = [n for n in nodes if n.get("type") == "Service"]
    incidents = [n for n in nodes if n.get("type") == "Incident"]

    return (
        f"Graph context for {namespace}:\n"
        f"  {len(pods)} pods tracked\n"
        f"  {len(services)} services\n"
        f"  {len(incidents)} incident nodes\n"
        f"  {len(links)} causal relationships\n\n"
        f"Pods: {[p.get('name') for p in pods[:10]]}\n"
        f"Open incidents: {[n.get('name') for n in incidents if not n.get('resolved')][:5]}"
    )


CHAT_TOOLS = [
    search_incidents,
    analyze_pod,
    get_blast_radius,
    get_top_blast_radius_services,
    get_patterns,
    get_pod_timeline,
    risk_check,
    get_graph_context,
]


def execute_tool(
    name: str, args: dict, namespace: str | None = None
) -> str:
    """Dispatch tool call by name. Injects session namespace when missing."""
    if namespace and "namespace" not in args:
        args = {**args, "namespace": namespace}
    tool_map = {t.name: t for t in CHAT_TOOLS}
    if name not in tool_map:
        return f"Unknown tool: {name}"

    # Guard: tools that require a specific pod name — avoid validation errors
    if name in ("get_pod_timeline", "get_blast_radius", "analyze_pod"):
        pod_name = (args.get("pod_name") or "").strip().lower()
        if not pod_name or pod_name in ("all", "any", "?", "none"):
            return (
                f"{name} requires a specific pod name and namespace. "
                "For 'which services cause blast radius' or 'most impactful services', "
                "use get_top_blast_radius_services instead. "
                "For broad incident queries use search_incidents with a natural-language query."
            )

    return tool_map[name].invoke(args)
