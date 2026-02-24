"""Django app config for chat."""
from django.apps import AppConfig


class ChatConfig(AppConfig):
    """Config for the chat (cluster assistant) app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat"
    verbose_name = "Chat"
