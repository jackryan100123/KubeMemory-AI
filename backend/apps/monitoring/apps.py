"""Django app config for monitoring."""
from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    """Register monitoring app and Celery signal handlers."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.monitoring"
    label = "monitoring"

    def ready(self) -> None:
        import apps.monitoring.signals  # noqa: F401
