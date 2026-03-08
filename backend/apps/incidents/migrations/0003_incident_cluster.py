"""Add cluster foreign key to Incident."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("clusters", "0002_clusterconnection_environment"),
        ("incidents", "0002_incident_estimated_waste_usd"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="cluster",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="incidents",
                to="clusters.clusterconnection",
            ),
        ),
    ]

