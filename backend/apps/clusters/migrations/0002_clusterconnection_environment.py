"""Add environment field to ClusterConnection."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clusters", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="clusterconnection",
            name="environment",
            field=models.CharField(
                choices=[
                    ("dev", "Development"),
                    ("staging", "Staging"),
                    ("prod", "Production"),
                    ("other", "Other"),
                ],
                default="dev",
                max_length=20,
            ),
        ),
    ]

