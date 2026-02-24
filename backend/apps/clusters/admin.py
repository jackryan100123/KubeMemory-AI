"""Admin for ClusterConnection."""
from django.contrib import admin
from .models import ClusterConnection


@admin.register(ClusterConnection)
class ClusterConnectionAdmin(admin.ModelAdmin):
    """Admin for ClusterConnection (read-only for sensitive data)."""

    list_display = ["name", "connection_method", "status", "node_count", "created_at"]
    list_filter = ["status", "connection_method"]
    readonly_fields = [
        "status",
        "server_version",
        "node_count",
        "last_connected",
        "error_message",
        "created_at",
    ]
