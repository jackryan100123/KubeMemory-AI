"""
Kubernetes client helpers for cluster connection test.
NEVER stores or logs kubeconfig content — only the path.
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

import urllib3

logger = logging.getLogger(__name__)

# Suppress TLS warning when kubeconfig has insecure-skip-tls-verify (e.g. Kind from Docker)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_connection(
    connection_method: str,
    kubeconfig_path: str = "",
    context_name: str = "",
) -> dict[str, Any]:
    """
    Test connectivity to a cluster. Loads kubeconfig from path only.
    Returns {connected, node_count, server_version, namespaces, error}.
    Uses 5-second timeout for list_node.
    """
    result: dict[str, Any] = {
        "connected": False,
        "node_count": 0,
        "server_version": "",
        "namespaces": [],
        "error": "",
    }
    try:
        from kubernetes import client, config
    except ImportError:
        result["error"] = "kubernetes client not installed"
        return result

    def _run() -> dict[str, Any]:
        out: dict[str, Any] = {
            "node_count": 0,
            "server_version": "",
            "namespaces": [],
        }
        if connection_method == "in_cluster":
            config.load_incluster_config()
        else:
            raw = (kubeconfig_path or os.environ.get("KUBECONFIG") or os.environ.get("K8S_KUBECONFIG_PATH") or "").strip()
            if not raw:
                raw = "~/.kube/config"
            path = os.path.expanduser(raw)
            if not os.path.isfile(path) and os.environ.get("K8S_KUBECONFIG_PATH"):
                path = os.environ.get("K8S_KUBECONFIG_PATH", "")
            if not path or not os.path.isfile(path):
                raise FileNotFoundError(f"Kubeconfig not found: {path or raw}")
            config.load_kube_config(config_file=path, context=context_name or None)
        v1 = client.CoreV1Api()
        nodes = v1.list_node()
        out["node_count"] = len(nodes.items) if nodes.items else 0
        ns_list = v1.list_namespace()
        out["namespaces"] = [
            (item.metadata.name or "")
            for item in (ns_list.items or [])
            if item.metadata and item.metadata.name
        ]
        try:
            version_resp = v1.api_client.call_api(
                "/version",
                "GET",
                auth_settings=["BearerToken"],
                response_type="object",
            )
            if version_resp and isinstance(version_resp[0], dict):
                git_version = (version_resp[0].get("gitVersion") or "")[:50]
                if git_version:
                    out["server_version"] = git_version
        except Exception:
            out["server_version"] = "unknown"
        return out

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run)
            try:
                data = future.result(timeout=5)
            except FuturesTimeoutError:
                result["error"] = "connection timeout (5s)"
                return result
        result["connected"] = True
        result["node_count"] = data.get("node_count", 0)
        result["server_version"] = data.get("server_version", "") or "unknown"
        result["namespaces"] = data.get("namespaces", [])
    except FileNotFoundError as e:
        result["error"] = str(e)
    except Exception as e:
        logger.exception("test_connection failed")
        result["error"] = str(e) or "connection refused"
    return result
