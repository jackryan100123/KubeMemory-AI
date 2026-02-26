"""
Manages the in-process watcher subprocess (run_watcher).
Used when the user starts watching from the UI so no manual docker/terminal is needed.
NEVER logs or stores kubeconfig content — only file paths.
"""
import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Single watcher process; guarded by _lock
_watcher_process: subprocess.Popen | None = None
_watcher_cluster_id: int | None = None
_lock = threading.Lock()

# Paths (container defaults)
KUBECONFIGS_DIR = Path(os.environ.get("KUBEMEMORY_KUBECONFIGS_DIR", "/app/kubeconfigs"))
ACTIVE_KUBECONFIG_PATH = Path(os.environ.get("K8S_KUBECONFIG_PATH", "/app/.kube/config"))


def _ensure_kubeconfigs_dir() -> None:
    """Ensure KUBECONFIGS_DIR exists (for per-cluster stored configs)."""
    KUBECONFIGS_DIR.mkdir(parents=True, exist_ok=True)


def get_cluster_kubeconfig_path(cluster_id: int) -> Path:
    """Path where a cluster's kubeconfig file is stored."""
    _ensure_kubeconfigs_dir()
    return KUBECONFIGS_DIR / f"cluster_{cluster_id}.config"


def write_cluster_kubeconfig(cluster_id: int, content: str, use_docker_host: bool = False) -> Path:
    """
    Write kubeconfig content to the cluster's file.
    If use_docker_host is True, replace 127.0.0.1/0.0.0.0 with host.docker.internal
    and add insecure-skip-tls-verify for the cluster server.
    Returns the path written.
    """
    _ensure_kubeconfigs_dir()
    path = get_cluster_kubeconfig_path(cluster_id)
    text = content
    if use_docker_host:
        text = text.replace("127.0.0.1", "host.docker.internal").replace("0.0.0.0", "host.docker.internal")
        # Add insecure-skip-tls-verify under the cluster server line if not present
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
    Copy the cluster's kubeconfig to the active path and return True if the file existed.
    Does not start the watcher; call start_watcher after this.
    """
    src = get_cluster_kubeconfig_path(cluster_id)
    if not src.exists():
        logger.warning("Cluster %s kubeconfig not found at %s", cluster_id, src)
        return False
    dest = ACTIVE_KUBECONFIG_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
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
            _watcher_process = subprocess.Popen(
                ["python", "manage.py", "run_watcher"],
                cwd="/app",
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
