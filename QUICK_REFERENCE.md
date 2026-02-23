# KubeMemory — Developer Quick Reference
# Keep this open in a tab while building

## PHASE SEQUENCE
Phase 1 → Scaffold + K8s Watcher (Week 1-2)
Phase 2 → ChromaDB + Neo4j Memory (Week 3-4)
Phase 3 → LangGraph Agents (Week 5-6)
Phase 4 → React Dashboard (Week 7-8)
Phase 5 → MCP Server + Hardening (Week 9-10)

## KEY RULE — NEVER DO THESE
✗ Hardcode any password/token/key in any file
✗ Use `os.environ["KEY"]` — always use `os.environ.get("KEY")`
✗ Commit .env file (only .env.example)
✗ Use `:latest` Docker tags in production
✗ Run containers as root
✗ Direct fetch() calls in React components
✗ useState for server data (use React Query)
✗ Add features from future phases

## KEY SERVICES & PORTS
┌─────────────────────────┬──────────┐
│ Service                 │ Port     │
├─────────────────────────┼──────────┤
│ Django API              │ 8000     │
│ React Frontend          │ 5173     │
│ Neo4j Browser           │ 7474     │
│ Neo4j Bolt              │ 7687     │
│ Ollama                  │ 11434    │
│ Postgres                │ 5432     │
│ Redis                   │ 6379     │
└─────────────────────────┴──────────┘

## ENVIRONMENT VARIABLES CHEAT SHEET
# Django
DJANGO_SECRET_KEY          → python -c "import secrets; print(secrets.token_hex(32))"
DJANGO_SETTINGS_MODULE     → config.settings.dev (or prod)

# DB
POSTGRES_DB/USER/PASSWORD/HOST/PORT

# Redis / Celery
REDIS_URL                  → redis://redis:6379/0
CELERY_BROKER_URL          → redis://redis:6379/1

# AI (all point to local services)
OLLAMA_BASE_URL            → http://ollama:11434
OLLAMA_CHAT_MODEL          → mistral:7b
OLLAMA_EMBED_MODEL         → nomic-embed-text

# Memory
CHROMA_PERSIST_DIR         → /app/chroma_data
CHROMA_COLLECTION_NAME     → kubememory_incidents
NEO4J_URI                  → bolt://neo4j:7687
NEO4J_USER                 → neo4j
NEO4J_PASSWORD             → <your-strong-password>

# K8s
K8S_IN_CLUSTER             → False (dev) | True (in-cluster)
K8S_NAMESPACES             → default,production,staging

## MAKE COMMANDS CHEAT SHEET
make dev              → start everything
make down             → stop everything
make migrate          → run django migrations
make shell            → django shell_plus
make seed             → seed 20 test incidents
make verify-memory    → check ChromaDB + Neo4j
make test-pipeline    → run LangGraph on incident #1
make k8s-up           → create kind cluster
make k8s-test         → deploy crash test pods
make mcp-server       → start MCP for Claude Desktop

## API ENDPOINTS REFERENCE
# Incidents
GET    /api/incidents/                    → list all
GET    /api/incidents/{id}/               → detail + AI analysis
PATCH  /api/incidents/{id}/              → update status
POST   /api/incidents/{id}/fixes/         → submit fix

# Memory
GET    /api/memory/search/?q=<query>      → semantic search
GET    /api/memory/graph/?namespace=<ns>  → graph data (React Force Graph)
GET    /api/memory/blast-radius/          → pod blast radius
GET    /api/memory/patterns/              → deploy-crash correlations

# Agents
POST   /api/agents/analyze/{id}/          → trigger re-analysis
GET    /api/agents/analysis/{id}/         → get stored analysis
GET    /api/agents/status/                → pipeline health check

# WebSocket
ws://localhost:8000/ws/incidents/         → real-time incident stream

## WEBSOCKET MESSAGE TYPES
// Server → Client
{ type: "new_incident",     data: {...incident} }
{ type: "analysis_complete", incident_id: N, analysis: "...", confidence: 0.87 }

## DJANGO APP STRUCTURE
apps/incidents/    → models, serializers, views, tasks
apps/memory/       → vector_store.py, graph_builder.py
apps/agents/       → agents.py, pipeline.py, state.py
apps/watcher/      → management/commands/run_watcher.py
apps/mcp_server/   → server.py, run_server.py
apps/ws/           → consumers.py

## REACT FILE STRUCTURE
src/api/           → client.js, incidents.js (ALL API calls here)
src/hooks/         → useWebSocket.js, useIncidents.js, useGraphData.js
src/store/         → incidentStore.js (Zustand — WS buffer, UI state only)
src/pages/         → Dashboard, IncidentDetail, GraphExplorer, Patterns
src/components/    → incidents/, graph/, patterns/, shared/

## CORRECTIVE RAG LOOP (how it works)
1. AI gives recommendation for incident
2. Engineer applies DIFFERENT fix that actually works
3. Engineer checks "AI was wrong" in fix form
4. Frontend sends: POST /api/incidents/{id}/fixes/ with correction_of=<ai_fix_id>
5. update_corrective_rag_task runs → embeds correction in ChromaDB
6. Next similar incident → correction surfaces in retrieval → AI uses it

## NEO4J CYPHER QUICK QUERIES (test in Neo4j browser)
# See all incidents
MATCH (i:Incident) RETURN i LIMIT 25

# See causal graph for a pod
MATCH (p:Pod {name: "payment-service"})<-[:AFFECTED]-(i:Incident)
OPTIONAL MATCH (i)-[:RESOLVED_BY]->(f:Fix)
RETURN p, i, f

# Find blast radius
MATCH (i1:Incident)-[:AFFECTED]->(p1:Pod)
MATCH (i2:Incident)-[:AFFECTED]->(p2:Pod)
WHERE abs(i1.timestamp.epochMillis - i2.timestamp.epochMillis) < 300000
AND p1.name <> p2.name
RETURN p1.name, p2.name, count(*) as co_occurrence
ORDER BY co_occurrence DESC

## CHROMADB QUICK TEST (Django shell)
from apps.memory.vector_store import IncidentVectorStore
vs = IncidentVectorStore()
results = vs.search_similar("payment service out of memory", n_results=3)
for r in results: print(r['metadata']['pod_name'], r['score'])

## DOCKER IMAGE SIZE TARGETS
Backend runtime image: < 500MB
Frontend nginx image: < 50MB
(Check with: docker images kubememory-*)

## SECURITY CHECKLIST (run before any commit)
git status                              # nothing unexpected staged
grep -r "password" . --include="*.py" | grep -v ".env" | grep -v "os.environ"
grep -r "SECRET" . --include="*.js"
grep -r "localhost:7687" . --include="*.py"  # should be 0 results
docker run --rm kubememory-django id    # should show uid=1001(appuser)
