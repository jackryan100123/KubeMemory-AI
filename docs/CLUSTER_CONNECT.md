# Connect Your Cluster to KubeMemory

This guide explains **all four connection workflows** in depth: when to use each, how they work, and how to connect from start to finish.

KubeMemory needs **read-only** access to your cluster (events, pods, namespaces, pod logs for context). It never modifies or deletes resources and never accesses secrets.

---

## Overview: Four connection workflows

| Workflow | When to use it | What you provide |
|----------|----------------|------------------|
| **Paste kubeconfig** | You have an existing cluster and can run `kubectl` (Kind, Minikube, any cluster). Easiest when the app runs in Docker. | Cluster name + pasted YAML from `kubectl config view --minify --raw`. Option: “App runs in Docker” so we rewrite the API server for the container. |
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
3. If you check **“App runs in Docker”**, we:
   - Replace `127.0.0.1` and `0.0.0.0` in the `server:` URL with `host.docker.internal` so the container can reach the host’s cluster.
   - Add `insecure-skip-tls-verify: true` under that server (needed for local clusters whose cert isn’t for `host.docker.internal`).
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
   - **App runs in Docker:** Check this if KubeMemory runs in Docker and the cluster is on the same machine (or the host that Docker uses).  
   Click **Save & test connection**.

4. **UI:** Click **Test connection**. If it fails, see troubleshooting below.

5. **UI:** Click **Choose namespaces** → select namespaces → **Start watching**. The watcher starts automatically.

### Important for local clusters (Kind / Minikube) when app is in Docker

- The cluster’s API server must be reachable from the container. By default, Kind/Minikube bind the API to `127.0.0.1`; from inside a container, `127.0.0.1` is the container itself, so connection fails.
- **Fix:** Create the cluster so the API listens on **0.0.0.0** (all interfaces). For Kind, use a config with `networking.apiServerAddress: "0.0.0.0"` (and optionally `apiServerPort: 6443`), then recreate the cluster. After that, “App runs in Docker” + paste works.

### Troubleshooting

| Symptom | What to do |
|--------|------------|
| Test connection: **Connection refused** to `host.docker.internal` | Cluster API is still bound to 127.0.0.1. Recreate cluster with API on 0.0.0.0 (Kind: use a config with `apiServerAddress: "0.0.0.0"`). Then get kubeconfig again and paste with “App runs in Docker” checked. |
| Test connection: **Certificate / TLS** error | Ensure “App runs in Docker” is checked so we add `insecure-skip-tls-verify: true` for local clusters. |
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

Do these in order.

| # | Where | What to do |
|---|--------|------------|
| 1 | Terminal | Create Kind cluster with API on 0.0.0.0 so Docker can reach it: e.g. create a config with `networking.apiServerAddress: "0.0.0.0"` and `apiServerPort: 6443`, then `kind create cluster --config <config>.yaml`. Or use project `k8s/prod-sim/kind-cluster.yaml`. |
| 2 | Terminal | Run workloads: `kubectl create deployment nginx --image=nginx --replicas=3`, then `kubectl get pods`. |
| 3 | Terminal | Start KubeMemory: from project root, `docker compose up -d`. |
| 4 | Browser | Open app (e.g. http://localhost:5173) → **Connect Cluster**. |
| 5 | UI | **Choose how to connect** → **Paste kubeconfig**. Run `kubectl config view --minify --raw`, copy all, paste in the box. Set cluster name. Check **App runs in Docker**. **Save & test connection**. |
| 6 | UI | **Test connection** → **Choose namespaces** → **Start watching**. |
| 7 | Done | Dashboard; watcher is running. Incidents appear when events occur. |

If **Test connection** fails with connection refused, recreate the cluster with the API on 0.0.0.0, then paste again with “App runs in Docker” checked.

---

## Quick reference

| Workflow | Get config / context | In UI |
|----------|----------------------|--------|
| Paste kubeconfig | `kubectl config view --minify --raw` → copy | Paste YAML, optional “App runs in Docker” |
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
| Connection refused to API server | App in Docker, kubeconfig points to 127.0.0.1 | Use **Paste kubeconfig** with “App runs in Docker”, or create kubeconfig with `host.docker.internal` and `insecure-skip-tls-verify`. For Kind, recreate cluster with `apiServerAddress: "0.0.0.0"`. |
| Kubeconfig not found | Path wrong or not visible to backend | Use path the backend/watcher can read; or use **Paste kubeconfig**. |
| Certificate / TLS error | Local cluster cert not for host.docker.internal | Use Paste with “App runs in Docker” so we add `insecure-skip-tls-verify`. |
| Start watching: 500 / watcher not starting | Backend can’t write active kubeconfig or start subprocess | Ensure writable path for active kubeconfig (e.g. `/app/kubeconfigs`); check backend logs. |
| Forbidden (RBAC) | Service account or user lacks read permission | Grant list/watch events, get/list pods and namespaces (read-only). Apply `k8s/rbac.yaml` or equivalent. |
| No events in dashboard | Cluster healthy or namespaces wrong | Trigger an event (e.g. delete a pod); ensure selected namespaces include where workloads run. |
