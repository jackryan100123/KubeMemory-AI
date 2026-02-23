"""URL configuration for KubeMemory."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.incidents.urls")),
    path("api/", include("apps.memory.urls")),
    path("api/", include("apps.agents.urls")),
]
