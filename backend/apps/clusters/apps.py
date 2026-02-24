"""Django app config for clusters."""
from django.apps import AppConfig


class ClustersConfig(AppConfig):
    """AppConfig for clusters app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clusters"
    verbose_name = "Cluster Connections"
