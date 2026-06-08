"""URL configuration for KubeMemory."""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.incidents.views import ClusterPatternViewSet
from config.health_views import health
from config.status_views import system_status

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="api-health"),
    path("api/status/", system_status, name="api-status"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Explicit path so it always matches (no conflict with router)
    path(
        "api/incidents/patterns/",
        ClusterPatternViewSet.as_view({"get": "list"}),
        name="incident-patterns",
    ),
    # Agents and memory before incidents so /api/agents/* and /api/memory/* match
    path("api/", include("apps.monitoring.urls")),
    path("api/", include("apps.agents.urls")),
    path("api/", include("apps.memory.urls")),
    path("api/", include("apps.clusters.urls")),
    path("api/", include("apps.incidents.urls")),
    path("api/chat/", include("apps.chat.urls")),
]
