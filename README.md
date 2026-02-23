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

## License

MIT
