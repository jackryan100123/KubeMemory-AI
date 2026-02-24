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

[link to architecture diagram]

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

## Security Notes

- All secrets via environment variables — no hardcoded credentials
- Non-root Docker containers
- K8s RBAC: watcher has read-only access (pods, events, namespaces only)
- No cloud API calls — everything runs locally

## More Documentation

- **[Step-by-Step: Real Time on Linux](docs/REALTIME_LINUX_QUICKSTART.md)** — clone, Kind cluster, real-time alerts
- **[How to Connect Your Cluster](docs/CLUSTER_CONNECT.md)** — Connect wizard or manual setup
- **[Connectivity In Depth](docs/CONNECTIVITY_IN_DEPTH.md)** — network and connectivity details

## License

MIT
