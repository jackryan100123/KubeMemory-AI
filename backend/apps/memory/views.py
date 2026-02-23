"""Memory API views: semantic search, graph data, patterns, blast radius."""
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .graph_builder import KubeGraphBuilder
from .vector_store import IncidentVectorStore


class MemorySearchView(APIView):
    """GET /api/memory/search/?q=<query>&namespace=<ns> — similar past incidents."""

    def get(self, request: Request) -> Response:
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        namespace = request.query_params.get("namespace") or None
        n_results = min(int(request.query_params.get("n", 5)), 20)
        store = IncidentVectorStore()
        results = store.search_similar(q, n_results=n_results, filter_namespace=namespace)
        return Response({"results": results})


class MemoryGraphView(APIView):
    """GET /api/memory/graph/?namespace=<ns> — nodes and links for React Force Graph."""

    def get(self, request: Request) -> Response:
        namespace = request.query_params.get("namespace") or "default"
        graph = KubeGraphBuilder()
        try:
            data = graph.get_graph_data_for_namespace(namespace)
            return Response(data)
        finally:
            graph.close()


class MemoryPatternsView(APIView):
    """GET /api/memory/patterns/ — deploy-to-crash correlation across cluster."""

    def get(self, request: Request) -> Response:
        graph = KubeGraphBuilder()
        try:
            data = graph.find_deploy_to_crash_correlation()
            return Response({"patterns": data})
        finally:
            graph.close()


class MemoryBlastRadiusView(APIView):
    """GET /api/memory/blast-radius/?pod=<name>&namespace=<ns> — co-occurring incidents."""

    def get(self, request: Request) -> Response:
        pod = request.query_params.get("pod", "").strip()
        namespace = request.query_params.get("namespace") or "default"
        if not pod:
            return Response(
                {"error": "Query parameter 'pod' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        graph = KubeGraphBuilder()
        try:
            data = graph.find_blast_radius(pod, namespace)
            return Response({"blast_radius": data})
        finally:
            graph.close()
