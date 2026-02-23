"""
Management command: create 20 dummy incidents across 5 pods and run full ingestion.
Use for testing the RAG pipeline before the watcher captures real data.
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.incidents.models import Incident
from apps.memory.graph_builder import KubeGraphBuilder
from apps.memory.vector_store import IncidentVectorStore


class Command(BaseCommand):
    help = "Create 20 test incidents across 5 pods and populate ChromaDB + Neo4j"

    PODS = [
        ("payment-service", "default"),
        ("auth-service", "default"),
        ("api-gateway", "default"),
        ("worker", "default"),
        ("scheduler", "default"),
    ]

    INCIDENT_TYPES = [
        Incident.IncidentType.CRASH_LOOP,
        Incident.IncidentType.OOM_KILL,
        Incident.IncidentType.IMAGE_PULL,
        Incident.IncidentType.NODE_PRESSURE,
        Incident.IncidentType.EVICTED,
        Incident.IncidentType.PENDING,
        Incident.IncidentType.UNKNOWN,
    ]

    SEVERITIES = [
        Incident.Severity.LOW,
        Incident.Severity.MEDIUM,
        Incident.Severity.HIGH,
        Incident.Severity.CRITICAL,
    ]

    DESCRIPTIONS = [
        "Container restarted repeatedly; exit code 1",
        "OOMKilled; memory limit exceeded",
        "Failed to pull image: connection timeout",
        "Node had pressure: memory, disk",
        "Pod evicted due to node resource pressure",
        "Pod stuck in Pending: insufficient CPU",
        "Unknown failure; check logs",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=20,
            help="Number of incidents to create (default 20)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        self.stdout.write("Creating %s test incidents..." % count)

        vector_store = IncidentVectorStore()
        graph = KubeGraphBuilder()

        created = 0
        now = timezone.now()
        for i in range(count):
            pod_name, namespace = random.choice(self.PODS)
            occurred_at = now - timedelta(days=random.randint(0, 30))
            incident_type = random.choice(self.INCIDENT_TYPES)
            severity = random.choice(self.SEVERITIES)
            desc = random.choice(self.DESCRIPTIONS)
            node_name = f"node-{random.randint(1, 5)}"
            service_name = pod_name.replace("-service", "") if "service" in pod_name else pod_name

            incident = Incident.objects.create(
                pod_name=pod_name,
                namespace=namespace,
                node_name=node_name,
                service_name=service_name,
                incident_type=incident_type,
                severity=severity,
                status=Incident.Status.OPEN,
                description=desc,
                raw_logs=f"Test log line {i} for {pod_name}",
                occurred_at=occurred_at,
            )

            try:
                chroma_id = vector_store.embed_incident(incident)
                neo4j_id = graph.ingest_incident(incident)
                incident.chroma_id = chroma_id
                incident.neo4j_id = neo4j_id
                incident.save(update_fields=["chroma_id", "neo4j_id"])
                created += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR("Ingestion failed for incident %s: %s" % (incident.id, e)))

        graph.close()
        self.stdout.write(self.style.SUCCESS("Created %s incidents and ran full ingestion (ChromaDB + Neo4j)." % created))
