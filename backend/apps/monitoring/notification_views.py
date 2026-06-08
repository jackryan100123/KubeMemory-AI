"""CRUD API for notification configuration."""
from rest_framework import viewsets

from .models import NotificationConfig
from .notification_serializers import NotificationConfigSerializer


class NotificationConfigViewSet(viewsets.ModelViewSet):
    """Manage Slack/webhook notification sinks."""

    queryset = NotificationConfig.objects.all()
    serializer_class = NotificationConfigSerializer
