"""
Manages the in-process watcher subprocess (run_watcher).
Used when the user starts watching from the UI so no manual docker/terminal is needed.
NEVER logs or stores kubeconfig content — only file paths.

Watcher state is persisted to a PID file so that status and stop work correctly when
the API is served by multiple workers (e.g. gunicorn); the worker that started the
watcher holds the process handle, but any worker can report status or stop via the file.
"""
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Multiple watcher processes keyed by cluster_id; guarded by _lock so that
# concurrent API workers don't race to start/stop the same watcher.
_watcher_processes: dict[int, subprocess.Popen] = {}
_lock = threading.Lock()

# Paths (container defaults). Use a writable path for active config so we don't write to
# a read-only mount (e.g. docker-compose mounts ./kubeconfig at /app/.kube/config:ro).
KUBECONFIGS_DIR = Path(os.environ.get("KUBEMEMORY_KUBECONFIGS_DIR", "/app/kubeconfigs"))
ACTIVE_KUBECONFIG_PATH = Path(os.environ.get("KUBEMEMORY_ACTIVE_KUBECONFIG") or str(KUBECONFIGS_DIR / "active.config"))
# Legacy single-watcher PID path (used when cluster_id is unknown/None).
WATCHER_PID_FILE = KUBECONFIGS_DIR / "watcher.pid"


def _ensure_kubeconfigs_dir() -> None:
    """Ensure KUBECONFIGS_DIR exists (for per-cluster stored configs)."""
    KUBECONFIGS_DIR.mkdir(parents=True, exist_ok=True)


def _pid_file_for(cluster_id: int | None) -> Path:
    """Return PID file path for a given cluster_id (or legacy global file if None)."""
    if cluster_id is None:
        return WATCHER_PID_FILE
    return KUBECONFIGS_DIR / f"watcher_{cluster_id}.pid"


