"""
Create or update a dev admin user from environment variables.
Usage: python manage.py ensure_dev_admin
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    """Ensure DEV_ADMIN_USERNAME / DEV_ADMIN_PASSWORD exist with admin role."""

    help = "Create dev admin user from DEV_ADMIN_USERNAME and DEV_ADMIN_PASSWORD env vars"

    def handle(self, *args, **options) -> None:
        username = os.environ.get("DEV_ADMIN_USERNAME", "").strip()
        password = os.environ.get("DEV_ADMIN_PASSWORD", "").strip()
        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Skip: set DEV_ADMIN_USERNAME and DEV_ADMIN_PASSWORD in .env"
                )
            )
            return
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": True, "is_superuser": True},
        )
        if not created:
            user.is_staff = True
            user.is_superuser = True
        user.set_password(password)
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["role"])
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin user '{username}'"))
