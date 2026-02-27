# Generated for Phase 6 — Chat session and message models

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ChatSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("namespace", models.CharField(default="all", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("message_count", models.IntegerField(default=0)),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant"), ("tool_call", "Tool Call"), ("tool_result", "Tool Result")], max_length=20)),
                ("content", models.TextField()),
                ("tool_name", models.CharField(blank=True, max_length=100)),
                ("tool_input", models.JSONField(blank=True, null=True)),
                ("tool_output", models.TextField(blank=True)),
                ("tool_success", models.BooleanField(default=True)),
                ("tokens_used", models.IntegerField(default=0)),
                ("latency_ms", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.chatsession")),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
