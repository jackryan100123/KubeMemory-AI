"""DRF serializers for Incident, Fix, and ClusterPattern with explicit validation."""
from rest_framework import serializers

from .models import ClusterPattern, Fix, Incident


class FixSerializer(serializers.ModelSerializer):
    """Serializer for Fix; validates applied_by and description."""

    class Meta:
        model = Fix
        fields = [
            "id",
            "incident",
            "description",
            "applied_by",
            "worked",
            "ai_suggested",
            "correction_of",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_description(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value.strip()

    def validate_applied_by(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("Applied by cannot be empty.")
        return value.strip()[:255]


class IncidentListSerializer(serializers.ModelSerializer):
    """List serializer for Incident; no nested fixes."""

    class Meta:
        model = Incident
        fields = [
            "id",
            "pod_name",
            "namespace",
            "node_name",
            "service_name",
            "incident_type",
            "severity",
            "status",
            "description",
            "occurred_at",
            "resolved_at",
            "created_at",
        ]


class IncidentDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Incident with nested fixes."""

    fixes = FixSerializer(many=True, read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "pod_name",
            "namespace",
            "node_name",
            "service_name",
            "incident_type",
            "severity",
            "status",
            "description",
            "raw_logs",
            "ai_analysis",
            "chroma_id",
            "neo4j_id",
            "occurred_at",
            "resolved_at",
            "created_at",
            "updated_at",
            "fixes",
        ]

    def validate_severity(self, value: str) -> str:
        if value not in dict(Incident.Severity.choices):
            raise serializers.ValidationError(
                f"Invalid severity. Must be one of: {list(dict(Incident.Severity.choices).keys())}"
            )
        return value

    def validate_status(self, value: str) -> str:
        if value not in dict(Incident.Status.choices):
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {list(dict(Incident.Status.choices).keys())}"
            )
        return value


class ClusterPatternSerializer(serializers.ModelSerializer):
    """Serializer for ClusterPattern (list only)."""

    class Meta:
        model = ClusterPattern
        fields = [
            "id",
            "pod_name",
            "namespace",
            "incident_type",
            "frequency",
            "best_fix",
            "fix_success_rate",
            "last_seen",
        ]
