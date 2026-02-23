"""Django app config for memory."""
from django.apps import AppConfig


class MemoryConfig(AppConfig):
    """Config for the memory app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.memory"
    verbose_name = "Memory"
