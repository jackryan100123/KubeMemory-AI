"""Pytest fixtures for KubeMemory backend tests."""
import os

import pytest
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("FERNET_KEY", "test-fernet-key-for-pytest-only!!!!")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def auth_client(api_client):
    User = get_user_model()
    user = User.objects.create_user(username="tester", password="testpass123")
    from apps.accounts.models import UserProfile

    UserProfile.objects.update_or_create(
        user=user, defaults={"role": UserProfile.Role.ADMIN}
    )
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client
