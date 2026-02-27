"""
Tests all 7 MCP tools and prints results.
Run before connecting Claude Desktop to verify everything works.

Usage: python manage.py test_mcp
"""
import time

from django.core.management.base import BaseCommand

from apps.chat.tools import execute_tool

TOOL_ORDER = [
    "search_incidents",
    "analyze_pod",
    "get_blast_radius",
    "get_top_blast_radius_services",
    "get_patterns",
    "get_pod_timeline",
    "risk_check",
    "get_graph_context",
]


class Command(BaseCommand):
    help = "Validate all 8 MCP/chat tools (run before connecting Claude Desktop)"

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("━" * 50)
        self.stdout.write("KubeMemory MCP Server — Tool Validation")
        self.stdout.write("━" * 50)
        self.stdout.write("")

        from apps.incidents.models import Incident

        sample = Incident.objects.order_by("-occurred_at").first()
        pod_name = (sample.pod_name if sample else "test-pod") or "test-pod"
        namespace = (sample.namespace if sample else "default") or "default"
        service_name = (sample.service_name if sample else "test-svc") or "test-svc"

        tests = [
            ("search_incidents", {"query": "crash or OOM", "limit": 5}),
            ("analyze_pod", {"pod_name": pod_name, "namespace": namespace, "incident_type": "Unknown"}),
            ("get_blast_radius", {"pod_name": pod_name, "namespace": namespace}),
            ("get_top_blast_radius_services", {"namespace": namespace or "all", "limit": 10}),
            ("get_patterns", {"limit": 8}),
            ("get_pod_timeline", {"pod_name": pod_name, "namespace": namespace, "limit": 10}),
            ("risk_check", {"service_name": service_name, "namespace": namespace}),
            ("get_graph_context", {"namespace": namespace}),
        ]

        all_ok = True
        for name, arguments in tests:
            start = time.time()
            try:
                out = execute_tool(name, arguments, namespace=None)
                elapsed_ms = int((time.time() - start) * 1000)
                preview = (out or "").strip()[:60].replace("\n", " ")
                if len(out or "") > 60:
                    preview += "..."
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {name:25} ({elapsed_ms:4}ms) → {preview}"
                    )
                )
            except Exception as e:
                all_ok = False
                elapsed_ms = int((time.time() - start) * 1000)
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ {name:25} ({elapsed_ms:4}ms) → {e!s}"
                    )
                )

        self.stdout.write("")
        if all_ok:
            self.stdout.write(
                self.style.SUCCESS(
                    "All 8 tools passed. MCP server is ready for Claude Desktop."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Some tools failed. Fix errors above before using Claude Desktop."
                )
            )
        self.stdout.write("━" * 50)
        self.stdout.write("")
