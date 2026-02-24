# KubeMemory Connectivity In Depth

This guide explains **exactly** how your Kubernetes cluster connects to KubeMemory, using a concrete example: **Kind with 1 control plane + 1 worker, nginx pod in `default` namespace**.

---

## 1. The Big Picture: What Connects to What

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  YOUR KIND CLUSTER (on your machine)                                        │
│  ┌──────────────┐     ┌──────────────┐                                      │
│  │ control-plane│     │   worker     │   nginx pod in namespace: default    │
│  │  (API 6443) │     │  (runs pods) │                                      │
│  └──────┬───────┘     └──────────────┘                                      │
│         │                                                                     │
│         │  kubeconfig (file on your PC)                                       │
│         │  tells clients: "API server is at https://127.0.0.1:XXXXX"         │
└─────────┼───────────────────────────────────────────────────────────────────┘
          │
          │  Watcher reads kubeconfig, opens a WATCH on /api/v1/namespaces/default/events
          │  and receives only Warning/Failed Pod events
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  KUBEMEMORY (Django + Celery + Redis + Postgres + Neo4j + ChromaDB)         │
│                                                                              │
│  run_watcher  ──►  ingest_incident_task.delay(payload)  ──►  Celery         │
│       │                                    │                                  │
│       │                                    ▼                                  │
│       │              Postgres (Incident row) + ChromaDB (embed) + Neo4j      │
│       │                                    │                                  │
│       │                                    ▼                                  │
│       │              run_ai_analysis_task.delay(incident_id)  ──►  Celery    │
│       │                                    │                                  │
│       └───────────────────────────────────┴──► WebSocket push to dashboard   │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Only one component** talks to Kubernetes: the **watcher** (`python manage.py run_watcher`).
- The watcher uses the **Kubernetes Python client** and your **kubeconfig** to open a **streaming watch** on **Events** in the namespaces you configured.
- It **never writes** to the cluster; it only **reads** Events (and pod details for logs/node name).

---

## 2. Your Exact Setup: Kind + 1 Control Plane + 1 Worker + nginx in `default`

Assumptions:

- Kind cluster is running (e.g. `kind create cluster` or your own config).
- `kubectl get nodes` shows 1 control plane and 1 worker.
- You have an nginx pod: `kubectl get pods -n default` shows something like `nginx-xxx`.

### 2.1 Where Things Run

| Thing              | Where it runs        | Role |
|--------------------|----------------------|------|
| Kind API server   | Your host (e.g. 127.0.0.1:6443 or random port) | Serves Kubernetes API |
| Kubeconfig        | Your host (e.g. `~/.kube/config` or `%USERPROFILE%\.kube\config`) | Tells clients how to reach the API |
| KubeMemory stack  | Docker Compose (django-api, celery-worker, redis, postgres, neo4j, frontend, ollama) | API, DB, AI, UI |
| **Watcher**       | Either **inside** the django-api container or **on your host** | Connects to Kind using kubeconfig and pushes events into KubeMemory |

### 2.2 The One Critical Detail: Who Can Reach the Kind API?

- Kind’s API server is bound to **your host** (e.g. `127.0.0.1:6443`).
- **From your host:** `127.0.0.1` is correct; kubeconfig works as-is.
- **From inside a Docker container:** `127.0.0.1` is the container, not the host. So the container **cannot** use a kubeconfig that says `server: https://127.0.0.1:6443`.

So you have two ways to run the watcher:

- **A) Watcher on the host** – kubeconfig stays as-is; watcher runs outside Docker and talks to Kind and to Redis/Postgres (and optionally Django) in Docker.
- **B) Watcher in Docker** – you must give the container a kubeconfig that points the server to the host (e.g. `host.docker.internal:6443`) and mount that file (or the whole `~/.kube`) into the container.

We’ll do both below; for your first time, **A is simpler**.

---

## 3. Step-by-Step: Your Kind + nginx in `default`

### Step 1: Confirm Kind and nginx

```bash
# Cluster and nodes
kubectl config current-context   # e.g. kind-kind
kubectl get nodes                # 1 control-plane, 1 worker

# Your nginx in default
kubectl get pods -n default
kubectl get events -n default --sort-by='.lastTimestamp'
```

If nginx is healthy, you might see few or no Warning events. That’s fine; the watcher will sit and wait for the first Warning/Failed event (e.g. when you break the pod or scale down).

### Step 2: Tell KubeMemory Which Cluster and Namespace

KubeMemory reads cluster access from **environment variables** (and optionally from the Cluster Connection wizard in the UI; the wizard saves config in the DB, but the **watcher** still uses env).

In your project root `.env` (same one used by `docker compose`), set:

