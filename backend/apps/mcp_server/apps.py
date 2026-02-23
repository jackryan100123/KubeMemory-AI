"""Django app config for MCP server."""
from django.apps import AppConfig


class McpServerConfig(AppConfig):
    """Config for the MCP server app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mcp_server"
    verbose_name = "MCP Server"
