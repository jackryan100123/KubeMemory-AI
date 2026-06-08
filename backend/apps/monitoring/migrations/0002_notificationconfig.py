# NotificationConfig model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("slack", "Slack"), ("webhook", "Webhook")],
                        max_length=20,
                    ),
                ),
                ("url", models.URLField(max_length=512)),
                (
                    "min_severity",
                    models.CharField(
                        default="high",
                        help_text="Minimum severity to trigger: low, medium, high, critical",
                        max_length=20,
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