```env
# We're not running inside the cluster
K8S_IN_CLUSTER=False

# Path to kubeconfig *inside the container* (if watcher runs in Docker)
# Or path on host (if watcher runs on host)
K8S_KUBECONFIG_PATH=/root/.kube/config

# Only watch default (where your nginx is)
K8S_NAMESPACES=default

# Optional: how long to hold the watch stream before reconnecting (seconds)
K8S_WATCH_TIMEOUT=600
```

For **watcher on the host** (recommended for Kind), you will run the watcher in a shell where `K8S_KUBECONFIG_PATH` points to your **host** kubeconfig (see below). The `.env` above is still used by Django/Celery; the watcher process can override with a host path.

### Step 3a: Run the Watcher **on the Host** (recommended for Kind)

This way the watcher uses your normal kubeconfig and talks to `127.0.0.1` (Kind) and to Dockerized Redis/Postgres.

1. **Start the rest of the stack** (no watcher yet):

   ```bash
   docker compose up -d
   ```

2. **On the host**, from the project root, with a venv that has the backend deps (or use `docker compose run --rm django-api` only for env, see below):

   - Set env so the watcher uses your host kubeconfig and only `default`:
     - Windows (PowerShell):
       ```powershell
       $env:K8S_IN_CLUSTER="False"
       $env:K8S_KUBECONFIG_PATH="$env:USERPROFILE\.kube\config"
       $env:K8S_NAMESPACES="default"
       ```
     - Linux/macOS:
       ```bash
       export K8S_IN_CLUSTER=False
       export K8S_KUBECONFIG_PATH=~/.kube/config
       export K8S_NAMESPACES=default
       ```

   - Run the watcher **against** the same Postgres/Redis as Docker (so it can enqueue Celery tasks and write to DB). Two options:

     - **Option 1 – run Django/Celery deps on host and point to Docker:**

       ```bash
       cd backend
       pip install -r requirements/base.txt   # or dev.txt
       export POSTGRES_HOST=localhost
       export REDIS_URL=redis://localhost:6379/0
       export CELERY_BROKER_URL=redis://localhost:6379/1
       export CELERY_RESULT_BACKEND=redis://localhost:6379/2
       # ... other env from .env (CHROMA_*, NEO4J_*, etc.)
       python manage.py run_watcher
       ```

       (Redis/Postgres must be reachable on localhost; if they’re only in Docker, use port mapping and the same vars.)

     - **Option 2 – run watcher in a one-off container that sees the host network and host kubeconfig** (so it still uses 127.0.0.1 for Kind):

       - Mount your kubeconfig into the container and use `network_mode: host` so 127.0.0.1 in kubeconfig is the host. Example (add to docker-compose or run one-off):

         ```bash
         docker compose run --rm --no-deps \
           -e K8S_NAMESPACES=default \
           -e K8S_KUBECONFIG_PATH=/root/.kube/config \
           -v "%USERPROFILE%\.kube:/root/.kube:ro" \
           --service-ports django-api \
           python manage.py run_watcher
         ```

         On Linux/macOS use `-v "$HOME/.kube:/root/.kube:ro"`. With `network_mode: host`, 127.0.0.1 in kubeconfig is the host, so Kind is reachable.

3. You should see logs like:

   ```
   Loaded kubeconfig from C:\Users\...\.kube\config
   [watcher] Watching namespace: default
   ```

   When a **Warning** or **Failed** event happens for a **Pod** in `default` (e.g. nginx back-off, OOMKilled, ImagePullBackOff), the watcher will:

   - Build an incident payload (pod name, namespace, reason, message, logs, node).
   - Call `ingest_incident_task.delay(incident_data)` so Celery writes to Postgres, ChromaDB, Neo4j, and pushes to the dashboard.

### Step 3b: Run the Watcher **inside** the Django Container (with host kubeconfig)

If you want `make watcher` (or `docker compose exec django-api python manage.py run_watcher`) to work, the container must:

1. Have a kubeconfig that points the API server to the **host**, not 127.0.0.1.
2. Have that kubeconfig (and optional CA) mounted into the container.

**1) Get the Kind API port from your kubeconfig:**

```bash
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
# e.g. https://127.0.0.1:6443
```

Note the port (e.g. `6443`).

**2) Create a kubeconfig the container can use** (server = host):

- On **Docker Desktop (Windows/Mac)** the host is `host.docker.internal`. Create a copy of your kubeconfig and replace the server:

  ```bash
  # Example: create kubeconfig-docker.yaml with server https://host.docker.internal:6443
  # (replace 6443 with your Kind port)
  ```

- Mount that file (and the same cluster CA/certs) into the container, e.g. in `docker-compose.yml` under `django-api`:

  ```yaml
  volumes:
    - chroma_data:/app/chroma_data
    # Uncomment and set to a path that has kubeconfig with server = host.docker.internal:PORT
    # - C:\Users\YourName\.kube:/root/.kube:ro
  ```

  And in `.env`:

  ```env
  K8S_KUBECONFIG_PATH=/root/.kube/config
  K8S_NAMESPACES=default
  ```

