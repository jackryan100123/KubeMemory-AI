"""API views for cluster connection: CRUD, test, connect, namespaces."""
import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .k8s_client import test_connection
from .models import ClusterConnection
from .serializers import ClusterConnectionSerializer
from .watcher_manager import write_cluster_kubeconfig, start_watcher, stop_watcher, watcher_status

logger = logging.getLogger(__name__)


class ClusterConnectionViewSet(ModelViewSet):
    """CRUD + test, connect, namespaces for ClusterConnection."""

    queryset = ClusterConnection.objects.all()
    serializer_class = ClusterConnectionSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs) -> Response:
        """Create cluster; if kubeconfig_content is provided, save to file and set kubeconfig_path."""
        content = (request.data.get("kubeconfig_content") or "").strip()
        use_docker_host = request.data.get("use_docker_host", False) in (True, "true", "1")
        data = {k: v for k, v in request.data.items() if k not in ("kubeconfig_content", "use_docker_host")}
        if content and not data.get("kubeconfig_path"):
            data["kubeconfig_path"] = ""  # will set after write
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        cluster = serializer.instance
        if content:
            try:
                path = write_cluster_kubeconfig(cluster.id, content, use_docker_host=use_docker_host)
                cluster.kubeconfig_path = str(path)
                cluster.save(update_fields=["kubeconfig_path"])
            except Exception as e:
                logger.exception("Failed to write kubeconfig for cluster %s: %s", cluster.id, e)
                return Response(
                    {"error": f"Failed to save kubeconfig: {e}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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
        Mark cluster as watching and start the watcher subprocess (no manual step).
        Updates status to WATCHING and returns success.
        """
        cluster = self.get_object()
        cluster.status = ClusterConnection.Status.WATCHING
        cluster.last_connected = timezone.now()
        cluster.error_message = ""
        cluster.save(update_fields=["status", "last_connected", "error_message"])
        namespaces = cluster.namespaces or ["default"]
        result = start_watcher(cluster.id, namespaces)
        if not result.get("started") and result.get("error"):
            return Response(
                {"status": "watching", "cluster_id": cluster.id, "name": cluster.name, "namespaces": cluster.namespaces, "watcher_started": False, "watcher_error": result["error"]},
                status=status.HTTP_200_OK,
            )
        return Response({
            "status": "watching",
            "cluster_id": cluster.id,
            "name": cluster.name,
            "namespaces": cluster.namespaces,
            "watcher_started": result.get("started", False),
        })

    @action(detail=True, methods=["post"], url_path="start-watcher")
    def start_watcher_action(self, request, pk=None) -> Response:
        """Start or restart the watcher for this cluster (activates its kubeconfig)."""
        cluster = self.get_object()
        namespaces = cluster.namespaces or ["default"]
        result = start_watcher(cluster.id, namespaces)
        if result.get("started"):
            return Response({"started": True})
        return Response(
            {"started": False, "error": result.get("error", "Failed to start watcher")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"], url_path="watcher/stop")
    def watcher_stop(self, request) -> Response:
        """Stop the in-process watcher."""
        return Response(stop_watcher())

    @action(detail=False, methods=["get"], url_path="watcher/status")
    def watcher_status_action(self, request) -> Response:
        """Return {running: bool, cluster_id?: int}."""
        return Response(watcher_status())

    @action(detail=False, methods=["get"], url_path="security-info")
    def security_info(self, request) -> Response:
        """
        Return what the app does with the cluster (read-only, no secrets, etc.)
        for display in the UI so users see security and transparency.
        """
        return Response({
            "title": "Cluster security & what we access",
            "read_only": True,
            "we_never": [
                "Modify or delete any resource in your cluster",
                "Create pods, deployments, or services",
                "Access secrets, ConfigMaps, or credentials",
                "Require cluster-admin or write permissions",
                "Store your kubeconfig content in our database (only file path or file on disk)",
            ],
            "we_do": [
                "List and watch Events, Pods, Namespaces (read-only)",
                "Read pod logs when an incident is detected (for context only)",
                "Store incident metadata (pod name, namespace, type, description) and embeddings in our database",
                "Use your kubeconfig only to connect to the API server; it is stored in a file on the server (or you paste it once and we write to a file). We never log or expose kubeconfig content.",
            ],
            "recommendations": [
                "Use a dedicated service account with minimal read-only RBAC (list/watch events, get/list pods and namespaces, read pod logs).",
                "Run the app in your own environment; we do not send cluster data to third parties.",
            ],
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
