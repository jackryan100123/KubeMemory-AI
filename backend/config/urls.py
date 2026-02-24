"""URL configuration for KubeMemory."""
from django.contrib import admin
from django.urls import include, path

from apps.incidents.views import ClusterPatternViewSet

urlpatterns = [
    path("admin/", admin.site.urls),
    # Explicit path so it always matches (no conflict with router)
    path(
        "api/incidents/patterns/",
        ClusterPatternViewSet.as_view({"get": "list"}),
        name="incident-patterns",
    ),
    # Agents and memory before incidents so /api/agents/* and /api/memory/* match
    path("api/", include("apps.agents.urls")),
    path("api/", include("apps.memory.urls")),
    path("api/", include("apps.clusters.urls")),
    path("api/", include("apps.incidents.urls")),
]
