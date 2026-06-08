"""Monitoring API views."""
from rest_framework import generics

from .models import TaskLog
from .serializers import TaskLogSerializer


class TaskLogListView(generics.ListAPIView):
    """Return the last 50 failed or retried Celery tasks."""

    serializer_class = TaskLogSerializer

    def get_queryset(self):
        return TaskLog.objects.filter(
            status__in=[TaskLog.Status.FAILURE, TaskLog.Status.RETRY]
        ).order_by("-created_at")[:50]
