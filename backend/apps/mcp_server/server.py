"""
KubeMemory MCP Server.
Exposes cluster memory tools to Claude Desktop and any MCP-compatible LLM.

To use with Claude Desktop, add to claude_desktop_config.json:
{
  "mcpServers": {
    "kubememory": {
      "command": "python",
      "args": ["/path/to/kubememory/backend/apps/mcp_server/server.py"],
      "env": {
        "DJANGO_SETTINGS_MODULE": "config.settings.dev",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password",
        "CHROMA_PERSIST_DIR": "/path/to/chroma_data",
        "OLLAMA_BASE_URL": "http://localhost:11434"
      }
    }
  }
}

NOTE: Never commit claude_desktop_config.json with real passwords.
Always reference it in .gitignore.
"""
import asyncio
import os
import sys
from typing import Any

# Add backend to Python path (backend/apps/mcp_server -> backend)
_backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

from apps.mcp_server.tools import execute_tool, get_ollama_tools


def _ollama_to_mcp_tools() -> list:
    """Convert Ollama tool definitions to MCP Tool list."""
    ollama = get_ollama_tools()
    return [
        Tool(
            name=t["function"]["name"],
            description=t["function"].get("description", ""),
            inputSchema=t["function"].get("parameters", {"type": "object", "properties": {}}),
        )
        for t in ollama
    ]


TOOLS = _ollama_to_mcp_tools()


async def handle_list_tools(
    ctx: ServerRequestContext,
    params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def handle_call_tool(
    ctx: ServerRequestContext,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}

    def do_call() -> str:
        return execute_tool(name, arguments)

    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, do_call)
    return types.CallToolResult(content=[TextContent(type="text", text=text)])


async def main() -> None:
    server = Server(
        name="kubememory",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
