"""
KubeMemory MCP Server — Production Grade.

Exposes 7 tools to Claude Desktop and any MCP-compatible client.
All tools use the same backend as the in-app chat (apps.chat.tools).
Includes session management so Claude maintains context across turns.

Setup in claude_desktop_config.json:
{
  "mcpServers": {
    "kubememory": {
      "command": "python",
      "args": ["-m", "apps.mcp_server.server"],
      "env": {
        "DJANGO_SETTINGS_MODULE": "config.settings.dev",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "<from your .env>",
        "CHROMA_PERSIST_DIR": "/path/to/chroma_data"
      }
    }
  }
}

SECURITY: Never commit claude_desktop_config.json.
          Add it to .gitignore immediately.
"""
import asyncio
import logging
import os
import sys

# Bootstrap Django: backend/apps/mcp_server -> backend
_backend_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp import types

try:
    from mcp.server.context import ServerRequestContext
except ImportError:
    from mcp.server.models import ServerRequestContext  # type: ignore

from apps.chat.tools import execute_tool

logger = logging.getLogger("apps.mcp_server")

# MCP Tool schemas — must match apps/chat/tools.py exactly
MCP_TOOL_SCHEMAS = [
    Tool(
        name="search_incidents",
        description=(
            "Semantic search over this cluster's complete incident history. "
            "Ask in natural language: 'OOMKill incidents in production', "
            "'payment service crashes after deploy', 'database errors last week'. "
            "Returns ranked list of matching incidents with dates and fixes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "namespace": {"type": "string", "description": "Filter by namespace (optional)"},
                "limit": {"type": "integer", "description": "Max results (default 5)", "default": 5},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="analyze_pod",
        description=(
            "Deep AI analysis of a specific pod using the full LangGraph 3-agent pipeline. "
            "Retrieves similar incidents from ChromaDB, traverses Neo4j causal graph, "
            "then synthesises a grounded recommendation via Ollama. "
            "Use when engineer asks WHY a pod is failing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "pod_name": {"type": "string", "description": "Pod name"},
                "namespace": {"type": "string", "description": "K8s namespace"},
                "incident_type": {"type": "string", "description": "Incident type (optional)"},
            },
            "required": ["pod_name", "namespace"],
        },
    ),
    Tool(
        name="get_blast_radius",
        description=(
            "Find which services historically crash within 5 minutes when a specific pod fails. "
            "Based on Neo4j co-occurrence graph built from actual cluster history. "
            "Use when engineer needs to know the blast radius before an incident spreads."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "pod_name": {"type": "string"},
                "namespace": {"type": "string"},
            },
            "required": ["pod_name", "namespace"],
        },
    ),
    Tool(
        name="get_patterns",
        description=(
            "Get the top recurring incident patterns in this cluster. "
            "Shows which pods fail most often, fix success rates, and what worked. "
            "Use for cluster health overview or 'what keeps breaking' questions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Filter by namespace (optional)"},
                "limit": {"type": "integer", "default": 8},
            },
        },
    ),
    Tool(
        name="get_pod_timeline",
        description=(
            "Get the full chronological incident history for a specific pod. "
            "Shows all past incidents, their severity, status, and what fixes were applied. "
            "Use when engineer asks 'what's been happening with X pod'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "pod_name": {"type": "string"},
                "namespace": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["pod_name", "namespace"],
        },
    ),
    Tool(
        name="risk_check",
        description=(
            "Pre-deploy risk assessment. Answers: 'Is it safe to deploy right now?' "
            "Checks open incidents, blast radius stability, and deploy-crash history "
            "from Neo4j. Returns risk level (low/medium/high) with specific reasons."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "Service to deploy"},
                "namespace": {"type": "string"},
            },
            "required": ["service_name", "namespace"],
        },
    ),
    Tool(
        name="get_graph_context",
        description=(
            "Get a summary of the Neo4j knowledge graph for a namespace. "
            "Shows pods, services, incident counts, and causal relationships. "
            "Use for cluster topology overview questions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
            },
            "required": ["namespace"],
        },
    ),
]


async def handle_list_tools(
    ctx: ServerRequestContext,
    params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=MCP_TOOL_SCHEMAS)


async def handle_call_tool(
    ctx: ServerRequestContext,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}
    logger.info("MCP tool call: %s args=%s", name, arguments)

    try:
        valid_tools = {t.name for t in MCP_TOOL_SCHEMAS}
        if name not in valid_tools:
            return types.CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}. Available: {list(valid_tools)}",
                    )
                ]
            )

        def do_call() -> str:
            return execute_tool(name, arguments, namespace=None)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, do_call)
        logger.info("MCP tool %s completed: %s chars", name, len(result))
        return types.CallToolResult(
            content=[TextContent(type="text", text=result)]
        )
    except ValueError as e:
        logger.warning("MCP tool %s validation error: %s", name, e)
        return types.CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Invalid input for {name}: {str(e)}",
                )
            ]
        )
    except Exception as e:
        logger.error("MCP tool %s failed: %s", name, e, exc_info=True)
        return types.CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Error running {name}: {str(e)}\n"
                    "Check that KubeMemory services are running.",
                )
            ]
        )


server = Server(
    "kubememory",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
