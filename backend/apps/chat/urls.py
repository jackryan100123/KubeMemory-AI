"""Chat API URL configuration."""
from django.urls import path

from .views import (
    ChatCommandsView,
    ChatMessageView,
    ChatSessionDetailView,
    ChatSessionListView,
    ChatSuggestionsView,
)

urlpatterns = [
    path("sessions/", ChatSessionListView.as_view()),
    path("sessions/<uuid:session_id>/", ChatSessionDetailView.as_view()),
    path(
        "sessions/<uuid:session_id>/message/",
        ChatMessageView.as_view(),
    ),
    path("suggestions/", ChatSuggestionsView.as_view()),
    path("commands/", ChatCommandsView.as_view()),
]
