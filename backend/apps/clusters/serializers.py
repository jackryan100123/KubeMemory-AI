"""DRF serializers for ClusterConnection."""
from rest_framework import serializers

from .models import ClusterConnection


VALID_CONNECTION_METHODS = {c.value for c in ClusterConnection.ConnectionMethod}


class ClusterConnectionSerializer(serializers.ModelSerializer):
    """Serializer for ClusterConnection; validates required fields."""

    class Meta:
        model = ClusterConnection
        fields = [
            "id",
            "name",
            "connection_method",
            "kubeconfig_path",
            "context_name",
            "namespaces",
            "status",
            "server_version",
            "node_count",
            "last_connected",
            "error_message",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "server_version",
            "node_count",
            "last_connected",
            "error_message",
            "created_at",
        ]
        extra_kwargs = {
            "kubeconfig_path": {"allow_blank": True, "required": False, "default": ""},
            "context_name": {"allow_blank": True, "required": False, "default": ""},
            "namespaces": {"required": False, "default": list},
        }

    def validate_name(self, value: str) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise serializers.ValidationError("Name cannot be empty.")
        return (value or "").strip()[:255]

    def validate_connection_method(self, value: str) -> str:
        if not value or value not in VALID_CONNECTION_METHODS:
            raise serializers.ValidationError(
                f"connection_method must be one of: {', '.join(sorted(VALID_CONNECTION_METHODS))}."
            )
        return value.strip()

    def validate_namespaces(self, value: list) -> list:
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Namespaces must be a list.")
        return [str(ns).strip() for ns in value if str(ns).strip()]
