"""DRF serializers for ChatSession and ChatMessage."""
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import ChatMessage, ChatSession


class ChatMessageSerializer(ModelSerializer):
    """Full message serializer for session detail."""

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "role",
            "content",
            "tool_name",
            "tool_input",
            "tool_output",
            "tool_success",
            "latency_ms",
            "created_at",
        ]


class ChatSessionSerializer(ModelSerializer):
    """Session with nested messages and last_message."""

    messages = ChatMessageSerializer(many=True, read_only=True)
    last_message = SerializerMethodField()

    def get_last_message(self, obj: ChatSession):
        msg = obj.messages.filter(role__in=["user", "assistant"]).last()
        return ChatMessageSerializer(msg).data if msg else None

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "title",
            "namespace",
            "message_count",
            "created_at",
            "updated_at",
            "messages",
            "last_message",
        ]


class ChatSessionListSerializer(ModelSerializer):
    """Lightweight — no messages. For sidebar list."""

    last_message = SerializerMethodField()

    def get_last_message(self, obj: ChatSession):
        msg = obj.messages.filter(role__in=["user", "assistant"]).last()
        if not msg:
            return None
        return {
            "role": msg.role,
            "content": (msg.content or "")[:80],
        }

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "title",
            "namespace",
            "message_count",
            "updated_at",
            "last_message",
        ]
