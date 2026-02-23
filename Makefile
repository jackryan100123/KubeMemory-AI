.PHONY: dev down logs shell migrate makemigrations test lint watcher celery seed_test_incidents verify_memory

dev:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f

shell:
	docker compose exec django-api python manage.py shell

migrate:
	docker compose exec django-api python manage.py migrate

makemigrations:
	docker compose exec django-api python manage.py makemigrations

test:
	docker compose exec django-api python manage.py test apps/

lint:
	docker compose exec django-api flake8 apps/ config/

watcher:
	docker compose exec django-api python manage.py run_watcher

celery:
	docker compose exec celery-worker celery -A config inspect active

seed_test_incidents:
	docker compose exec django-api python manage.py seed_test_incidents

verify_memory:
	docker compose exec django-api python manage.py verify_memory
