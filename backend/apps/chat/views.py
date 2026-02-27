"""
Chat API views.
POST /api/chat/sessions/              → create session
GET  /api/chat/sessions/              → list sessions
GET  /api/chat/sessions/{id}/         → session detail + messages
DELETE /api/chat/sessions/{id}/       → delete session
POST /api/chat/sessions/{id}/message/ → send message (SSE streaming)
GET  /api/chat/suggestions/?ns=<ns>   → context-aware suggested questions
GET  /api/chat/commands/              → slash command list
"""
import json
import logging

from django.db import transaction
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .engine import ChatEngine
from .models import ChatSession
from .serializers import ChatSessionListSerializer, ChatSessionSerializer

logger = logging.getLogger(__name__)


class ChatSessionListView(APIView):
    """List or create chat sessions. DELETE with ?all=1 clears all sessions."""

    def get(self, request):
        sessions = list(ChatSession.objects.order_by("-updated_at")[:20])
        ids = [str(s.id) for s in sessions]
        total = ChatSession.objects.count()
        logger.info("[chat] GET /sessions/ list count=%s total_in_db=%s ids=%s", len(sessions), total, ids[:5])
        resp = Response(ChatSessionListSerializer(sessions, many=True).data)
        resp["Cache-Control"] = "no-store, no-cache, must-revalidate"
        resp["X-Chat-Total-In-DB"] = str(total)
        return resp

    def delete(self, request):
        if request.query_params.get("all") != "1":
            return Response(
                {"error": "Use ?all=1 to confirm clearing all chat sessions"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            count, _ = ChatSession.objects.all().delete()
        logger.info("[chat] DELETE /sessions/?all=1 cleared %s sessions", count)
        return Response(
            {"deleted": count},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        namespace = request.data.get("namespace", "all")
        now = timezone.now()
        default_title = f"New chat ({now.strftime('%b %d, %H:%M')})"
        session = ChatSession.objects.create(namespace=namespace, title=default_title)
        logger.info("[chat] POST /sessions/ created session_id=%s namespace=%s", session.id, namespace)
        return Response(
            ChatSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class ChatSessionDetailView(APIView):
    """Retrieve or delete a session."""

    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id)
            return Response(ChatSessionSerializer(session).data)
        except ChatSession.DoesNotExist:
            logger.warning("[chat] GET /sessions/%s/ 404 not found", session_id)
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def delete(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            logger.warning("[chat] DELETE /sessions/%s/ 404 not found", session_id)
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        session_id_str = str(session_id)
        with transaction.atomic():
            session.delete()
        count_after = ChatSession.objects.count()
        logger.info("[chat] DELETE /sessions/%s/ deleted ok total_in_db_now=%s", session_id_str, count_after)
        resp = Response(status=status.HTTP_204_NO_CONTENT)
        resp["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return resp


class ChatMessageView(APIView):
    """Stream a response via Server-Sent Events (SSE)."""

    def post(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_message = (request.data.get("message") or "").strip()
        if not user_message:
            return Response(
                {"error": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        engine = ChatEngine(session)

        def event_stream():
            for event in engine.stream_response(user_message):
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [STREAM_END]\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ChatSuggestionsView(APIView):
    """Context-aware suggested questions based on current cluster state."""

    def get(self, request):
        namespace = request.query_params.get("ns", "all")

        from apps.incidents.models import Incident

        critical = (
            Incident.objects.filter(status="open", severity="critical")
            .order_by("-occurred_at")[:3]
        )

        suggestions = []
        for inc in critical:
            suggestions.append({
                "text": f"Why is {inc.pod_name} {inc.incident_type}?",
                "category": "active_incident",
                "icon": "🔴",
                "tool_hint": "analyze_pod",
            })

        suggestions += [
            {
                "text": "What are the most recurring problems in this cluster?",
                "category": "patterns",
                "icon": "🔁",
                "tool_hint": "get_patterns",
            },
            {
                "text": f"Is it safe to deploy to {namespace} right now?",
                "category": "risk",
                "icon": "⚠️",
                "tool_hint": "risk_check",
            },
            {
                "text": "Which services are most likely to cause a blast radius?",
                "category": "blast_radius",
                "icon": "💥",
                "tool_hint": "get_blast_radius",
            },
            {
                "text": "Show me all incidents from the last 7 days",
                "category": "history",
                "icon": "📅",
                "tool_hint": "search_incidents",
            },
        ]

        return Response({
            "suggestions": suggestions[:6],
            "namespace": namespace,
        })


class ChatCommandsView(APIView):
    """Return available slash commands."""

    def get(self, request):
        return Response({
            "commands": [
                {
                    "command": "/analyze",
                    "args": "<pod> <namespace>",
                    "description": "Deep analysis of a pod",
                },
                {
                    "command": "/history",
                    "args": "<pod> <namespace>",
                    "description": "Full incident timeline for a pod",
                },
                {
                    "command": "/blast",
                    "args": "<pod> <namespace>",
                    "description": "Blast radius for a pod",
                },
                {
                    "command": "/risk",
                    "args": "<service> <namespace>",
                    "description": "Pre-deploy risk check",
                },
                {
                    "command": "/patterns",
                    "args": "[namespace]",
                    "description": "Top recurring cluster patterns",
                },
                {
                    "command": "/search",
                    "args": "<query>",
                    "description": "Semantic search over incidents",
                },
                {
                    "command": "/clear",
                    "args": "",
                    "description": "Clear current session",
                },
                {
                    "command": "/new",
                    "args": "",
                    "description": "Start a new session",
                },
            ],
        })
