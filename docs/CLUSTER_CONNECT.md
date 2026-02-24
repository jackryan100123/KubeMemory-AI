# How to Connect Your Cluster to KubeMemory

KubeMemory's watcher needs read-only access to your cluster.
Here's exactly how to set it up for each scenario.

**For a deep dive** (how connectivity works, Kind + 1 worker + nginx in `default`, watcher on host vs in Docker), see **[Connectivity In Depth](CONNECTIVITY_IN_DEPTH.md)**.

---

## Option A — Local Kind Cluster (Recommended for Testing)

### Step 1: Create the cluster

```bash
cd k8s/prod-sim
./bootstrap.sh
```

### Step 2: Verify kubeconfig

```bash
kubectl config current-context
# Should show: kind-kubememory-prod-sim

kubectl get nodes
# Should show 4 nodes (1 control-plane + 3 workers)
```

### Step 3: Set env vars

In your `.env` file:

```
K8S_IN_CLUSTER=False
K8S_KUBECONFIG_PATH=/Users/yourname/.kube/config
K8S_NAMESPACES=production,staging,data-pipeline
```

### Step 4: Start watcher

```bash
make watcher
# You should see:
# [watcher] Connected to kind-kubememory-prod-sim
# [watcher] Watching namespaces: production, staging, data-pipeline
# [watcher] Event captured: CrashLoopBackOff on payment-service
```

---

## Option B — Remote Cluster (EKS / GKE / AKS)

### Step 1: Get your kubeconfig

```bash
# EKS
aws eks update-kubeconfig --name my-cluster --region us-east-1

# GKE
gcloud container clusters get-credentials my-cluster --region us-central1

# AKS
az aks get-credentials --resource-group my-rg --name my-cluster
```

### Step 2: Apply RBAC (read-only)

```bash
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/serviceaccount.yaml
```

### Step 3: Verify permissions

```bash
kubectl auth can-i list pods --as=system:serviceaccount:default:kubememory-watcher
# Should say: yes

kubectl auth can-i delete pods --as=system:serviceaccount:default:kubememory-watcher
# Should say: no  ← this is correct, we have no write access
```

### Step 4: Set env vars

```
K8S_IN_CLUSTER=False
K8S_KUBECONFIG_PATH=/Users/yourname/.kube/config
K8S_NAMESPACES=production,staging
```

---

## Option C — In-Cluster (Deploy KubeMemory as a Pod)

Use this when you want KubeMemory to run INSIDE the cluster itself.

```bash
# Apply the service account with in-cluster RBAC
kubectl apply -f k8s/in-cluster-rbac.yaml

# Set in .env:
K8S_IN_CLUSTER=True
```

The watcher will auto-discover the cluster via the mounted service account token.

---

## Verifying Events Are Flowing

After connecting, check:

```bash
# 1. Watcher shows events
make watcher
# → [watcher] CrashLoopBackOff: payment-service (production)

# 2. API has incidents
curl http://localhost:8000/api/incidents/ | python -m json.tool

# 3. Dashboard shows live feed
# Open http://localhost:5173 — you should see red alerts

# 4. Memory is populated
make verify-memory
# ✓ ChromaDB: N documents
# ✓ Neo4j: N incidents in graph
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `connection refused at 6443` | Docker not running or cluster stopped. Run `kind get clusters` |
| `Forbidden: pods is forbidden` | RBAC not applied. Run `kubectl apply -f k8s/rbac.yaml` |
| `no such file: ~/.kube/config` | Kubeconfig missing. Run the appropriate cloud CLI command above |
| `watcher connects but no events` | Pods are healthy. Apply test workloads: `kubectl apply -f k8s/prod-sim/workloads/` |
| `Ollama not responding` | Run `docker compose up ollama` and wait for model pull to finish |
