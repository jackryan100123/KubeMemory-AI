"""Django admin for Incident, Fix, and ClusterPattern."""
from django.contrib import admin
from .models import ClusterPattern, Fix, Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "pod_name",
        "namespace",
        "incident_type",
        "severity",
        "status",
        "occurred_at",
    ]
    list_filter = ["severity", "status", "incident_type", "namespace"]
    search_fields = ["pod_name", "namespace", "description"]
    ordering = ["-occurred_at"]


@admin.register(Fix)
class FixAdmin(admin.ModelAdmin):
    list_display = ["id", "incident", "applied_by", "worked", "ai_suggested", "created_at"]
    list_filter = ["worked", "ai_suggested"]
    search_fields = ["description", "applied_by"]


@admin.register(ClusterPattern)
class ClusterPatternAdmin(admin.ModelAdmin):
    list_display = ["id", "pod_name", "namespace", "incident_type", "frequency", "last_seen"]
    list_filter = ["incident_type", "namespace"]
    search_fields = ["pod_name", "namespace"]