**3) Ensure the container can resolve `host.docker.internal`** (Docker Desktop does this by default).

**4) Start stack and run watcher inside the API container:**

```bash
docker compose up -d
make watcher
```

If the mounted kubeconfig uses `https://host.docker.internal:6443`, the watcher inside the container will connect to Kind on your host and watch `default` for Pod Warning/Failed events.

---

## 4. What the Watcher Actually Does (Code-Level)

1. **Load config**  
   `_load_kube_config()`: if `K8S_IN_CLUSTER` is false, it calls `config.load_kube_config(config_file=K8S_KUBECONFIG_PATH)`.

2. **Namespaces**  
   `_get_namespaces()`: splits `K8S_NAMESPACES` (e.g. `"default"`) into a list.

3. **Watch stream**  
   For each namespace it runs:
   `Watch().stream(v1.list_namespaced_event, namespace, timeout_seconds=watch_timeout)`  
   So it’s a long-lived HTTP stream of **Events** in that namespace.

4. **Filter**  
   Keeps only events where:
   - `object.kind == "Event"`
   - `object.type` in `("Warning", "Failed")`
   - `object.involved_object.kind == "Pod"`

5. **Build payload**  
   For each such event it:
   - Reads pod logs (if possible),
   - Maps `event.reason` to an incident type (e.g. CrashLoopBackOff, OOMKill, ImagePullBackOff),
   - Builds `incident_data` (pod_name, namespace, node_name, service_name, incident_type, severity, description, raw_logs, occurred_at).

6. **Enqueue**  
   `ingest_incident_task.delay(incident_data)` sends the payload to Celery. The rest (DB, vector store, graph, AI, WebSocket) is outside the watcher.

So **connectivity** for the watcher is: **kubeconfig → Kind API server → watch Events in `default` (and any other namespaces you set)**. No writes to the cluster.

---

## 5. End-to-End Checklist for Your Setup

- [ ] Kind cluster running; `kubectl get nodes` shows 1 control plane, 1 worker.
- [ ] nginx (or any pod) in `default`; `kubectl get pods -n default` works.
- [ ] `.env` has `K8S_IN_CLUSTER=False`, `K8S_NAMESPACES=default`, and `K8S_KUBECONFIG_PATH` set for the environment where the watcher runs.
- [ ] KubeMemory stack up: `docker compose up -d`.
- [ ] Watcher running:
  - **Host:** env vars for kubeconfig + `K8S_NAMESPACES=default`, then `python manage.py run_watcher` (with Postgres/Redis reachable).
  - **Docker:** kubeconfig mounted with server = `host.docker.internal:<port>`, then `make watcher` or `docker compose exec django-api python manage.py run_watcher`.
- [ ] Trigger a Warning event (e.g. kill nginx pod, or use a bad image), then check:
  - `curl http://localhost:8000/api/incidents/`
  - Dashboard at http://localhost:5173

Once one incident shows up, connectivity is proven end-to-end: **Kind (default namespace) → watcher → Celery → Postgres/ChromaDB/Neo4j → dashboard.**

---

## 6. Optional: Use the Connect Wizard (UI)

The **Connect Cluster** wizard at `/connect` lets you:

- Create a **ClusterConnection** (name, method, kubeconfig path, context, namespaces).
- **Test** connection (list nodes, server version, namespaces).
- **Connect** (save and mark as “watching”).

The watcher **does not** read from the DB yet; it still uses **env vars** (`K8S_KUBECONFIG_PATH`, `K8S_NAMESPACES`). So the wizard is for documenting and testing the cluster; you still configure the actual watcher via `.env` (and optionally a mounted kubeconfig) as above. Future work could make the watcher use the stored ClusterConnection.

---

## 7. Troubleshooting (Your Setup)

| Symptom | What to check |
|--------|----------------|
| Watcher says "connection refused" or timeout | Kind is not running, or watcher is in Docker and kubeconfig still uses `127.0.0.1` (use host run or host.docker.internal kubeconfig). |
| Watcher connects but no incidents | Only Warning/Failed **Pod** events create incidents. Generate one (e.g. `kubectl delete pod -n default <nginx-pod>` and check events). |
| `Forbidden` / 403 | Your kubeconfig user must be allowed to `list` and `watch` events and `get` pods in `default`. Kind default kubeconfig is usually cluster-admin. |
| `No such file: .../config` | `K8S_KUBECONFIG_PATH` must point to a file that exists **in the process** that runs the watcher (host path or mounted path in container). |

This is connectivity in depth for your project: one Kind cluster, one worker, nginx in `default`, and KubeMemory’s watcher as the only component that talks to the cluster.
