"""WebSocket URL routing for KubeMemory."""
from django.urls import re_path

from apps.chat.consumers import ChatConsumer
from .consumers import IncidentConsumer

websocket_urlpatterns = [
    re_path(r"^ws/incidents/$", IncidentConsumer.as_asgi()),
    re_path(r"^ws/chat/$", ChatConsumer.as_asgi()),
]
