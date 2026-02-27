"""
Chat session and message models.
Stores full conversation history so the assistant has memory
across multiple questions in the same session.
"""
import uuid

from django.db import models


class ChatSession(models.Model):
    """
    A conversation session. One session = one chat thread.
    Scoped to a namespace so context is relevant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    namespace = models.CharField(max_length=255, default="all")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Session {self.id} ({self.namespace}) — {self.message_count} msgs"

    def auto_title(self) -> None:
        """Set title from the first user message so the sidebar shows a meaningful label."""
        first = self.messages.filter(role="user").first()
        if not first:
            return
        new_title = (first.content or "").strip()[:60]
        if not new_title:
            new_title = "New chat"
        current = (self.title or "").strip()
        is_default = not current or current == "New chat" or current.startswith("New chat (")
        if current and not is_default:
            return
        self.title = new_title
        from django.utils import timezone
        self.updated_at = timezone.now()
        self.save(update_fields=["title", "updated_at"])


class ChatMessage(models.Model):
    """
    A single message in a chat session.
    role: 'user' | 'assistant' | 'tool_call' | 'tool_result'
    """

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL_CALL = "tool_call", "Tool Call"
        TOOL_RESULT = "tool_result", "Tool Result"

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()

    # For tool_call messages
    tool_name = models.CharField(max_length=100, blank=True)
    tool_input = models.JSONField(null=True, blank=True)

    # For tool_result messages
    tool_output = models.TextField(blank=True)
    tool_success = models.BooleanField(default=True)

    # Metadata
    tokens_used = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"[{self.role}] {(self.content or '')[:50]}"
