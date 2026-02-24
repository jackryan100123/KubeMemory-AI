"""URL routing for incidents API. Prefix: api/ (from main urls)."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FixViewSet, IncidentViewSet

router = DefaultRouter()
router.register(r"incidents", IncidentViewSet, basename="incident")

# Literal paths first so they are not matched by router's incidents/<pk>/
# (patterns/ is registered in config/urls.py for reliable 200)
urlpatterns = [
    path(
        "incidents/<int:incident_id>/fixes/",
        FixViewSet.as_view({"post": "create"}),
        name="incident-fixes",
    ),
    path("", include(router.urls)),
]
