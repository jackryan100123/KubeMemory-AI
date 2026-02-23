"""Django app config for watcher."""
from django.apps import AppConfig


class WatcherConfig(AppConfig):
    """Config for the K8s watcher app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.watcher"
    verbose_name = "Watcher"
