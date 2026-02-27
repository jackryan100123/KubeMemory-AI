"""
KubeMemory Chat Engine.

Manages a multi-turn conversation with full tool use.
Uses LangGraph pipeline tools under the hood.
Streams tokens back via a generator for SSE.

Design:
  - User sends message + session_id
  - Engine loads conversation history from DB
  - Builds messages array with history
  - Calls Ollama with tool definitions
  - If Ollama wants to call a tool → run tool → append result → continue
  - Stream final response tokens back
  - Save all messages to DB
"""
import json
import logging
import os
import time
from typing import Any, Generator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from .models import ChatMessage, ChatSession
from .tools import CHAT_TOOLS, execute_tool

logger = logging.getLogger("apps.chat")

SYSTEM_PROMPT = """You are KubeMemory Assistant — an expert SRE AI with access to
THIS cluster's complete incident history, causal graph, and fix database.

You have access to these tools:
- search_incidents: semantic search over past incidents (query, optional namespace, limit)
- analyze_pod: deep analysis of a specific pod (pod_name, namespace required)
- get_blast_radius: for ONE specific pod, find which other pods crash with it (pod_name, namespace required)
- get_top_blast_radius_services: cluster-wide — which pods have the LARGEST blast radius (namespace, limit). Use for "which services cause the most blast radius" or "highest impact services"
- get_patterns: top recurring incident patterns (optional namespace, limit)
- get_pod_timeline: full incident history for ONE pod (pod_name, namespace required)
- risk_check: pre-deploy risk for a service (service_name, namespace)
- get_graph_context: graph summary for a namespace

RULES:
1. ALWAYS use tools before answering — never guess from general knowledge.
2. Ground every answer in actual cluster data retrieved by tools.
3. When a tool returns no results, say so honestly and suggest alternatives.
4. Keep answers concise; use bullet points for lists.
5. WHICH TOOL TO USE:
   - "Which services cause (the most) blast radius?" / "highest blast radius" / "most impactful when they fail" → use get_top_blast_radius_services (NOT get_blast_radius).
   - "Blast radius of payment-service" / "what breaks when X goes down" (user named a pod) → use get_blast_radius(pod_name, namespace).
   - "All incidents", "incidents last 7 days", "recent incidents", no specific pod → use search_incidents with a natural-language query.
   - get_pod_timeline and get_blast_radius require a specific pod_name; if the user did not name a pod, use get_top_blast_radius_services (for blast radius) or search_incidents (for incidents).
6. After calling a tool, summarize the results clearly for the user; if a tool returns "no results", explain what they can try instead.

Current cluster namespace context: {namespace}
"""


class ChatEngine:
    """Runs the chat conversation with tool use and streaming."""

    def __init__(self, session: ChatSession) -> None:
        self.session = session
        self.llm = ChatOllama(
            model=os.environ.get("OLLAMA_CHAT_MODEL", "mistral:7b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
            temperature=0.1,
        )

    def _load_history(self) -> list:
        """Load conversation history as LangChain message objects."""
        messages: list = [
            SystemMessage(
                content=SYSTEM_PROMPT.format(namespace=self.session.namespace)
            )
        ]
        for msg in self.session.messages.all():
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content or ""))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content or ""))
            elif msg.role == "tool_result":
                messages.append(
                    ToolMessage(
                        content=msg.tool_output or "",
                        tool_call_id=str(msg.id),
                    )
                )
        return messages

    def _save_message(
        self, role: str, content: str, **kwargs: Any
    ) -> ChatMessage:
        """Persist a message to the database."""
        msg = ChatMessage.objects.create(
            session=self.session,
            role=role,
            content=content,
            **kwargs,
        )
        self.session.message_count += 1
        self.session.save(update_fields=["message_count", "updated_at"])
        return msg

    def _tool_description(self, tool_name: str) -> str:
        """Human-readable description for tool call events."""
        descriptions = {
            "search_incidents": "Searching incident history...",
            "analyze_pod": "Running LangGraph 3-agent analysis...",
            "get_blast_radius": "Querying blast radius for this pod...",
            "get_top_blast_radius_services": "Finding services with largest blast radius...",
            "get_patterns": "Loading cluster patterns...",
            "get_pod_timeline": "Fetching pod incident timeline...",
            "risk_check": "Running pre-deploy risk assessment...",
            "get_graph_context": "Loading knowledge graph data...",
        }
        return descriptions.get(tool_name, f"Calling {tool_name}...")

    def stream_response(self, user_message: str) -> Generator[dict, None, None]:
        """
        Main entry point. Yields SSE-compatible dicts:
          {"type": "token",       "content": "partial text"}
          {"type": "tool_call",   "tool": "...", "input": {...}}
          {"type": "tool_result", "tool": "...", "output": "...", "success": bool}
          {"type": "done",        "message_id": 42, "latency_ms": 1234}
          {"type": "error",       "message": "..."}
        """
        start = time.time()

        self._save_message("user", user_message)
        self.session.auto_title()

        history = self._load_history()
        history.append(HumanMessage(content=user_message))

        try:
            full_response = ""
            tool_calls_made: list[str] = []

            while True:
                llm_with_tools = self.llm.bind_tools(CHAT_TOOLS)
                response = llm_with_tools.invoke(history)

                if hasattr(response, "tool_calls") and response.tool_calls:
                    for tc in response.tool_calls:
                        tool_name = tc.get("name") or ""
                        tool_input = tc.get("args") or {}
                        tool_id = tc.get("id") or str(len(history))

                        yield {
                            "type": "tool_call",
                            "tool": tool_name,
                            "input": tool_input,
                            "description": self._tool_description(tool_name),
                        }

                        tool_start = time.time()
                        try:
                            tool_output = execute_tool(
                                tool_name,
                                tool_input,
                                namespace=self.session.namespace,
                            )
                            success = True
                        except Exception as e:
                            tool_output = f"Tool error: {str(e)}"
                            success = False

                        tool_latency = int((time.time() - tool_start) * 1000)

                        self._save_message(
                            "tool_call",
                            f"Calling {tool_name}",
                            tool_name=tool_name,
                            tool_input=tool_input,
                            latency_ms=tool_latency,
                        )
                        tool_result_msg = self._save_message(
                            "tool_result",
                            (tool_output or "")[:500],
                            tool_name=tool_name,
                            tool_output=tool_output or "",
                            tool_success=success,
                            latency_ms=tool_latency,
                        )

                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "output": (tool_output or "")[:300],
                            "success": success,
                            "latency_ms": tool_latency,
                        }

                        history.append(
                            AIMessage(
                                content="",
                                tool_calls=[
                                    {
                                        "name": tool_name,
                                        "args": tool_input,
                                        "id": tool_id,
                                    }
                                ],
                            )
                        )
                        history.append(
                            ToolMessage(
                                content=tool_output or "",
                                tool_call_id=tool_id,
                            )
                        )
                        tool_calls_made.append(tool_name)

                    continue

                response_content = response.content or ""
                full_response = response_content

                words = response_content.split(" ")
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield {"type": "token", "content": chunk}

                break

            latency_ms = int((time.time() - start) * 1000)
            saved_msg = self._save_message(
                "assistant",
                full_response,
                latency_ms=latency_ms,
                tokens_used=len(full_response.split()),
            )

            yield {
                "type": "done",
                "message_id": saved_msg.id,
                "latency_ms": latency_ms,
                "tools_used": tool_calls_made,
            }

        except Exception as e:
            logger.error("Chat engine error: %s", e, exc_info=True)
            yield {"type": "error", "message": str(e)}
