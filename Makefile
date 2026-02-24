.PHONY: help dev down logs shell migrate makemigrations test lint \
        watcher celery seed verify-memory test-pipeline mcp-server \
        k8s-up k8s-down k8s-test clean build-prod

help:
	@echo "KubeMemory Developer Commands"
	@echo "────────────────────────────────────────────────"
	@echo "  make dev              Start all services (dev)"
	@echo "  make down              Stop all services"
	@echo "  make logs              Tail all logs"
	@echo "  make shell             Django shell"
	@echo "  make migrate           Run migrations"
	@echo "  make makemigrations    Create new migrations"
	@echo ""
	@echo "  make seed              Seed 20 test incidents + embed all"
	@echo "  make verify-memory     Check ChromaDB + Neo4j health"
	@echo "  make test-pipeline     Test LangGraph on incident #1"
	@echo "  make mcp-server        Start MCP server for Claude Desktop"
	@echo ""
	@echo "  make k8s-up            Create kind cluster"
	@echo "  make k8s-down         Delete kind cluster"
	@echo "  make k8s-test          Deploy test crash workloads"
	@echo ""
	@echo "  make build-prod       Build production images"
	@echo "  make clean             Remove volumes + images"

dev:
	cp -n .env.example .env 2>/dev/null || true
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=50

shell:
	docker compose exec django-api python manage.py shell_plus

migrate:
	docker compose exec django-api python manage.py migrate

makemigrations:
	docker compose exec django-api python manage.py makemigrations

test:
	docker compose exec django-api python manage.py test apps/ -v 2

lint:
	docker compose exec django-api flake8 apps/ config/ --max-line-length=100

seed:
	docker compose exec django-api python manage.py seed_test_incidents

verify-memory:
	docker compose exec django-api python manage.py verify_memory

test-pipeline:
	docker compose exec django-api python manage.py test_pipeline --incident-id 1

mcp-server:
	cd backend && python manage.py run_mcp

watcher:
	docker compose exec django-api python manage.py run_watcher

k8s-up:
	kind create cluster --config k8s/kind-cluster.yaml
	kubectl apply -f k8s/rbac.yaml
	@echo "✓ Kind cluster ready. Run 'make watcher' to start watching."

k8s-down:
	kind delete cluster --name kubememory

k8s-test:
	kubectl apply -f k8s/test-workloads/

build-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build

clean:
	docker compose down -v --remove-orphans
	docker system prune -f
