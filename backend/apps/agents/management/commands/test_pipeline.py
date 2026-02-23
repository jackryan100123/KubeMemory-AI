"""
Test the full LangGraph pipeline on an existing incident.
Usage: python manage.py test_pipeline --incident-id 1
"""
from django.core.management.base import BaseCommand

from apps.incidents.models import Incident
from apps.agents.pipeline import analyze_incident


class Command(BaseCommand):
    help = "Run the full LangGraph pipeline on an incident and print analysis"

    def add_arguments(self, parser):
        parser.add_argument("--incident-id", type=int, required=True)

    def handle(self, *args, **options):
        incident_id = options["incident_id"]
        incident = Incident.objects.filter(id=incident_id).first()
        if not incident:
            self.stderr.write(self.style.ERROR(f"Incident #{incident_id} not found."))
            return

        self.stdout.write("Running pipeline...")
        final_state = analyze_incident(incident_id)

        root_cause = final_state.get("root_cause", "")
        recommendation = final_state.get("recommendation", "")
        prevention = final_state.get("prevention_advice", "")
        confidence = final_state.get("confidence", 0.0)
        sources = final_state.get("similar_incidents", [])
        causal = final_state.get("causal_patterns", [])
        processing_ms = final_state.get("processing_time_ms", 0)
        errors = final_state.get("errors", [])

        sep = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        self.stdout.write(sep)
        self.stdout.write(f"KUBEMEMORY ANALYSIS — Incident #{incident_id}")
        self.stdout.write(sep)
        self.stdout.write(
            f"Pod: {incident.pod_name} (namespace: {incident.namespace})"
        )
        self.stdout.write(
            f"Type: {incident.incident_type} | Severity: {incident.severity}"
        )
        self.stdout.write("")
        self.stdout.write("ROOT CAUSE:")
        self.stdout.write(root_cause or "(none)")
        self.stdout.write("")
        self.stdout.write("RECOMMENDATION:")
        self.stdout.write(recommendation or "(none)")
        self.stdout.write("")
        self.stdout.write("PREVENTION:")
        self.stdout.write(prevention or "(none)")
        self.stdout.write("")
        self.stdout.write(f"CONFIDENCE: {confidence}")
        self.stdout.write("")
        self.stdout.write("SOURCES (past incidents retrieved):")
        for s in sources:
            meta = s.get("metadata", {})
            occ = meta.get("occurred_at", "unknown")
            itype = meta.get("incident_type", "")
            pod = meta.get("pod_name", "")
            inc_id = meta.get("incident_id", "?")
            self.stdout.write(f"  - Incident #{inc_id} ({occ}): {itype} on {pod}")
        if not sources:
            self.stdout.write("  (none)")
        self.stdout.write("")
        self.stdout.write("NEO4J PATTERNS:")
        for p in causal:
            self.stdout.write(
                f"  - {p.get('incident_type', '')}: freq={p.get('frequency', 0)}, "
                f"fixes={p.get('fixes_that_worked', [])}"
            )
        if not causal:
            self.stdout.write("  (none)")
        self.stdout.write("")
        self.stdout.write(f"PROCESSING TIME: {processing_ms}ms")
        if errors:
            self.stdout.write(self.style.WARNING("Errors:"))
            for e in errors:
                self.stdout.write(f"  - {e}")
        self.stdout.write(sep)
