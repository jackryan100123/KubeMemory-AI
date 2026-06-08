# Dedup fields, structured analysis, embedding version
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("incidents", "0003_incident_cluster"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="analysis_result",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="incident",
            name="fingerprint",
            field=models.CharField(
                blank=True, db_index=True, max_length=64, null=True, unique=True
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="occurrence_count",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="incident",
            name="last_seen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="incident",
            name="embedding_model_version",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
