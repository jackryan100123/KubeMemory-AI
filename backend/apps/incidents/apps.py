"""Django app config for incidents."""
from django.apps import AppConfig


class IncidentsConfig(AppConfig):
    """Config for the incidents app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.incidents"
    verbose_name = "Incidents"
