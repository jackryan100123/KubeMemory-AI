"""DRF serializers for ClusterConnection."""
from rest_framework import serializers

from .models import ClusterConnection


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

    def validate_name(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()[:255]

    def validate_namespaces(self, value: list) -> list:
        if not isinstance(value, list):
            raise serializers.ValidationError("Namespaces must be a list.")
        return [str(ns).strip() for ns in value if str(ns).strip()]
