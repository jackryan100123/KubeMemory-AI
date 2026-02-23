"""WebSocket URL routing for KubeMemory."""
from django.urls import re_path

from .consumers import IncidentConsumer

websocket_urlpatterns = [
    re_path(r"^ws/incidents/$", IncidentConsumer.as_asgi()),
]
