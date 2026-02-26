"""
Manages the in-process watcher subprocess (run_watcher).
Used when the user starts watching from the UI so no manual docker/terminal is needed.
NEVER logs or stores kubeconfig content — only file paths.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Single watcher process; guarded by _lock
_watcher_process: subprocess.Popen | None = None
_watcher_cluster_id: int | None = None
_lock = threading.Lock()

# Paths (container defaults). Use a writable path for active config so we don't write to
# a read-only mount (e.g. docker-compose mounts ./kubeconfig at /app/.kube/config:ro).
KUBECONFIGS_DIR = Path(os.environ.get("KUBEMEMORY_KUBECONFIGS_DIR", "/app/kubeconfigs"))
ACTIVE_KUBECONFIG_PATH = Path(os.environ.get("KUBEMEMORY_ACTIVE_KUBECONFIG") or str(KUBECONFIGS_DIR / "active.config"))


def _ensure_kubeconfigs_dir() -> None:
    """Ensure KUBECONFIGS_DIR exists (for per-cluster stored configs)."""
    KUBECONFIGS_DIR.mkdir(parents=True, exist_ok=True)


def get_cluster_kubeconfig_path(cluster_id: int) -> Path:
    """Path where a cluster's kubeconfig file is stored."""
    _ensure_kubeconfigs_dir()
    return KUBECONFIGS_DIR / f"cluster_{cluster_id}.config"


def _kind_cluster_name_from_kubeconfig(content: str) -> str | None:
    """
    Infer Kind cluster name from kubeconfig. Kind uses context names like 'kind-demo'
    and the control-plane container is '<name>-control-plane'. Returns None if not detected.
    """
    # current-context: kind-demo or kind-kubememory-prod-sim
    match = re.search(r"current-context:\s*(\S+)", content)
    if match:
        ctx = match.group(1).strip()
        if ctx.startswith("kind-"):
            return ctx[5:].strip() or None  # strip "kind-" prefix
    # Fallback: cluster name in clusters block often matches (e.g. kind-demo)
    match = re.search(r"clusters:\s*\n\s*-\s*cluster:.*?name:\s*(\S+)", content, re.DOTALL)
    if match:
        name = match.group(1).strip()
        if name.startswith("kind-"):
            return name[5:].strip() or None
    return None


def write_cluster_kubeconfig(
    cluster_id: int,
    content: str,
    use_docker_host: bool = False,
    use_kind_network: bool = False,
    kind_cluster_name: str | None = None,
) -> Path:
    """
    Write kubeconfig content to the cluster's file.

    - If use_docker_host is True (and not use_kind_network): replace 127.0.0.1/0.0.0.0
      with host.docker.internal and add insecure-skip-tls-verify. Works when the cluster
      API is bound to 0.0.0.0 so the host can be reached from the container.

    - If use_kind_network is True: rewrite server to https://<name>-control-plane:6443
      so the app (when attached to the Kind Docker network) talks to the control-plane
      container directly. No need to recreate the cluster with 0.0.0.0. kind_cluster_name
      can be provided or inferred from current-context (e.g. kind-demo -> demo).

    Returns the path written.
    """
    _ensure_kubeconfigs_dir()
    path = get_cluster_kubeconfig_path(cluster_id)
    text = content

    if use_kind_network:
        name = (kind_cluster_name or "").strip() or _kind_cluster_name_from_kubeconfig(content)
        if not name:
            # Fallback: use a safe default so we at least write something
            name = "kind"
        host = f"{name}-control-plane"
        server = f"https://{host}:6443"
        # Replace server: https://... with our Kind control-plane URL
        text = re.sub(
            r"server:\s*https?://[^\s\n]+",
            f"server: {server}",
            text,
            count=1,
        )
        # Ensure insecure-skip-tls-verify (Kind cert is for localhost/127.0.0.1)
        if "insecure-skip-tls-verify" not in text:
            lines = text.split("\n")
            out = []
            for line in lines:
                out.append(line)
                if re.match(r"\s*server:\s*", line):
                    out.append("    insecure-skip-tls-verify: true")
            text = "\n".join(out)
    elif use_docker_host:
        text = text.replace("127.0.0.1", "host.docker.internal").replace(
            "0.0.0.0", "host.docker.internal"
        )
        if "insecure-skip-tls-verify" not in text and "host.docker.internal" in text:
            lines = text.split("\n")
            out = []
            for line in lines:
                out.append(line)
                if line.strip().startswith("server:") and "host.docker.internal" in line:
                    out.append("    insecure-skip-tls-verify: true")
            text = "\n".join(out)
    path.write_text(text, encoding="utf-8")
    return path


def activate_cluster_config(cluster_id: int, namespaces: list[str]) -> bool:
    """
    Copy the cluster's kubeconfig to the writable active path and return True if the file existed.
    Does not start the watcher; call start_watcher after this.
    """
    src = get_cluster_kubeconfig_path(cluster_id)
    if not src.exists():
        logger.warning("Cluster %s kubeconfig not found at %s", cluster_id, src)
        return False
    dest = ACTIVE_KUBECONFIG_PATH
    _ensure_kubeconfigs_dir()  # ensure dest.parent exists and is writable
    shutil.copy2(src, dest)
    logger.info("Activated kubeconfig for cluster %s -> %s", cluster_id, dest)
    return True


def start_watcher(cluster_id: int, namespaces: list[str]) -> dict[str, Any]:
    """
    Activate this cluster's kubeconfig and start the watcher subprocess (or restart with new config).
    namespaces: list of namespace names to watch.
    Returns {started: bool, error?: str}.
    """
    global _watcher_process, _watcher_cluster_id
    with _lock:
        if _watcher_process is not None and _watcher_process.poll() is None:
            _watcher_process.terminate()
            _watcher_process.wait(timeout=10)
            _watcher_process = None
            _watcher_cluster_id = None
        if not activate_cluster_config(cluster_id, namespaces):
            return {"started": False, "error": "Cluster kubeconfig file not found. Use paste kubeconfig or provide path."}
        env = os.environ.copy()
        env["K8S_KUBECONFIG_PATH"] = str(ACTIVE_KUBECONFIG_PATH)
        env["K8S_NAMESPACES"] = ",".join(namespaces) if namespaces else "default"
        try:
            # Use writable dir that contains manage.py (e.g. /app in Docker, or backend/ locally)
            cwd = Path("/app") if Path("/app/manage.py").exists() else Path(os.getcwd())
            _watcher_process = subprocess.Popen(
                [sys.executable, "manage.py", "run_watcher"],
                cwd=str(cwd),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            _watcher_cluster_id = cluster_id
            logger.info("Started watcher for cluster %s, namespaces %s", cluster_id, namespaces)
            return {"started": True}
        except Exception as e:
            logger.exception("Failed to start watcher: %s", e)
            return {"started": False, "error": str(e)}


def stop_watcher() -> dict[str, Any]:
    """Stop the watcher subprocess if running. Returns {stopped: bool}."""
    global _watcher_process, _watcher_cluster_id
    with _lock:
        if _watcher_process is None:
            return {"stopped": False}
        if _watcher_process.poll() is None:
            _watcher_process.terminate()
            _watcher_process.wait(timeout=10)
        _watcher_process = None
        _watcher_cluster_id = None
        logger.info("Stopped watcher")
        return {"stopped": True}


def watcher_status() -> dict[str, Any]:
    """Return {running: bool, cluster_id?: int}."""
    with _lock:
        running = _watcher_process is not None and _watcher_process.poll() is None
        return {"running": running, "cluster_id": _watcher_cluster_id}
