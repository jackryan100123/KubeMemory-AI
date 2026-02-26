#!/bin/bash
# =====================================================================
# KubeMemory Production-Sim Cluster Bootstrap
# Run this once to create a fully loaded test cluster
# =====================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[kubememory]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check prerequisites
command -v kind >/dev/null || error "kind not installed. Run: brew install kind"
command -v kubectl >/dev/null || error "kubectl not installed. Run: brew install kubectl"
command -v docker >/dev/null || error "Docker not running"

log "Creating production-sim Kind cluster..."
kind create cluster --config kind-cluster.yaml

log "Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

log "Creating namespaces..."
kubectl apply -f namespaces.yaml

log "Deploying workloads (these will start generating events)..."
kubectl apply -f workloads/

log "Waiting 10s for pods to start crashing..."
sleep 10

log "Current cluster state:"
kubectl get pods --all-namespaces

echo ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Cluster ready! Events will start flowing in ~60 seconds."
log ""
log "Next steps:"
log "  1. Set kubeconfig: kind get kubeconfig --name kubememory-prod-sim > ~/.kube/kind-kubememory-config"
log "     then: export KUBECONFIG=~/.kube/kind-kubememory-config"
log "  2. From project root: docker compose up -d && make migrate"
log "  3. Connect in UI: http://localhost:5173 → Connect Cluster (see docs/CLUSTER_CONNECT.md)"
log "  4. Watch events: kubectl get events --all-namespaces -w"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
