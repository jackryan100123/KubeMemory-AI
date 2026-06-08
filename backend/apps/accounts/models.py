"""UserProfile model linking Django User to KubeMemory RBAC roles."""
from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Per-user role for API and cluster mutation permissions."""

    class Role(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        OPERATOR = "operator", "Operator"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"
