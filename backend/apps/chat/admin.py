"""Django admin for ChatSession and ChatMessage."""
from django.contrib import admin
from .models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "namespace", "message_count", "updated_at"]
    list_filter = ["namespace"]
    search_fields = ["title"]
    ordering = ["-updated_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "role", "content_preview", "created_at"]
    list_filter = ["role"]
    search_fields = ["content"]
    ordering = ["created_at"]

    def content_preview(self, obj):
        return (obj.content or "")[:60] + ("..." if len(obj.content or "") > 60 else "")

    content_preview.short_description = "Content"