def _is_process_alive(pid: int) -> bool:
    """Return True if a process with the given PID exists and is running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _read_watcher_pid_file(cluster_id: int | None = None) -> dict[str, Any] | None:
    """Read watcher PID file; return {pid, cluster_id} or None if missing/invalid."""
    try:
        path = _pid_file_for(cluster_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        pid = data.get("pid")
        cluster_id = data.get("cluster_id")
        if pid is None or not isinstance(pid, int):
            return None
        return {"pid": pid, "cluster_id": cluster_id}
    except (json.JSONDecodeError, OSError):
        return None


def _write_watcher_pid_file(pid: int, cluster_id: int | None) -> None:
    """Write watcher PID and cluster_id to file so any worker can report status."""
    _ensure_kubeconfigs_dir()
    path = _pid_file_for(cluster_id)
    path.write_text(
        json.dumps({"pid": pid, "cluster_id": cluster_id}, indent=0),
        encoding="utf-8",
    )


def _remove_watcher_pid_file(cluster_id: int | None) -> None:
    """Remove PID file (e.g. after watcher stopped)."""
    try:
        path = _pid_file_for(cluster_id)
        if path.exists():
            path.unlink()
    except OSError:
        pass


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
    Writes PID to a per-cluster file so watcher_status/stop work from any API worker.
    Returns {started: bool, error?: str}.
    """
    with _lock:
        # Stop any existing watcher for this cluster (in this worker or another).
        existing = _watcher_processes.get(cluster_id)
        if existing is not None and existing.poll() is None:
            existing.terminate()
            existing.wait(timeout=10)
            _watcher_processes.pop(cluster_id, None)
            _remove_watcher_pid_file(cluster_id)
        else:
            # Watcher may have been started by another API worker; stop via PID file.
            pid_data = _read_watcher_pid_file(cluster_id)
            if pid_data and _is_process_alive(pid_data["pid"]):
                try:
                    os.kill(pid_data["pid"], signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
                _remove_watcher_pid_file(cluster_id)
        if not activate_cluster_config(cluster_id, namespaces):
            return {"started": False, "error": "Cluster kubeconfig file not found. Use paste kubeconfig or provide path."}
        env = os.environ.copy()
        env["K8S_KUBECONFIG_PATH"] = str(ACTIVE_KUBECONFIG_PATH)
        env["K8S_NAMESPACES"] = ",".join(namespaces) if namespaces else "default"
        env["K8S_CLUSTER_ID"] = str(cluster_id)
        try:
            # Use writable dir that contains manage.py (e.g. /app in Docker, or backend/ locally)
            cwd = Path("/app") if Path("/app/manage.py").exists() else Path(os.getcwd())
            proc = subprocess.Popen(
                [sys.executable, "manage.py", "run_watcher"],
                cwd=str(cwd),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            _watcher_processes[cluster_id] = proc
            _write_watcher_pid_file(proc.pid, cluster_id)
            logger.info("Started watcher for cluster %s, namespaces %s", cluster_id, namespaces)
            return {"started": True}
        except Exception as e:
            logger.exception("Failed to start watcher: %s", e)
            return {"started": False, "error": str(e)}


def _stop_watcher_for_cluster(cluster_id: int) -> bool:
    """Stop watcher for a specific cluster_id. Returns True if anything was stopped."""
    stopped = False
    proc = _watcher_processes.get(cluster_id)
    if proc is not None and proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=10)
        _watcher_processes.pop(cluster_id, None)
        _remove_watcher_pid_file(cluster_id)
        logger.info("Stopped watcher for cluster %s (local process)", cluster_id)
        stopped = True
    pid_data = _read_watcher_pid_file(cluster_id)
    if pid_data and _is_process_alive(pid_data["pid"]):
        try:
            os.kill(pid_data["pid"], signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        _remove_watcher_pid_file(cluster_id)
        logger.info("Stopped watcher for cluster %s (via PID file)", cluster_id)
        stopped = True
    return stopped


def stop_watcher(cluster_id: int | None = None) -> dict[str, Any]:
    """
    Stop watcher subprocess(es).

    If cluster_id is provided, stop only that cluster's watcher.
    If cluster_id is None, stop all known watchers.
    Returns {stopped: bool}.
    """
    with _lock:
        if cluster_id is not None:
            return {"stopped": _stop_watcher_for_cluster(cluster_id)}

        stopped_any = False
        # Stop all in-memory tracked watchers.
        for cid in list(_watcher_processes.keys()):
            if _stop_watcher_for_cluster(cid):
                stopped_any = True

        # Also stop any watchers that have PID files but are not in memory here.
        _ensure_kubeconfigs_dir()
        for path in KUBECONFIGS_DIR.glob("watcher_*.pid"):
            name = path.name  # watcher_<id>.pid
            try:
                cid_str = name.removeprefix("watcher_").removesuffix(".pid")
                cid = int(cid_str)
            except ValueError:
                continue
            if cid in _watcher_processes:
                continue
            if _stop_watcher_for_cluster(cid):
                stopped_any = True

        # Legacy global watcher PID file (no cluster_id).
        legacy = _read_watcher_pid_file(None)
        if legacy and _is_process_alive(legacy["pid"]):
            try:
                os.kill(legacy["pid"], signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            _remove_watcher_pid_file(None)
            logger.info("Stopped legacy watcher (no cluster_id)")
            stopped_any = True

        return {"stopped": stopped_any}


def watcher_status(cluster_id: int | None = None) -> dict[str, Any]:
    """
    Return watcher status.

    If cluster_id is provided, returns {running: bool, cluster_id: int | None} for that cluster.
    If cluster_id is None, returns a summary:
      {running: bool, cluster_id: int | None, cluster_ids: list[int]}
    where cluster_id (singular) is the first active cluster (for backward-compatible UI).
    """
    with _lock:
        if cluster_id is not None:
            # Check in-memory process first.
            proc = _watcher_processes.get(cluster_id)
            if proc is not None and proc.poll() is None:
                return {"running": True, "cluster_id": cluster_id}
            # Fallback to PID file.
            pid_data = _read_watcher_pid_file(cluster_id)
            if pid_data and _is_process_alive(pid_data["pid"]):
                return {"running": True, "cluster_id": pid_data.get("cluster_id")}
            if pid_data:
                _remove_watcher_pid_file(cluster_id)
            return {"running": False, "cluster_id": cluster_id}

        # Global summary across all clusters.
        active_cluster_ids: list[int] = []

        # Check local processes.
        for cid, proc in _watcher_processes.items():
            if proc.poll() is None and cid not in active_cluster_ids:
                active_cluster_ids.append(cid)

        # Check PID files for any additional clusters.
        _ensure_kubeconfigs_dir()
        for path in KUBECONFIGS_DIR.glob("watcher_*.pid"):
            name = path.name
            try:
                cid_str = name.removeprefix("watcher_").removesuffix(".pid")
                cid = int(cid_str)
            except ValueError:
                continue
            if cid in active_cluster_ids:
                continue
            pid_data = _read_watcher_pid_file(cid)
            if pid_data and _is_process_alive(pid_data["pid"]):
                active_cluster_ids.append(cid)
            elif pid_data:
                _remove_watcher_pid_file(cid)

        running = bool(active_cluster_ids)
        first_cluster = active_cluster_ids[0] if active_cluster_ids else None
        return {"running": running, "cluster_id": first_cluster, "cluster_ids": active_cluster_ids}
