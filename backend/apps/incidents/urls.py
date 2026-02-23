"""URL routing for incidents API. Prefix: incidents/."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ClusterPatternViewSet, FixViewSet, IncidentViewSet

router = DefaultRouter()
router.register(r"incidents", IncidentViewSet, basename="incident")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "incidents/<int:incident_id>/fixes/",
        FixViewSet.as_view({"post": "create"}),
        name="incident-fixes",
    ),
    path(
        "incidents/patterns/",
        ClusterPatternViewSet.as_view({"get": "list"}),
        name="incident-patterns",
    ),
]
