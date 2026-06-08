"""Django app config for accounts (UserProfile RBAC)."""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Register accounts app and signal handlers."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self) -> None:
        import apps.accounts.signals  # noqa: F401
