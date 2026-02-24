"""ClusterConnection model for storing connected K8s cluster metadata."""
from django.db import models


class ClusterConnection(models.Model):
    """Stores metadata about a connected K8s cluster."""

    class ConnectionMethod(models.TextChoices):
        KUBECONFIG = "kubeconfig", "Kubeconfig File"
        IN_CLUSTER = "in_cluster", "In-Cluster (Pod)"
        CONTEXT = "context", "Kubeconfig Context"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONNECTED = "connected", "Connected"
        FAILED = "failed", "Failed"
        WATCHING = "watching", "Watching Events"

    name = models.CharField(max_length=255)
    connection_method = models.CharField(
        max_length=20, choices=ConnectionMethod.choices
    )
    kubeconfig_path = models.CharField(max_length=512, blank=True)
    context_name = models.CharField(max_length=255, blank=True)
    namespaces = models.JSONField(default=list)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    server_version = models.CharField(max_length=50, blank=True)
    node_count = models.IntegerField(default=0)
    last_connected = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"
