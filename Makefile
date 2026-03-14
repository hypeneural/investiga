.PHONY: install lint format test test-unit test-e2e api worker migrate makemigration doctor import-legacy infra infra-down

# ── Setup ──────────────────────────────────────────────────
install:
	pip install -e ".[dev]"
	playwright install chromium

# ── Code Quality ───────────────────────────────────────────
lint:
	ruff check .
	mypy packages/ apps/

format:
	ruff format .
	ruff check --fix .

# ── Tests ──────────────────────────────────────────────────
test:
	pytest -n auto

test-unit:
	pytest packages/*/tests -n auto

test-e2e:
	pytest tests/e2e -v

# ── Services ───────────────────────────────────────────────
api:
	uvicorn investiga_api.main:app --reload --host 0.0.0.0 --port 8000

worker:
	python -m investiga_workers.main

# ── Database ───────────────────────────────────────────────
migrate:
	alembic upgrade head

makemigration:
	alembic revision --autogenerate -m "$(m)"

# ── CLI ────────────────────────────────────────────────────
doctor:
	python -m investiga_cli.main doctor

import-legacy:
	python -m investiga_cli.main import-legacy-json

# ── Infrastructure ─────────────────────────────────────────
infra:
	docker compose -f infra/docker/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker/docker-compose.yml down
