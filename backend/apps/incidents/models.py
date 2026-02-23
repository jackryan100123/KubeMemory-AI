"""Incident, Fix, and ClusterPattern models for KubeMemory."""
from django.db import models


class Incident(models.Model):
    """Represents a single Kubernetes cluster incident."""

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INVESTIGATING = "investigating", "Investigating"
        RESOLVED = "resolved", "Resolved"

    class IncidentType(models.TextChoices):
        CRASH_LOOP = "CrashLoopBackOff", "CrashLoopBackOff"
        OOM_KILL = "OOMKill", "OOMKill"
        NODE_PRESSURE = "NodePressure", "NodePressure"
        IMAGE_PULL = "ImagePullBackOff", "ImagePullBackOff"
        EVICTED = "Evicted", "Evicted"
        PENDING = "Pending", "Pending"
        UNKNOWN = "Unknown", "Unknown"

    pod_name = models.CharField(max_length=255, db_index=True)
    namespace = models.CharField(max_length=255, db_index=True)
    node_name = models.CharField(max_length=255, blank=True)
    service_name = models.CharField(max_length=255, blank=True, db_index=True)
    incident_type = models.CharField(max_length=50, choices=IncidentType.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    description = models.TextField()
    raw_logs = models.TextField(blank=True)
    ai_analysis = models.TextField(blank=True)
    chroma_id = models.CharField(max_length=255, blank=True)
    neo4j_id = models.CharField(max_length=255, blank=True)
    occurred_at = models.DateTimeField(db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at"]

    def __str__(self) -> str:
        return f"{self.incident_type} — {self.pod_name} ({self.namespace})"


class Fix(models.Model):
    """A fix applied to resolve an incident. Feeds the Corrective RAG loop."""

    incident = models.ForeignKey(
        Incident, on_delete=models.CASCADE, related_name="fixes"
    )
    description = models.TextField()
    applied_by = models.CharField(max_length=255)
    worked = models.BooleanField(default=False)
    ai_suggested = models.BooleanField(default=False)
    correction_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "✓" if self.worked else "✗"
        return f"{status} Fix for {self.incident.pod_name} by {self.applied_by}"


class ClusterPattern(models.Model):
    """Aggregated incident patterns derived from graph analysis."""

    pod_name = models.CharField(max_length=255)
    namespace = models.CharField(max_length=255)
    incident_type = models.CharField(max_length=50)
    frequency = models.IntegerField(default=0)
    best_fix = models.TextField(blank=True)
    fix_success_rate = models.FloatField(default=0.0)
    last_seen = models.DateTimeField()

    class Meta:
        ordering = ["-frequency"]
        unique_together = [("pod_name", "namespace", "incident_type")]

    def __str__(self) -> str:
        return f"{self.incident_type} on {self.pod_name} x{self.frequency}"
