"""DRF serializers for NotificationConfig."""
from rest_framework import serializers

from .models import NotificationConfig

VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_TYPES = {c.value for c in NotificationConfig.NotificationType}


class NotificationConfigSerializer(serializers.ModelSerializer):
    """CRUD serializer for notification sinks."""

    class Meta:
        model = NotificationConfig
        fields = ["id", "type", "url", "min_severity", "enabled", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_type(self, value: str) -> str:
        if value not in VALID_TYPES:
            raise serializers.ValidationError(f"type must be one of: {sorted(VALID_TYPES)}")
        return value

    def validate_min_severity(self, value: str) -> str:
        if value not in VALID_SEVERITIES:
            raise serializers.ValidationError(
                f"min_severity must be one of: {sorted(VALID_SEVERITIES)}"
            )
        return value

    def validate_url(self, value: str) -> str:
        if not value or not str(value).strip():
            raise serializers.ValidationError("url cannot be empty.")
        return str(value).strip()
