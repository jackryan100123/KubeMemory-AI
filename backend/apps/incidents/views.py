"""DRF ViewSets for Incident, Fix, and ClusterPattern."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ClusterPattern, Fix, Incident
from .serializers import (
    ClusterPatternSerializer,
    FixSerializer,
    IncidentDetailSerializer,
    IncidentListSerializer,
)
from .tasks import update_corrective_rag_task


class IncidentViewSet(viewsets.ModelViewSet):
    """List, retrieve, partial_update (status changes) for Incident."""

    queryset = Incident.objects.all()
    http_method_names = ["get", "head", "options", "patch"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return IncidentDetailSerializer
        return IncidentListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context

    def get_queryset(self):
        return Incident.objects.all().order_by("-occurred_at")

    def partial_update(self, request, *args, **kwargs):
        """Allow partial update (e.g. status only)."""
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class FixViewSet(viewsets.GenericViewSet):
    """Create Fix for an incident; triggers corrective RAG Celery task."""

    serializer_class = FixSerializer

    def create(self, request, incident_id: int):
        incident = Incident.objects.filter(pk=incident_id).first()
        if not incident:
            return Response(
                {"error": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = {**request.data, "incident": incident_id}
        serializer = FixSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        fix = serializer.save()
        update_corrective_rag_task.delay(fix.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ClusterPatternViewSet(viewsets.ReadOnlyModelViewSet):
    """List only for ClusterPattern."""

    queryset = ClusterPattern.objects.all().order_by("-frequency")
    serializer_class = ClusterPatternSerializer

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
