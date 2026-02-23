"""URL routing for agents app (Phase 3)."""
from django.urls import path

from . import views

urlpatterns = [
    path("agents/analyze/<int:incident_id>/", views.trigger_analyze),
    path("agents/analysis/<int:incident_id>/", views.get_analysis),
    path("agents/status/", views.pipeline_status),
]
