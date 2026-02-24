"""
Django management command: run_mcp.
Runs the MCP server for development/testing without Claude Desktop.

Usage: python manage.py run_mcp
"""
import asyncio
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the KubeMemory MCP server (stdio transport for Claude Desktop)"

    def handle(self, *args, **options):
        from apps.mcp_server.server import main
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            sys.exit(0)
