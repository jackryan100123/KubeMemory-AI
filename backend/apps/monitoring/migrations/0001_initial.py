# Generated for TaskLog model
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TaskLog",
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
                ("task_id", models.CharField(db_index=True, max_length=255)),
                ("task_name", models.CharField(db_index=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("failure", "Failure"),
                            ("retry", "Retry"),
                            ("success", "Success"),
                        ],
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
