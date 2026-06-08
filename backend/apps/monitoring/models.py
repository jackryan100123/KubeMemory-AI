"""TaskLog model for Celery task failure visibility."""
from django.db import models


class TaskLog(models.Model):
    """Record of Celery task execution outcomes (especially failures)."""

    class Status(models.TextChoices):
        FAILURE = "failure", "Failure"
        RETRY = "retry", "Retry"
        SUCCESS = "success", "Success"

    task_id = models.CharField(max_length=255, db_index=True)
    task_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task_name} [{self.status}] {self.task_id}"


class NotificationConfig(models.Model):
    """Webhook or Slack notification sink for incidents."""

    class NotificationType(models.TextChoices):
        SLACK = "slack", "Slack"
        WEBHOOK = "webhook", "Webhook"

    type = models.CharField(max_length=20, choices=NotificationType.choices)
    url = models.URLField(max_length=512)
    min_severity = models.CharField(
        max_length=20,
        default="high",
        help_text="Minimum severity to trigger: low, medium, high, critical",
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.type} ({self.min_severity}+) {'on' if self.enabled else 'off'}"
