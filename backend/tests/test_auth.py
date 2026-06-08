"""JWT authentication tests."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_incidents_unauthenticated_returns_401(api_client) -> None:
    url = reverse("incident-list")
    response = api_client.get(url)
    assert response.status_code == 401


@pytest.mark.django_db
def test_incidents_authenticated_returns_200(auth_client) -> None:
    url = reverse("incident-list")
    response = auth_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_health_public(api_client) -> None:
    response = api_client.get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
