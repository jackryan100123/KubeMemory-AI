"""DRF ViewSets for Incident, Fix, and ClusterPattern."""
from django.core.cache import cache
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

# Rate limit: max 10 fix submissions per incident per hour per IP
FIX_SUBMIT_RATE_LIMIT = 10
FIX_SUBMIT_WINDOW_SECONDS = 3600


def _get_client_ip(request):
    """Return client IP for rate limiting."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


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
        qs = Incident.objects.all().order_by("-occurred_at")
        if self.action != "list":
            return qs
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        occurred_after = self.request.query_params.get("occurred_after")
        if occurred_after:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(occurred_after)
            if dt:
                qs = qs.filter(occurred_at__gte=dt)
        return qs

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
    """Create Fix for an incident; triggers corrective RAG Celery task. Rate limited."""

    serializer_class = FixSerializer

    def create(self, request, incident_id: int):
        incident = Incident.objects.filter(pk=incident_id).first()
        if not incident:
            return Response(
                {"error": "Incident not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Rate limit: 10 fix submissions per incident per hour per IP
        ip = _get_client_ip(request)
        cache_key = f"fix_submit:{incident_id}:{ip}"
        count = cache.get(cache_key) or 0
        if count >= FIX_SUBMIT_RATE_LIMIT:
            return Response(
                {"error": f"Rate limit exceeded. Max {FIX_SUBMIT_RATE_LIMIT} fix submissions per incident per hour."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        cache.set(cache_key, count + 1, timeout=FIX_SUBMIT_WINDOW_SECONDS)

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
