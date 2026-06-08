"""Admin for monitoring models."""
from django.contrib import admin

from .models import NotificationConfig, TaskLog


@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    """Browse Celery task logs."""

    list_display = ("task_name", "status", "task_id", "created_at")
    list_filter = ("status", "task_name")
    search_fields = ("task_id", "error_message")


@admin.register(NotificationConfig)
class NotificationConfigAdmin(admin.ModelAdmin):
    """Manage notification sinks."""

    list_display = ("type", "min_severity", "enabled", "created_at")
