# KubeMemory-AI

Persistent AI brain for Kubernetes clusters: ingest incidents, store in ChromaDB + Neo4j, and run a LangGraph pipeline (Retriever → Correlator → Recommender) to produce cluster-grounded recommendations.

## Stack

- **Backend:** Django 4.2, DRF, Celery, Channels, LangGraph, Ollama
- **Memory:** ChromaDB (vector), Neo4j (graph)
- **Frontend:** React 18, Vite, TailwindCSS, Zustand, React Query

## Quick start

```bash
cp .env.example .env   # edit with your secrets (never commit .env)
docker compose up -d --build
# Wait for ollama-init to pull models, then:
docker compose exec django-api python manage.py migrate
docker compose exec django-api python manage.py seed_test_incidents
docker compose exec django-api python manage.py test_pipeline --incident-id 1
```

## Real-time quickstart (Linux)

To **clone, create a Kind cluster, and see the app work in real time** on a Linux system, follow **[Step-by-Step: Real Time on Linux](docs/REALTIME_LINUX_QUICKSTART.md)**.

## Connecting your cluster

To connect a Kubernetes cluster (Kind, EKS, GKE, AKS, or in-cluster), see **[How to Connect Your Cluster](docs/CLUSTER_CONNECT.md)**. Use the **Connect Cluster** wizard in the dashboard (`/connect`) or follow the guide for manual setup.

## License

MIT
