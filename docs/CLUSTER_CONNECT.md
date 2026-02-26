# Connect Your Cluster to KubeMemory

This guide explains **all four connection workflows** in depth: when to use each, how they work, and how to connect from start to finish.

KubeMemory needs **read-only** access to your cluster (events, pods, namespaces, pod logs for context). It never modifies or deletes resources and never accesses secrets.

---

## Overview: Four connection workflows

| Workflow | When to use it | What you provide |
|----------|----------------|------------------|
| **Paste kubeconfig** | You have an existing cluster and can run `kubectl` (Kind, Minikube, any cluster). Easiest when the app runs in Docker. | Cluster name + pasted YAML. Options: “App runs in Docker” (rewrite to host) or **“Use Kind network”** (no need to recreate a 127.0.0.1 cluster). |
| **Kubeconfig file path** | You have a config file (e.g. from cloud CLI or a custom path). The app process can read that path. | Cluster name + path (e.g. `~/.kube/config`, `/path/to/gke-config.yaml`). Optional: context name. |
| **Use default kubeconfig** | `kubectl` already works; the backend runs where it can read the default kubeconfig (e.g. host or container with `~/.kube/config` mounted). | Cluster name + context name from `kubectl config current-context`. |
| **In-cluster** | KubeMemory runs **inside** the cluster (e.g. as a pod). No kubeconfig file needed. | Cluster name only. The app uses the in-cluster service account. |

In the UI: open **Connect Cluster** and choose one of these; the wizard shows workflow-specific instructions.

---

## Workflow 1: Paste kubeconfig (in depth)

### When to use

- You have **any** cluster (Kind, Minikube, EKS, GKE, AKS, on-prem) and can run `kubectl` on your machine.
- You prefer **not** to deal with file paths or mounting; you copy config once and paste.
- The app often runs **in Docker** on the same host as the cluster (or another host); we can rewrite the API server address so the container can reach the cluster.

### How it works

1. You paste the **full YAML** from `kubectl config view --minify --raw`.
2. The backend saves it to a **writable file** per cluster (e.g. `/app/kubeconfigs/cluster_<id>.config`). We never store the raw content in the database.
3. **If the app runs in Docker**, choose one:
   - **“App runs in Docker”** (host method): we replace `127.0.0.1`/`0.0.0.0` with `host.docker.internal` and add `insecure-skip-tls-verify`. This works only if the cluster API is bound to **0.0.0.0** so the host is reachable from the container.
   - **“Use Kind network”**: we rewrite the server to `https://<cluster-name>-control-plane:6443` so the backend (when attached to Kind’s Docker network) talks to the control-plane container directly. **You do not need to recreate the cluster** — your existing Kind cluster with API on 127.0.0.1 is fine. The backend must be on the Kind network: either run once `docker network connect kind $(docker compose ps -q django-api)`, or start the stack with the optional override so it’s automatic: `docker compose -f docker-compose.yml -f docker-compose.kind.yml up -d` (create your Kind cluster first so the `kind` network exists).
4. When you click **Start watching**, we copy that cluster’s file to the active watcher path and start the watcher subprocess. No manual `docker exec` or terminal watcher needed.

### Step-by-step

1. **Terminal:** Get kubeconfig for the context you use:
   ```bash
   kubectl config view --minify --raw
   ```
   Copy the **entire** output.

2. **Browser:** Open the app → **Connect Cluster** → **Choose how to connect** → **Paste kubeconfig**.

3. **UI:**  
   - **Cluster name:** Any label (e.g. `demo`, `prod-sim`).  
   - **Paste kubeconfig YAML here:** Paste what you copied.  
   - **App runs in Docker:** Check this if KubeMemory runs in Docker and the cluster is on the same machine.  
   - **If you get “Connection refused”** (cluster already on 127.0.0.1): check **Use Kind network** instead. Optionally enter the Kind cluster name (e.g. `demo`); we can infer it from your kubeconfig if left blank. Then run once on the host:
     ```bash
     docker network connect kind $(docker compose ps -q django-api)
     ```
   Click **Save & test connection**.

