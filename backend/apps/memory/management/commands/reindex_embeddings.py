"""
Re-embed all incidents whose embedding_model_version differs from OLLAMA_EMBED_MODEL.
Usage: python manage.py reindex_embeddings
"""
import os

from django.core.management.base import BaseCommand

from apps.incidents.models import Incident
from apps.memory.vector_store import IncidentVectorStore


class Command(BaseCommand):
    """Reindex incident embeddings when the embed model changes."""

    help = "Re-embed incidents whose embedding_model_version != OLLAMA_EMBED_MODEL"

    def handle(self, *args, **options) -> None:
        current = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        qs = Incident.objects.exclude(embedding_model_version=current)
        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("All incidents already use current embed model."))
            return
        vs = IncidentVectorStore()
        updated = 0
        for incident in qs.iterator():
            vs.delete_incident(incident)
            chroma_id = vs.embed_incident(incident)
            incident.chroma_id = chroma_id
            incident.embedding_model_version = current
            incident.save(update_fields=["chroma_id", "embedding_model_version"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Reindexed {updated}/{total} incidents to {current}"))
