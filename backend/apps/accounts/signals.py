"""Create UserProfile when a User is created."""
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created: bool, **kwargs) -> None:
    """Ensure every user has a profile; superusers default to admin."""
    if created:
        role = UserProfile.Role.ADMIN if instance.is_superuser else UserProfile.Role.VIEWER
        UserProfile.objects.create(user=instance, role=role)
    else:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                "role": UserProfile.Role.ADMIN if instance.is_superuser else UserProfile.Role.VIEWER,
            },
        )
