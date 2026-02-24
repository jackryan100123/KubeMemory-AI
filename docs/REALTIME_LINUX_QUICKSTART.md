# Step-by-Step: Run KubeMemory in Real Time on Linux

Clone the repo, create a Kind cluster, run the app, and see incidents flow in real time. Use this on a **Linux** system (bare metal, VM, or WSL2).

---

## Prerequisites

Install once:

| Tool | Purpose | Install (Linux) |
|------|----------|------------------|
| **Docker** + **Docker Compose** | Run KubeMemory stack | [Install Docker Engine](https://docs.docker.com/engine/install/) + `sudo usermod -aG docker $USER` (log out/in) |
| **Kind** | Local Kubernetes cluster | `curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64 && chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind` |
| **kubectl** | Talk to the cluster | `curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && chmod +x kubectl && sudo mv kubectl /usr/local/bin/` |
| **Git** | Clone repo | `sudo apt install git` (or equivalent) |

Check:

```bash
docker --version && docker compose version
kind --version
kubectl version --client
```

---

## Step 1: Clone the Project

```bash
cd ~
git clone https://github.com/YOUR_ORG/KubeMemory-AI.git
cd KubeMemory-AI
```

*(Replace the URL with your actual repo if different.)*

---

## Step 2: Create the Kind Cluster and Workloads

This creates a cluster that will generate real incidents (CrashLoopBackOff, OOMKill, ImagePullBackOff, Pending, etc.).

```bash
cd k8s/prod-sim
chmod +x bootstrap.sh
./bootstrap.sh
```

**What this does:**

- Creates Kind cluster `kubememory-prod-sim` (1 control-plane + 3 workers).
- Creates namespaces: `production`, `staging`, `monitoring`, `data-pipeline`.
- Deploys workloads that fail on purpose (payment-service, auth-service, api-gateway, ml-data-worker, notification-service).

**Modern Kind (no `kubeconfig-path`):** If the script prints a line like `export KUBECONFIG=$(kind get kubeconfig-path ...)`, use this instead:

```bash
export KUBECONFIG=$(kind get kubeconfig --name kubememory-prod-sim)
# Or persist it:
kind get kubeconfig --name kubememory-prod-sim > ~/.kube/kind-kubememory-config
export KUBECONFIG=~/.kube/kind-kubememory-config
```

Verify:

```bash
kubectl get nodes
kubectl get pods -A
```

You should see some pods in `CrashLoopBackOff`, `ImagePullBackOff`, or `Pending` after a short time.

---

## Step 3: Configure Environment

From the **project root** (`KubeMemory-AI/`):

```bash
cd ~/KubeMemory-AI
cp .env.example .env
```

Edit `.env` and set at least:

- **POSTGRES_PASSWORD** – strong password.
- **NEO4J_PASSWORD** – strong password.
- **K8S_NAMESPACES** – namespaces to watch (must match your cluster):

```env
K8S_IN_CLUSTER=False
K8S_KUBECONFIG_PATH=/root/.kube/config
K8S_NAMESPACES=production,staging,data-pipeline,default
K8S_WATCH_TIMEOUT=600
```

Save and exit. Do **not** commit `.env`.

---

## Step 4: Start KubeMemory Stack

```bash
docker compose up -d --build
```

Wait for services to be healthy (about 1–2 minutes). Check:

```bash
docker compose ps
```

All services (postgres, redis, neo4j, django-api, celery-worker, celery-beat, frontend, ollama) should be Up. If postgres is unhealthy, wait a bit (it has a 90s start period).

---

## Step 5: Run Migrations

```bash
docker compose exec django-api python manage.py migrate
```

You should see migrations for `clusters`, `incidents`, etc. applied.

*(Optional)* Seed a few test incidents so the dashboard has data immediately:

```bash
docker compose exec django-api python manage.py seed_test_incidents
```

---

## Step 6: Make the Watcher Reach Kind (Pick One)

The watcher runs **inside** the `django-api` container. The Kind API server is on the **host** (e.g. `127.0.0.1:6443`). From inside the container, `127.0.0.1` is the container, so we need the container to use the **host** for the API.

### Option A: Use a kubeconfig that points to the host (recommended on Linux)

1. **Get the Kind API server address from your current kubeconfig:**

   ```bash
   kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
   # Example: https://127.0.0.1:6443
   ```

   Note the **port** (e.g. `6443`).

2. **Create a kubeconfig the container can use** (replace `127.0.0.1` with `host.docker.internal`):

   ```bash
   KUBE_PORT=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' | sed -n 's|.*:\([0-9]*\)$|\1|p')
   sed "s/127.0.0.1/host.docker.internal/g" "$KUBECONFIG" > ~/.kube/kubeconfig-docker.yaml
   ```

   If your server URL has a different host, adjust the `sed` (e.g. replace that host with `host.docker.internal`).

3. **Mount kubeconfig and allow the container to resolve `host.docker.internal`.**

   Create a small override so the watcher container can use this file and reach the host:

   ```bash
   # Replace $HOME if your shell doesn't expand it in the heredoc
   cat <<EOF > docker-compose.watcher-kind.yml
   # Override to mount kubeconfig and reach Kind from the django-api container (Linux)
   services:
     django-api:
       volumes:
         - chroma_data:/app/chroma_data
         - ${HOME}/.kube:/root/.kube:ro
       extra_hosts:
         - "host.docker.internal:host-gateway"
   EOF
   ```

   Then start (or restart) with the override:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.watcher-kind.yml up -d
   ```

4. **Point the watcher at the docker kubeconfig.** Set in `.env`:

   ```env
   K8S_KUBECONFIG_PATH=/root/.kube/kubeconfig-docker.yaml
   ```

   (If you put the file elsewhere under the mounted `~/.kube`, use that path.)

   Restart django-api so it picks up the env:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.watcher-kind.yml up -d django-api
   ```

5. **Start the watcher** (in the foreground to see logs):

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.watcher-kind.yml exec django-api python manage.py run_watcher
   ```

   You should see lines like:

   ```
   Loaded kubeconfig from /root/.kube/kubeconfig-docker.yaml
   [watcher] Watching namespace: production
   [watcher] Watching namespace: staging
   ...
   Dispatched incident pod=payment-service-xxx namespace=production reason=CrashLoopBackOff
   ```

   Leave this terminal open, or run it in the background (e.g. `tmux` / `screen`).

### Option B: Run the watcher on the host

If you prefer not to use `host.docker.internal`:

1. **Expose Redis** so the host can enqueue Celery tasks. Add to `docker-compose.yml` under the `redis` service (or use an override):

   ```yaml
   ports:
     - "6379:6379"
   ```

2. **Start the stack**, then in a **new terminal** on the host:

   ```bash
   cd ~/KubeMemory-AI/backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements/base.txt
   export K8S_IN_CLUSTER=False
   export K8S_KUBECONFIG_PATH=$HOME/.kube/config
   export K8S_NAMESPACES=production,staging,data-pipeline,default
   export CELERY_BROKER_URL=redis://localhost:6379/1
   export CELERY_RESULT_BACKEND=redis://localhost:6379/2
   # Optional: if your .env has POSTGRES_HOST=localhost and you expose postgres 5432
   python manage.py run_watcher
   ```

   Use your real `KUBECONFIG` (e.g. `$KUBECONFIG` or `~/.kube/config`) so the watcher talks to Kind at `127.0.0.1`.

---

## Step 7: Verify in Real Time

### 7.1 API

```bash
curl -s http://localhost:8000/api/incidents/ | head -c 500
```

You should see JSON with incident records (from the prod-sim workloads or seeded data).

### 7.2 Dashboard

1. Open in a browser: **http://localhost:5173** (or the port your frontend uses).
2. You should see:
   - Stats (Open Incidents, Critical, Cluster Health, Estimated Waste).
   - Namespace health heatmap.
   - Live incident feed and patterns.

### 7.3 Trigger a New Incident (optional)

In another terminal:

```bash
# Scale down a deployment to cause a short burst of events
kubectl scale deployment -n production notification-service --replicas=0
sleep 5
kubectl scale deployment -n production notification-service --replicas=2
```

Or delete a pod so it restarts:

```bash
kubectl delete pod -n production -l app=payment-service --force --grace-period=0
```

Within a few seconds the watcher should log a dispatched incident and the dashboard/API should show the new or updated incident.

### 7.4 Watch cluster events

```bash
kubectl get events -A --sort-by='.lastTimestamp' -w
```

---

## Step 8: Optional Checks

- **Neo4j:** http://localhost:7474 (browser). Login with `NEO4J_USER` / `NEO4J_PASSWORD` from `.env`.
- **Ollama:** http://localhost:11434 (or use the dashboard “Run AI analysis” on an incident).
- **Verify memory:**  
  `docker compose exec django-api python manage.py verify_memory`

---

## One-Page Cheat Sheet (Copy-Paste)

```bash
# 1. Clone and go to project
git clone https://github.com/YOUR_ORG/KubeMemory-AI.git
cd KubeMemory-AI

# 2. Kind cluster
cd k8s/prod-sim && chmod +x bootstrap.sh && ./bootstrap.sh
export KUBECONFIG=$(kind get kubeconfig --name kubememory-prod-sim)
cd ../..

# 3. Env
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, NEO4J_PASSWORD, K8S_NAMESPACES=production,staging,data-pipeline,default

# 4. Stack
docker compose up -d --build
docker compose exec django-api python manage.py migrate
docker compose exec django-api python manage.py seed_test_incidents  # optional

# 5. Kubeconfig for Docker (Linux: host.docker.internal)
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
sed "s/127.0.0.1/host.docker.internal/g" "$KUBECONFIG" > ~/.kube/kubeconfig-docker.yaml
# (creates docker-compose.watcher-kind.yml with ${HOME} so compose expands it)
printf '%s\n' 'services:' '  django-api:' '    volumes:' '      - chroma_data:/app/chroma_data' '      - ${HOME}/.kube:/root/.kube:ro' '    extra_hosts:' '      - "host.docker.internal:host-gateway"' > docker-compose.watcher-kind.yml
# In .env set: K8S_KUBECONFIG_PATH=/root/.kube/kubeconfig-docker.yaml
docker compose -f docker-compose.yml -f docker-compose.watcher-kind.yml up -d django-api

# 6. Watcher (foreground)
docker compose -f docker-compose.yml -f docker-compose.watcher-kind.yml exec django-api python manage.py run_watcher

# 7. Verify
curl -s http://localhost:8000/api/incidents/ | head -c 300
# Open http://localhost:5173
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `connection refused` when running watcher | Kind not running (`kind get clusters`), or kubeconfig still uses `127.0.0.1` inside Docker (use `kubeconfig-docker.yaml` + `host.docker.internal`). |
| `host.docker.internal: unknown host` | Add `extra_hosts: - "host.docker.internal:host-gateway"` to the service (Docker 20.10+). |
| No incidents in dashboard | Watcher not running, or no Warning/Failed Pod events yet. Trigger one (delete pod, scale deployment) or run `seed_test_incidents`. |
| Postgres unhealthy | Wait 90s and run `docker compose up -d` again. |
| Frontend not loading | Check `docker compose ps`; frontend port (e.g. 5173 or 80) must be free. |

Once the watcher is running and the cluster has some failing workloads, the app is working in real time: **Kind → watcher → Celery → Postgres/ChromaDB/Neo4j → API and dashboard.**
