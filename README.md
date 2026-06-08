# KubeMemory

> A persistent AI brain for Kubernetes clusters — powered by GraphRAG,
> LangGraph agents, and a local LLM. Zero cloud cost.

[screenshot placeholder]

## The Problem It Solves

Every K8s tool (K8sGPT, Datadog, PagerDuty) is stateless and amnesiac.
Every incident is treated as if it never happened before.

KubeMemory gives your cluster a persistent memory of every incident,
learns from every fix, and uses GraphRAG + multi-agent reasoning to give
you historically-aware troubleshooting that gets smarter over time.

## Architecture

```
┌─────────────┐     events      ┌──────────────┐     Celery ingest    ┌─────────────┐
│  Kubernetes │ ──────────────► │ K8s Watcher  │ ──────────────────► │ Django API  │
│   Cluster   │                 │  (run_watcher)│                     │ + Postgres  │
└─────────────┘                 └──────────────┘                     └──────┬──────┘
                                                                            │
                    ┌───────────────────────────────────────────────────────┤
                    ▼                       ▼                               ▼
             ┌────────────┐         ┌────────────┐                  ┌──────────────┐
             │  ChromaDB  │         │   Neo4j    │                  │ Celery (llm) │
             │  (vectors) │         │  (graph)   │                  │ LangGraph    │
             └────────────┘         └────────────┘                  └──────┬───────┘
                                                                            │
                    ┌───────────────────────────────────────────────────────┘
                    ▼
             ┌────────────┐    WebSocket     ┌─────────────┐
             │   Ollama   │ ◄─────────────── │ React UI    │
             │  (local)   │                  │ (Vite/nginx)│
             └────────────┘                  └─────────────┘
```

- **K8s Watcher** → streams cluster events in real-time
- **ChromaDB** → vector semantic search over past incidents
- **Neo4j** → causal knowledge graph (who crashes with whom, deploy correlations)
- **LangGraph** → 3 agents: Retriever, Correlator, Recommender
- **Corrective RAG** → learns when engineers override AI recommendations
- **MCP Server** → Claude Desktop can query your cluster with full context
- **Django + React** → real-time dashboard via WebSockets

## Quick Start (5 minutes)

### Prerequisites

- Docker + Docker Compose
- kind (for local K8s)
- 8GB RAM (Ollama needs ~4GB for Mistral 7B)

### Run it

```bash
git clone https://github.com/yourname/kubememory
cd kubememory
make dev        # starts everything, auto-pulls Ollama models
make k8s-up     # creates local Kind cluster
make seed       # seeds 20 test incidents
make k8s-test   # deploys crashloop + OOM test pods (if k8s/test-workloads/ exists)
```

Open: http://localhost:5173

### Use with Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kubememory": {
      "command": "python",
      "args": ["path/to/kubememory/backend/manage.py", "run_mcp"],
      "env": { "see .env.example for required variables" }
    }
  }
}
```

Then ask Claude: *"What caused the payment service to crash last night?"*

## Tech Stack (100% Zero Cost)

| Layer   | Tech                    |
|--------|--------------------------|
| LLM    | Ollama + Mistral 7B (local) |
| Vector DB | ChromaDB (embedded)   |
| Graph DB | Neo4j Community       |
| Agents | LangGraph              |
| Backend | Django + Channels + Celery |
| Frontend | React + Vite + Tailwind |
| K8s    | Kind (local)           |

## Environment Setup

Copy `.env.example` to `.env` and fill in values.
Never commit `.env` — it's in `.gitignore`.

## Security

- **JWT authentication** — all `/api/*` routes require a Bearer token except `/api/health/` and `/api/token/`. Sign in at `/login` (dev user: set `DEV_ADMIN_USERNAME` / `DEV_ADMIN_PASSWORD` in `.env`, then `python manage.py ensure_dev_admin`).
- **Encrypted kubeconfig** — pasted cluster credentials are stored with `FERNET_KEY` (generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`). Set `FERNET_KEY` in `.env` before migrations.
- **RBAC roles** — `viewer`, `operator`, `admin` on `UserProfile`; operators required for watcher connect/start; viewers cannot mutate production clusters.
- All other secrets via environment variables — never commit `.env`
- Non-root Docker containers; K8s watcher uses read-only RBAC

## Monitoring

- **Watcher heartbeat** — Redis key `watcher:heartbeat:<cluster_id>` (45s TTL); `/status` shows green when heartbeat is under 45 seconds old
- **Task logs** — failed Celery tasks at `/api/monitoring/task-logs/` and on the Status page
- **Ollama readiness** — `ollama:ready` in Redis; exposed on `/api/status/` as `ollama_ready`
- **Notifications** — configure Slack/webhook sinks under Settings → Notifications

## More Documentation

- **[Connect Your Cluster](docs/CLUSTER_CONNECT.md)** — all connection workflows (paste, file path, context, in-cluster), step-by-step and troubleshooting

## License

MIT