4. **UI:** Click **Test connection**. If it fails, the UI shows suggestions; see also [Troubleshooting](#troubleshooting-all-workflows) below.

5. **UI:** Click **Choose namespaces** → select namespaces → **Start watching**. The watcher starts automatically.

### Cluster already on 127.0.0.1? (No need to recreate)

If your Kind (or similar) cluster is **already running** with the API bound to 127.0.0.1, you have two options. Recreating the cluster is **not** required.

| Option | When to use | What you do |
|--------|-------------|-------------|
| **Use Kind network** (recommended) | Kind cluster, app in Docker, “Connection refused” with “App runs in Docker”. | In the UI: Paste kubeconfig → check **Use Kind network** (optionally set Kind cluster name, e.g. `demo`). Ensure the backend is on the Kind network: run once `docker network connect kind $(docker compose ps -q django-api)`, or start with `docker compose -f docker-compose.yml -f docker-compose.kind.yml up -d` so it’s automatic. Then Test connection. |
| **host.docker.internal** | Cluster API is bound to **0.0.0.0** so the host is reachable from the container. | Check **App runs in Docker** only (do not check Use Kind network). If your cluster is still on 127.0.0.1, either use “Use Kind network” above or recreate the cluster with `apiServerAddress: "0.0.0.0"` (last resort). |

Tools like **k8sgpt** and similar typically expect either a kubeconfig path the process can read and network reachability to the API (e.g. same host or correct server URL). KubeMemory supports both: rewriting the server to the host or, for Kind, rewriting to the control-plane container hostname so existing 127.0.0.1 clusters work without change.

### Troubleshooting (Paste kubeconfig)

| Symptom | What to do |
|--------|------------|
| Test connection: **Connection refused** (app in Docker) | Prefer **Use Kind network**: go back, check “Use Kind network”, run `docker network connect kind $(docker compose ps -q django-api)`, then Save & test again. No cluster recreate needed. Alternatively, ensure cluster API is on 0.0.0.0 and use “App runs in Docker” only. |
| Test connection: **Certificate / TLS** error | Ensure “App runs in Docker” or “Use Kind network” is used so we add `insecure-skip-tls-verify: true` for local clusters. |
| Use Kind network but still **connection refused** | Confirm the backend is on the Kind network: `docker network inspect kind` and check the backend container is listed. Re-run `docker network connect kind $(docker compose ps -q django-api)` if needed. Kind cluster name must match (e.g. context `kind-demo` → name `demo`). |
| Start watching: **500 or watcher didn’t start** | Backend writes the active kubeconfig to a writable path (e.g. `/app/kubeconfigs/active.config`). Ensure the app has write access to that directory; check backend logs. |

---

## Workflow 2: Kubeconfig file path (in depth)

### When to use

- You have a **path** to a kubeconfig file (e.g. `~/.kube/config`, or a file from `aws eks update-kubeconfig`, `gcloud container clusters get-credentials`, or a custom file).
- The KubeMemory **backend process** can read that path (same host, or the path is mounted into the container).

### How it works

1. You give a **path** (and optionally a **context** name). The backend does not read the file at create time; it stores the path and context.
2. When you **Test connection** or when the **watcher** runs, the backend loads kubeconfig from that path and uses the given context (or current context if blank).
3. If the app runs in Docker, the path must be **inside the container** (e.g. `/app/.kube/config` for a mounted file). The project’s `docker-compose` can mount a host file (e.g. `./kubeconfig:/app/.kube/config`); then you’d use path `/app/.kube/config` or the backend’s default.

### Step-by-step

1. **Get kubeconfig on the host** (if needed):
   - **Kind:** `kind get kubeconfig --name <name> > kubeconfig` (then optionally sed for Docker; see below).
   - **EKS:** `aws eks update-kubeconfig --name <cluster> --region <region>` (writes to `~/.kube/config`).
   - **GKE:** `gcloud container clusters get-credentials <cluster> --region <region>`.
   - **AKS:** `az aks get-credentials --resource-group <rg> --name <cluster>`.

2. **If the app runs in Docker** and the cluster is on the same host (Kind/Minikube), create a kubeconfig the container can use (project root):
   ```bash
   kind get kubeconfig --name <cluster-name> | \
     sed -e 's/127.0.0.1/host.docker.internal/g' \
         -e 's/0.0.0.0/host.docker.internal/g' \
         -e '/server: https:\/\/host.docker.internal/a\    insecure-skip-tls-verify: true' \
     > kubeconfig
   ```
   Then ensure `docker-compose` mounts `./kubeconfig` to the path the app uses (e.g. `/app/.kube/config`).

3. **Browser:** Connect Cluster → **Kubeconfig file path**.

4. **UI:**  
   - **Cluster name:** Any label.  
   - **Path to kubeconfig file:** Path **as seen by the backend** (e.g. `~/.kube/config` on host, or `/app/.kube/config` in container).  
   - **Context name (optional):** Leave blank for current context, or set e.g. `kind-demo`.  
   Click **Save & test connection** → **Test connection** → **Choose namespaces** → **Start watching**.

### Troubleshooting

| Symptom | What to do |
|--------|------------|
| **Kubeconfig not found** / No configuration | The path is wrong for the process (e.g. host path used but watcher runs in container). Use a path the backend/watcher can read, or use **Paste kubeconfig** and paste the file contents. |
| **Connection refused** (Docker) | From inside the container, the API server address in the kubeconfig must be the host (e.g. `host.docker.internal`), not `127.0.0.1`. Create the kubeconfig with the sed above or use Paste with “App runs in Docker”. |

---

## Workflow 3: Use default kubeconfig (context) (in depth)

### When to use

- **kubectl** already works (e.g. you’ve run `kind create cluster` or a cloud get-credentials).
- The KubeMemory backend runs where it can read the **default** kubeconfig (e.g. `~/.kube/config` or `KUBECONFIG`). Typical: backend on the **host** (not in Docker), or Docker with `~/.kube` mounted and path set to that file.

### How it works

1. You provide only a **context name** (from `kubectl config current-context`). The backend uses the default kubeconfig path from the environment (or `~/.kube/config`) and loads that context.
2. No file content is pasted; no custom path is required beyond the default.

### Step-by-step

1. **Terminal:** Get current context:
   ```bash
   kubectl config current-context
   ```
   Example: `kind-demo`, `minikube`, `gke_my-project_us-central1_my-cluster`.

2. **Browser:** Connect Cluster → **Use default kubeconfig**.

3. **UI:**  
   - **Cluster name:** Any label.  
   - **Context name:** The value from step 1.  
   Click **Save & test connection** → **Test connection** → **Choose namespaces** → **Start watching**.

### Troubleshooting

| Symptom | What to do |
|--------|------------|
| **Kubeconfig not found** | Backend has no default kubeconfig (e.g. no `~/.kube/config` in container). Run backend where that file exists, or mount it and set path, or use **Paste kubeconfig**. |
| **Connection refused** (Docker) | Default kubeconfig usually points to 127.0.0.1. From inside Docker that doesn’t reach the host. Use **Paste kubeconfig** with “App runs in Docker” instead. |

---

## Workflow 4: In-cluster (in depth)

### When to use

- KubeMemory is **deployed inside** the cluster (e.g. as a Deployment with a ServiceAccount).
- No kubeconfig file is needed; the API server and CA are provided by the cluster, and the pod uses the service account token.

### How it works

1. You choose **In-cluster** and give only a **cluster name** (for display).
2. The backend sets `connection_method` to `in_cluster`. When testing or running the watcher, it uses `load_incluster_config()` (Kubernetes client loads the pod’s service account and cluster env).
3. RBAC must allow the service account to list/watch events and get/list pods and namespaces (read-only). Use the project’s in-cluster RBAC manifests if available.

### Step-by-step

1. **Cluster:** Deploy KubeMemory (e.g. apply manifests that create ServiceAccount, RBAC, Deployment). Ensure the pod has the usual in-cluster env (no kubeconfig mount).

2. **Browser:** Connect Cluster → **In-cluster**.

3. **UI:**  
   - **Cluster name:** Any label (e.g. `production`).  
   Click **Save & test connection** → **Test connection** → **Choose namespaces** → **Start watching**.

### Troubleshooting

| Symptom | What to do |
|--------|------------|
| **Not running in cluster** / in-cluster config failed | This workflow only works when the app process runs inside a Kubernetes pod. If you’re on a host or in Docker, use one of the other workflows. |
| **Forbidden** | Service account needs read-only RBAC (list/watch events, get/list pods and namespaces). Apply the correct ClusterRole/ClusterRoleBinding (or namespace-scoped Role/RoleBinding). |

---

## Full flow: Create a cluster → Connect (example with Kind)

Do these in order. Your cluster can be **existing** (default 127.0.0.1) or new (0.0.0.0); both are supported.

| # | Where | What to do |
|---|--------|------------|
| 1 | Terminal | Create or use a Kind cluster: `kind create cluster --name demo` (default 127.0.0.1 is fine), or use `k8s/prod-sim/kind-cluster.yaml` for API on 0.0.0.0. |
| 2 | Terminal | (Optional) Run workloads: `kubectl create deployment nginx --image=nginx --replicas=3`, then `kubectl get pods`. |
| 3 | Terminal | Start KubeMemory: from project root, `docker compose up -d`. |
| 4 | Terminal | **If your Kind cluster uses default 127.0.0.1:** attach the backend to the Kind network. Either run once `docker network connect kind $(docker compose ps -q django-api)`, or next time start with `docker compose -f docker-compose.yml -f docker-compose.kind.yml up -d` (Kind cluster must exist first). Skip if you use API on 0.0.0.0 and “App runs in Docker” only. |
| 5 | Browser | Open app (e.g. http://localhost:5173) → **Connect Cluster**. |
| 6 | UI | **Choose how to connect** → **Paste kubeconfig**. Run `kubectl config view --minify --raw`, copy all, paste in the box. Set cluster name. Check **App runs in Docker**. If the cluster is on 127.0.0.1, check **Use Kind network** (and run the command in step 4 if you haven’t). **Save & test connection**. |
| 7 | UI | **Test connection** → **Choose namespaces** → **Start watching**. |
| 8 | Done | Dashboard; watcher is running. Incidents appear when events occur. |

If **Test connection** fails: use the suggestions on the page (e.g. “Use Kind network” + `docker network connect kind ...`). You do **not** need to recreate the cluster unless you prefer the host method with API on 0.0.0.0.

---

## Quick reference

| Workflow | Get config / context | In UI |
|----------|----------------------|--------|
| Paste kubeconfig | `kubectl config view --minify --raw` → copy | Paste YAML. App in Docker: “App runs in Docker” or **“Use Kind network”** (127.0.0.1 clusters, no recreate). |
| File path | Path backend can read (e.g. `~/.kube/config` or mounted path) | Enter path, optional context |
| Default kubeconfig | `kubectl config current-context` | Enter context name |
| In-cluster | None (pod uses service account) | Cluster name only |

---

## Security and what we access

- **We never:** modify or delete resources, create workloads, access secrets, require cluster-admin or write permissions, or store kubeconfig content in the DB (only paths or on-disk files).
- **We do:** list and watch Events, Pods, Namespaces (read-only); read pod logs when an incident is detected; store incident metadata and embeddings; use kubeconfig only to connect to the API (never logged or exposed).
- **Recommendation:** Use a dedicated service account with minimal read-only RBAC. Run the app in your own environment; we don’t send cluster data to third parties.

In the app, expand **“Security & what we access”** on the Connect page for the same summary.

---

## Troubleshooting (all workflows)

| Error | Likely cause | Fix |
|-------|----------------|-----|
| Connection refused to API server (app in Docker) | Kubeconfig points to 127.0.0.1; container can’t reach host. | **Preferred:** Use **Paste kubeconfig** with **“Use Kind network”** and run `docker network connect kind $(docker compose ps -q django-api)`. No cluster recreate. **Alternative:** Recreate Kind with `apiServerAddress: "0.0.0.0"` and use “App runs in Docker” only. |
| Kubeconfig not found | Path wrong or not visible to backend | Use path the backend/watcher can read; or use **Paste kubeconfig**. |
| Certificate / TLS error | Local cluster cert not for host.docker.internal or control-plane hostname | Use Paste with “App runs in Docker” or “Use Kind network” so we add `insecure-skip-tls-verify`. |
| Start watching: 500 / watcher not starting | Backend can’t write active kubeconfig or start subprocess | Ensure writable path for active kubeconfig (e.g. `/app/kubeconfigs`); check backend logs. |
| Forbidden (RBAC) | Service account or user lacks read permission | Grant list/watch events, get/list pods and namespaces (read-only). Apply `k8s/rbac.yaml` or equivalent. |
| No events in dashboard | Cluster healthy or namespaces wrong | Trigger an event (e.g. delete a pod); ensure selected namespaces include where workloads run. |
