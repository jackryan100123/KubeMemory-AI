"""
Django management command that watches Kubernetes events in real-time
and dispatches Celery tasks for each new incident detected.

Usage: python manage.py run_watcher
"""
import logging
import os
import signal
import time
from typing import Any

import urllib3
from django.core.management.base import BaseCommand
from kubernetes import client, config

# Suppress TLS warning when kubeconfig has insecure-skip-tls-verify (e.g. Kind from Docker)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from kubernetes.client.rest import ApiException
from kubernetes.watch import Watch

from apps.incidents.tasks import ingest_incident_task

logger = logging.getLogger(__name__)

REASON_TO_TYPE = {
    "CrashLoopBackOff": "CrashLoopBackOff",
    "OOMKilling": "OOMKill",
    "Killing": "CrashLoopBackOff",
    "BackOff": "CrashLoopBackOff",
    "Failed": "Unknown",
    "NodeNotReady": "NodePressure",
    "Evicted": "Evicted",
    "ImagePullBackOff": "ImagePullBackOff",
    "ErrImagePull": "ImagePullBackOff",
}

REASON_TO_SEVERITY = {
    "OOMKilling": "critical",
    "CrashLoopBackOff": "high",
    "NodeNotReady": "high",
    "Evicted": "medium",
    "ImagePullBackOff": "low",
    "BackOff": "medium",
}


def _load_kube_config() -> None:
    """Load in-cluster or kubeconfig based on K8S_IN_CLUSTER."""
    in_cluster = os.environ.get("K8S_IN_CLUSTER", "false").lower() in ("true", "1", "yes")
    if in_cluster:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    else:
        kubeconfig_path = os.environ.get("K8S_KUBECONFIG_PATH", "/root/.kube/config")
        config.load_kube_config(config_file=kubeconfig_path)
        logger.info("Loaded kubeconfig from %s", kubeconfig_path)


def _get_namespaces() -> list[str]:
    """Return list of namespaces to watch from K8S_NAMESPACES env."""
    raw = os.environ.get("K8S_NAMESPACES", "default")
    return [ns.strip() for ns in raw.split(",") if ns.strip()]


def _get_watch_timeout() -> int:
    """Return watch timeout in seconds from env."""
    return int(os.environ.get("K8S_WATCH_TIMEOUT", "600"))


def _read_pod_logs(v1: client.CoreV1Api, namespace: str, pod_name: str, tail_lines: int = 100) -> str:
    """Fetch last N lines of pod logs; return empty string on any error."""
    try:
        resp = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
        )
        return resp or ""
    except Exception as e:
        logger.debug("Could not read logs for %s/%s: %s", namespace, pod_name, e)
        return ""


def _build_incident_data(
    v1: client.CoreV1Api,
    namespace: str,
    pod_name: str,
    reason: str,
    message: str,
    event_time: Any,
    node_name: str = "",
) -> dict[str, Any]:
    """Build incident payload for ingest_incident_task."""
    incident_type = REASON_TO_TYPE.get(reason, "Unknown")
    severity = REASON_TO_SEVERITY.get(reason, "medium")
    raw_logs = _read_pod_logs(v1, namespace, pod_name)
    occurred_at = event_time.isoformat() if hasattr(event_time, "isoformat") else str(event_time)
    return {
        "pod_name": pod_name,
        "namespace": namespace,
        "node_name": node_name or "",
        "service_name": "",
        "incident_type": incident_type,
        "severity": severity,
        "description": message or f"{reason}",
        "raw_logs": raw_logs,
        "occurred_at": occurred_at,
    }


class Command(BaseCommand):
    """Run the Kubernetes event watcher and dispatch Celery tasks."""

    help = "Watch Kubernetes events and ingest incidents via Celery"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._shutdown = False

    def handle(self, *args: Any, **options: Any) -> None:
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        _load_kube_config()
        v1 = client.CoreV1Api()
        namespaces = _get_namespaces()
        watch_timeout = _get_watch_timeout()
        backoff = 1
        max_backoff = 60

        while not self._shutdown:
            for namespace in namespaces:
                if self._shutdown:
                    break
                try:
                    self._watch_namespace(v1, namespace, watch_timeout)
                    backoff = 1
                except ApiException as e:
                    logger.warning("K8s API error for namespace %s: %s", namespace, e)
                except Exception as e:
                    logger.exception("Watcher error: %s", e)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        self._shutdown = True
        logger.info("Received signal %s, shutting down watcher", signum)

    def _watch_namespace(
        self,
        v1: client.CoreV1Api,
        namespace: str,
        watch_timeout: int,
    ) -> None:
        w = Watch()
        stream = w.stream(
            v1.list_namespaced_event,
            namespace,
            timeout_seconds=watch_timeout,
        )
        for event in stream:
            if self._shutdown:
                break
            obj = event.get("object")
            if not obj or obj.kind != "Event":
                continue
            reason = getattr(obj, "reason", None) or ""
            type_ = getattr(obj, "type", None) or ""
            if type_ not in ("Warning", "Failed"):
                continue
            message = getattr(obj, "message", None) or ""
            involved = getattr(obj, "involved_object", None)
            if not involved or getattr(involved, "kind", None) != "Pod":
                continue
            pod_name = getattr(involved, "name", None)
            if not pod_name:
                continue
            node_name = ""
            try:
                pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                node_name = getattr(pod.spec, "node_name", None) or ""
            except Exception:
                pass
            event_time = getattr(obj, "last_timestamp", None) or getattr(obj, "event_time", None)
            if not event_time:
                from django.utils import timezone
                event_time = timezone.now()

            incident_data = _build_incident_data(
                v1=v1,
                namespace=namespace,
                pod_name=pod_name,
                reason=reason,
                message=message,
                event_time=event_time,
                node_name=node_name,
            )
            ingest_incident_task.delay(incident_data)
            logger.info(
                "Dispatched incident pod=%s namespace=%s reason=%s",
                pod_name, namespace, reason,
            )
