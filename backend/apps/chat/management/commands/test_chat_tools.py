"""
Run all chat tools from the backend and print results.
Use to verify tool wiring and responses without the frontend.

Usage: python manage.py test_chat_tools
       python manage.py test_chat_tools --tool get_top_blast_radius_services
"""
import time

from django.core.management.base import BaseCommand

from apps.chat.tools import CHAT_TOOLS, execute_tool
from apps.incidents.models import Incident


def get_sample_pod_and_namespace():
    """Use a real pod from DB if any, else defaults."""
    sample = Incident.objects.order_by("-occurred_at").first()
    pod_name = (sample.pod_name if sample else "payment-service") or "payment-service"
    namespace = (sample.namespace if sample else "default") or "default"
    service_name = (sample.service_name if sample else pod_name) or pod_name
    return pod_name, namespace, service_name


# Default args per tool for testing (namespace can be overridden by execute_tool).
TOOL_TEST_CASES = [
    ("search_incidents", {"query": "crash or OOM or restart", "limit": 5}),
    ("get_top_blast_radius_services", {"namespace": "all", "limit": 10}),
    ("get_patterns", {"limit": 8}),
    ("get_graph_context", {"namespace": "default"}),
    ("get_blast_radius", None),  # filled with sample pod
    ("get_pod_timeline", None),
    ("risk_check", None),
    ("analyze_pod", None),
]


class Command(BaseCommand):
    help = "Run all chat tools from the backend and print full output"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tool",
            type=str,
            default=None,
            help="Run only this tool (e.g. get_top_blast_radius_services)",
        )
        parser.add_argument(
            "--namespace",
            type=str,
            default="all",
            help="Namespace for tools that use it (default: all)",
        )

    def handle(self, *args, **options):
        tool_filter = (options.get("tool") or "").strip().lower()
        namespace = options.get("namespace") or "all"
        pod_name, ns_from_db, service_name = get_sample_pod_and_namespace()

        self.stdout.write("")
        self.stdout.write("━" * 60)
        self.stdout.write("KubeMemory Chat — Tool verification (backend)")
        self.stdout.write("━" * 60)
        self.stdout.write(f"Sample pod: {pod_name}, namespace: {namespace}")
        self.stdout.write("")

        tests = []
        for name, arguments in TOOL_TEST_CASES:
            if tool_filter and name != tool_filter:
                continue
            if arguments is None:
                if name == "get_blast_radius":
                    arguments = {"pod_name": pod_name, "namespace": ns_from_db}
                elif name == "get_pod_timeline":
                    arguments = {"pod_name": pod_name, "namespace": ns_from_db, "limit": 5}
                elif name == "risk_check":
                    arguments = {"service_name": service_name, "namespace": ns_from_db}
                elif name == "analyze_pod":
                    arguments = {"pod_name": pod_name, "namespace": ns_from_db, "incident_type": "Unknown"}
                else:
                    arguments = {"namespace": ns_from_db}
            else:
                arguments = dict(arguments)
                if "namespace" in arguments and namespace:
                    arguments["namespace"] = namespace
            tests.append((name, arguments))

        if not tests:
            self.stdout.write(self.style.ERROR(f"No tool named '{tool_filter}'"))
            return

        all_ok = True
        for name, arguments in tests:
            self.stdout.write(f"\n--- {name} ---")
            start = time.time()
            try:
                out = execute_tool(name, arguments, namespace=namespace)
                elapsed_ms = int((time.time() - start) * 1000)
                self.stdout.write(out or "(empty)")
                self.stdout.write(self.style.SUCCESS(f"  [{elapsed_ms}ms] OK"))
            except Exception as e:
                all_ok = False
                self.stdout.write(self.style.ERROR(f"  ERROR: {e}"))

        self.stdout.write("")
        self.stdout.write("━" * 60)
        if all_ok:
            self.stdout.write(self.style.SUCCESS("All run tools completed."))
        else:
            self.stdout.write(self.style.WARNING("Some tools failed (see above)."))
        self.stdout.write("")
