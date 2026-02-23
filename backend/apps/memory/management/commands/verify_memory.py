"""
Management command: verify ChromaDB and Neo4j connectivity and report sizes.
Runs a test semantic search query.
"""
import os

from django.core.management.base import BaseCommand

from apps.memory.graph_builder import KubeGraphBuilder
from apps.memory.vector_store import IncidentVectorStore


class Command(BaseCommand):
    help = "Verify ChromaDB and Neo4j connectivity, collection sizes, and semantic search"

    def handle(self, *args, **options):
        all_ok = True

        # ChromaDB
        try:
            store = IncidentVectorStore()
            coll = store._collection
            count = coll.count()
            collection_name = os.environ.get("CHROMA_COLLECTION_NAME") or "kubememory_incidents"
            self.stdout.write("✓ ChromaDB: %s documents in %s" % (count, collection_name))
        except Exception as e:
            self.stdout.write(self.style.ERROR("✗ ChromaDB: %s" % e))
            all_ok = False

        # Neo4j
        try:
            graph = KubeGraphBuilder()
            with graph._driver.session() as session:
                r = session.run("MATCH (p:Pod) RETURN count(p) AS pods")
                rec = r.single()
                pods = rec["pods"] if rec else 0
                r = session.run("MATCH (i:Incident) RETURN count(i) AS incidents")
                rec = r.single()
                incidents = rec["incidents"] if rec else 0
                r = session.run("MATCH (f:Fix) RETURN count(f) AS fixes")
                rec = r.single()
                fixes = rec["fixes"] if rec else 0
            graph.close()
            self.stdout.write("✓ Neo4j: %s pods, %s incidents, %s fixes in graph" % (pods, incidents, fixes))
        except Exception as e:
            self.stdout.write(self.style.ERROR("✗ Neo4j: %s" % e))
            all_ok = False

        # Semantic search test
        try:
            store = IncidentVectorStore()
            results = store.search_similar("payment service crash", n_results=5)
            self.stdout.write(
                "✓ Semantic search test: found %s similar incidents for \"payment service crash\""
                % len(results)
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR("✗ Semantic search test: %s" % e))
            all_ok = False

        if not all_ok:
            raise SystemExit(1)
