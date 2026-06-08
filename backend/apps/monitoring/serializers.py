"""DRF serializers for monitoring models."""
from rest_framework import serializers

from .models import TaskLog


class TaskLogSerializer(serializers.ModelSerializer):
    """Serializer for TaskLog list responses."""

    class Meta:
        model = TaskLog
        fields = [
            "id",
            "task_id",
            "task_name",
            "status",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields

    def validate_task_id(self, value: str) -> str:
        if not value or not str(value).strip():
            raise serializers.ValidationError("task_id cannot be empty.")
        return str(value).strip()[:255]
