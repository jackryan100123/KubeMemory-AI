"""Django app config for agents."""
from django.apps import AppConfig


class AgentsConfig(AppConfig):
    """Config for the agents app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.agents"
    verbose_name = "Agents"

    def ready(self) -> None:
        try:
            from apps.agents.ollama_health import verify_ollama_models

            verify_ollama_models()
        except Exception:
            pass
