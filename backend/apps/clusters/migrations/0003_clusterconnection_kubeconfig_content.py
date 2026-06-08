# Generated for encrypted kubeconfig at rest
from django.db import migrations
import config.encrypted_fields


class Migration(migrations.Migration):

    dependencies = [
        ("clusters", "0002_clusterconnection_environment"),
    ]

    operations = [
        migrations.AddField(
            model_name="clusterconnection",
            name="kubeconfig_content",
            field=config.encrypted_fields.EncryptedTextField(
                blank=True,
                help_text="Pasted kubeconfig YAML, encrypted at rest (never exposed via API).",
            ),
        ),
    ]
