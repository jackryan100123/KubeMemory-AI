# Minikube: Create Cluster + Connect to KubeMemory

Step-by-step: run a simple Minikube cluster with 3 nginx pods, then connect it to the KubeMemory app.

---

## Part 1: Minikube cluster with 3 nginx pods

### 1.1 Install Minikube (if not already)

**Linux:**
```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm minikube-linux-amd64
```

**macOS:**
```bash
brew install minikube
```

**Or:** https://minikube.sigs.k8s.io/docs/start/

### 1.2 Start a Minikube cluster

```bash
minikube start
```

Optional: use a driver (e.g. Docker) and more resources:
```bash
minikube start --driver=docker --cpus=2 --memory=4096
```

### 1.3 Verify cluster

```bash
kubectl get nodes
kubectl get ns
```

### 1.4 Run 3 nginx pods

**Option A — one Deployment with 3 replicas (simplest):**

```bash
kubectl create deployment nginx --image=nginx --replicas=3
kubectl get pods
```

**Option B — explicit namespace and expose (optional):**

```bash
kubectl create namespace app
kubectl create deployment nginx -n app --image=nginx --replicas=3
kubectl get pods -n app
```

### 1.5 Confirm 3 nginx pods are running

```bash
kubectl get pods
# or, if you used -n app:
kubectl get pods -n app
```

You should see 3 pods with status `Running`.

### 1.6 (Optional) Create a Service so pods are “used”

```bash
kubectl expose deployment nginx --port=80
# or with namespace:
kubectl expose deployment nginx -n app --port=80
```

---

## Part 2: Connect Minikube to KubeMemory app

KubeMemory runs in Docker and needs to reach the Minikube API. Minikube’s API is usually at `127.0.0.1` with a random port, so from inside Docker you must use the **host** address.

**Recommended (UI only):** Connect Cluster → **Paste kubeconfig** → paste `kubectl config view --minify --raw` output, check "App running in Docker" → Test → namespaces → Start watching. Watcher starts automatically. See **Security & what we access** on the Connect page.

### 2.1 Get Minikube kubeconfig

```bash
minikube update-context
kubectl config view --minify
```

Note the `server:` URL (e.g. `https://127.0.0.1:61456`). The port changes per Minikube start.

### 2.2 Expose Minikube API so Docker can reach it (Linux)

If the app runs in Docker on the same machine, containers can’t use `127.0.0.1` on the host. Use one of these:

**A) Use host network for the API (recommended for local dev)**

Tunnel so the API is reachable at a stable address:

```bash
minikube tunnel
# Leave this running in a terminal (or run in background)
```

Or use the minikube profile and get the API URL:

```bash
minikube profile list
# Use the API URL from: minikube status
```

**B) Kubeconfig file for Docker (project root `kubeconfig`)**

The app mounts `./kubeconfig` from the project root into the container. To use Minikube from inside Docker:

1. Get Minikube API server URL and port:
   ```bash
   kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
   # e.g. https://127.0.0.1:61456
   ```

2. From the project root, create a kubeconfig that uses the host (replace `61456` with your port):
   ```bash
   cd /path/to/KubeMemory-AI
   minikube update-context
   kubectl config view --minify --raw | \
     sed -e 's/127.0.0.1/host.docker.internal/g' \
         -e 's/0.0.0.0/host.docker.internal/g' \
         -e '/server: https:\/\/host.docker.internal/a\    insecure-skip-tls-verify: true' \
     > kubeconfig
   ```
   If `host.docker.internal` is not available (some Linux), use your host IP (e.g. `192.168.x.x` or `172.17.0.1`) instead in the sed, and ensure Minikube is bound to that or `0.0.0.0`.

3. Restart the API so it picks up the file: `docker compose up -d django-api`.

**C) Run the watcher on the host (easiest)**

Use your normal kubeconfig and run the watcher **on the host** (not in Docker), so it talks to `127.0.0.1` directly. See project docs for `run_watcher` on the host.

### 2.3 Start KubeMemory app

From the project root:

```bash
cd /path/to/KubeMemory-AI
docker compose up -d
# Wait for services to be healthy
```

Open the app in the browser (e.g. http://localhost:5173 or your frontend URL).

### 2.4 Connect cluster in the UI

1. Go to **Connect Cluster** (sidebar: “+ Connect Cluster” or `/connect`).

2. **Step 1** — Click **GET STARTED**.

3. **Step 2 — Connection method**  
   Choose **“Kubeconfig File Path”** (for Minikube we use the host’s kubeconfig).

4. **Step 3 — Configure & test**
   - **Cluster name:** e.g. `minikube`.
   - **Kubeconfig path:**  
     - If the watcher runs **on the host**: use `~/.kube/config` or the full path (e.g. `/home/ubuntu/.kube/config`).  
     - If the app runs **in Docker** and must reach Minikube: use a path that is mounted into the container and points to a kubeconfig that uses `host.docker.internal` (or the host IP) as the API server.  
   - **Context (optional):** leave blank for default, or set to `minikube` if that’s your context name.
   - Click **TEST CONNECTION**.  
   - If it fails: ensure the cluster is running (`minikube status`), the path is correct, and (if in Docker) the API server in that kubeconfig is reachable from the container (e.g. `host.docker.internal:PORT`).

5. **Step 4 — Namespaces**  
   Select the namespaces to watch (e.g. `default`, or `app` if you created it). Avoid `kube-system` for less noise. Click **START WATCHING ✓**.

6. You should be redirected to the dashboard; the sidebar will show the cluster (e.g. “minikube”) as connected/watching.

### 2.5 Start the watcher (so incidents are ingested)

The UI “connect” step only registers the cluster. To actually watch events and create incidents:

**If the watcher runs inside Docker (django-api container):**

- The container must have a kubeconfig that reaches Minikube (e.g. via `host.docker.internal` and the correct port).  
- Then:
  ```bash
  docker compose exec django-api python manage.py run_watcher
  ```

**If the watcher runs on the host (recommended for Minikube):**

- Use the same kubeconfig as when testing in the UI (e.g. `~/.kube/config`).
  ```bash
  export KUBECONFIG=~/.kube/config   # or minikube kubeconfig
  cd backend
  python manage.py run_watcher
  ```
  (Or run via your project’s `make watcher` if it’s set up for host kubeconfig.)

### 2.6 Verify end-to-end

- In the app: Dashboard and Incidents pages should show data when events occur (e.g. pod restarts, failures).
- Trigger a simple event (e.g. delete a pod and let it recreate):
  ```bash
  kubectl delete pod -l app=nginx
  kubectl get pods -w
  ```
- Check the app again for new incidents/events.

---

## Quick reference

| Step | Command / action |
|------|-------------------|
| Start Minikube | `minikube start` |
| 3 nginx pods | `kubectl create deployment nginx --image=nginx --replicas=3` |
| Check pods | `kubectl get pods` |
| App connection (recommended) | Connect Cluster → **Paste kubeconfig** → paste YAML, check Docker → Test → namespaces → Start watching (watcher starts automatically) |
| App connection (alternative) | Connect Cluster → Kubeconfig path → `~/.kube/config` (or mounted path) → Test → Select namespaces → Start watching |
| Run watcher | Automatic when you click Start watching; or manually: `python manage.py run_watcher` on host or in container |
