"""
Cluster chat agent: Ollama + MCP tools loop with streaming.
Production-grade, modular: tools come from apps.mcp_server.tools.
"""
import json
import logging
import os
from typing import Any, Callable

from apps.agents.agents import get_working_chat_model
from apps.mcp_server.tools import execute_tool, get_ollama_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the KubeMemory cluster assistant. You have access to this Kubernetes cluster's incident memory via tools.

**When to use each tool:**
- search_incident_history: Use for broad or vague questions — "recent incidents", "what happened", "any OOMKills", "incidents in production", "history". Only needs "query" (the user's question in natural language). Optional: namespace, limit.
- get_cluster_patterns: Use for "patterns", "what fails most", "recurring issues", "deploy crashes". Optional: namespace, limit.
- get_pod_history: Use ONLY when the user names a specific pod (e.g. "history for payment-api" or "incidents for pod x in default"). Requires both pod_name and namespace. Do NOT use for "all" or "everything" or when no pod is named.
- get_blast_radius: Use when the user asks which services are affected when a given pod fails. Requires pod_name and namespace.
- analyze_incident: Use when the user wants root cause or recommendation for a specific pod/incident. Requires pod_name and namespace.

**Rules:** For general questions like "show incidents" or "what's in the cluster", use search_incident_history with the user's message as the query. Never call get_pod_history without a specific pod name. If a tool returns "No ... found", say so and suggest: run `make seed` to add sample data, or narrow the query (e.g. a namespace or pod name). Answer concisely; summarize tool results for the user."""


def _ollama_chat_stream(
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict],
    stream_callback: Callable[[str, dict], None],
) -> tuple[str, str, list[dict]]:
    """
    Call Ollama /api/chat with stream=True. Invoke stream_callback("chunk", {"content": "..."}) for each content delta.
    Returns (accumulated_content, accumulated_thinking, tool_calls_list).
    """
    import urllib.request
    import urllib.error

    body = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": True,
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    content_acc = ""
    thinking_acc = ""
    tool_calls_acc: list[dict] = []
    buffer = ""
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            while True:
                chunk_bytes = resp.read(1024)
                if not chunk_bytes:
                    break
                buffer += chunk_bytes.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = parsed.get("message") or {}
                    if msg.get("content"):
                        content_acc += msg["content"]
                        stream_callback("chunk", {"content": msg["content"]})
                    if msg.get("thinking"):
                        thinking_acc += msg.get("thinking", "")
                    if msg.get("tool_calls"):
                        for tc in msg["tool_calls"]:
                            tool_calls_acc.append(tc)
                    if parsed.get("done"):
                        return content_acc, thinking_acc, tool_calls_acc
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else str(e)
        logger.exception("Ollama chat request failed: %s %s", e.code, err_body)
        stream_callback("error", {"message": f"Ollama error: {e.code} {err_body}"})
    except Exception as e:
        logger.exception("Ollama stream failed: %s", e)
        stream_callback("error", {"message": str(e)})
    return content_acc, thinking_acc, tool_calls_acc


def run_chat_agent(
    user_message: str,
    history: list[dict[str, str]] | None = None,
    stream_callback: Callable[[str, dict], None] | None = None,
) -> str:
    """
    Run the agent loop: user message + optional history, Ollama with tools, execute tool_calls, repeat until done.
    stream_callback(event_type, data) is called with:
      - "chunk", {"content": "..."} for each content delta
      - "tool_call", {"name": "...", "arguments": {...}, "result": "..."}
      - "done", {}
      - "error", {"message": "..."}
    Returns the full assistant reply (accumulated content).
    """
    base_url = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    model = get_working_chat_model(base_url=base_url)
    if not model:
        err = "No Ollama chat model available. Pull a model, e.g.: ollama pull qwen2.5:0.5b"
        if stream_callback:
            stream_callback("error", {"message": err})
        return err

    tools = get_ollama_tools()
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for h in history:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "") or ""})
    messages.append({"role": "user", "content": user_message})

    def noop(_event: str, _data: dict) -> None:
        pass

    cb = stream_callback or noop
    full_reply = ""
    max_tool_rounds = 10
    rounds = 0

    while rounds < max_tool_rounds:
        rounds += 1
        content, _thinking, tool_calls = _ollama_chat_stream(
            base_url, model, messages, tools, cb
        )
        full_reply = content

        # Fallback: if model didn't call any tool on first round and gave no/minimal reply,
        # run search_incident_history so the user gets useful cluster data
        if (
            rounds == 1
            and not tool_calls
            and (not content or len((content or "").strip()) < 80)
            and user_message.strip()
            and len(user_message.strip()) > 3
        ):
            query_lower = user_message.lower()
            if any(
                w in query_lower
                for w in (
                    "incident", "history", "crash", "pattern", "what", "show", "recent",
                    "oom", "error", "fail", "cluster", "namespace", "pod",
                )
            ):
                tool_calls = [
                    {
                        "function": {
                            "name": "search_incident_history",
                            "arguments": {"query": user_message.strip(), "limit": 8},
                        },
                    },
                ]
                full_reply = ""  # will be filled after tool result is summarized

        if tool_calls:
            # Build assistant message for Ollama (with tool_calls)
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": tc.get("function", {}).get("arguments") or {},
                    },
                }
                for tc in tool_calls
            ]
            messages.append(assistant_msg)
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name", "")
                args = fn.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args) if args else {}
                    except json.JSONDecodeError:
                        args = {}
                elif args is None:
                    args = {}
                result = execute_tool(name, args)
                messages.append({"role": "tool", "tool_name": name, "content": result})
                cb("tool_call", {"name": name, "arguments": args, "result": result[:500]})
        else:
            if content or full_reply:
                messages.append({"role": "assistant", "content": content or full_reply})
            cb("done", {})
            break
    else:
        cb("done", {})  # max rounds reached

    return full_reply
