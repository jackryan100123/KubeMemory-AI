"""API views for cluster connection: CRUD, test, connect, namespaces."""
import logging
from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .k8s_client import test_connection
from .models import ClusterConnection
from .serializers import ClusterConnectionSerializer

logger = logging.getLogger(__name__)


class ClusterConnectionViewSet(ModelViewSet):
    """CRUD + test, connect, namespaces for ClusterConnection."""

    queryset = ClusterConnection.objects.all()
    serializer_class = ClusterConnectionSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None) -> Response:
        """
        Test connectivity for this cluster. Uses kubeconfig path from model.
        Returns {connected, node_count, server_version, namespaces} or {connected: false, error}.
        """
        cluster = self.get_object()
        result = test_connection(
            connection_method=cluster.connection_method,
            kubeconfig_path=cluster.kubeconfig_path or "",
            context_name=cluster.context_name or "",
        )
        if result.get("connected"):
            cluster.status = ClusterConnection.Status.CONNECTED
            cluster.node_count = result.get("node_count", 0)
            cluster.server_version = (result.get("server_version") or "")[:50]
            cluster.last_connected = timezone.now()
            cluster.error_message = ""
            cluster.save(update_fields=["status", "node_count", "server_version", "last_connected", "error_message"])
        else:
            cluster.status = ClusterConnection.Status.FAILED
            cluster.error_message = result.get("error", "Unknown error")[:2000]
            cluster.save(update_fields=["status", "error_message"])
        return Response(result)

    @action(detail=True, methods=["post"])
    def connect(self, request, pk=None) -> Response:
        """
        Mark cluster as watching (user must start watcher with this cluster's config).
        Updates status to WATCHING and returns success.
        """
        cluster = self.get_object()
        cluster.status = ClusterConnection.Status.WATCHING
        cluster.last_connected = timezone.now()
        cluster.error_message = ""
        cluster.save(update_fields=["status", "last_connected", "error_message"])
        return Response({
            "status": "watching",
            "cluster_id": cluster.id,
            "name": cluster.name,
            "namespaces": cluster.namespaces,
        })

    @action(detail=True, methods=["get"])
    def namespaces(self, request, pk=None) -> Response:
        """
        List available namespaces in the cluster (from last successful test or cached).
        If not yet tested, runs test first and returns namespaces from that.
        """
        cluster = self.get_object()
        result = test_connection(
            connection_method=cluster.connection_method,
            kubeconfig_path=cluster.kubeconfig_path or "",
            context_name=cluster.context_name or "",
        )
        if result.get("connected"):
            return Response({"namespaces": result.get("namespaces", [])})
        return Response(
            {"error": result.get("error", "Connection failed"), "namespaces": []},
            status=status.HTTP_400_BAD_REQUEST,
        )
