"""URL routing for agents app (Phase 3 + Phase 4.5)."""
from django.urls import path

from . import views

urlpatterns = [
    path("agents/analyze/<int:incident_id>/", views.trigger_analyze),
    path("agents/analysis/<int:incident_id>/", views.get_analysis),
    path("agents/status/", views.pipeline_status),
    path("agents/runbook/<int:incident_id>/", views.generate_runbook),
    path("agents/risk-check/", views.risk_check),
]
