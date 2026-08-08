# Bharat OS — development entrypoints.
#
# `make test` runs the entire suite, backend and frontend, and is what CI runs.

.DEFAULT_GOAL := help
SHELL := /bin/bash

BACKEND  := backend
FRONTEND := frontend
VENV     := $(BACKEND)/.venv
PY       := $(VENV)/bin/python
PYTEST   := $(VENV)/bin/pytest
ALEMBIC  := $(VENV)/bin/alembic
RUFF     := $(VENV)/bin/ruff
UVICORN  := $(VENV)/bin/uvicorn

.PHONY: help
help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

.PHONY: install
install: install-backend install-frontend ## Install all dependencies

.PHONY: install-backend
install-backend: ## Create the backend venv and install dependencies
	cd $(BACKEND) && uv venv --python 3.11 .venv && uv pip install -e '.[dev]'

.PHONY: install-frontend
install-frontend: ## Install frontend dependencies
	cd $(FRONTEND) && npm install

# ---------------------------------------------------------------------------
# Tests — the single command that must stay green
# ---------------------------------------------------------------------------

.PHONY: test
test: test-backend test-frontend ## Run the full test suite (unit and integration)

.PHONY: test-backend
test-backend: ## Run backend tests
	cd $(BACKEND) && .venv/bin/pytest -q

.PHONY: test-frontend
test-frontend: ## Run frontend tests
	cd $(FRONTEND) && npm run --silent test

.PHONY: test-e2e
test-e2e: ## Run browser end-to-end tests (needs the bharat_os_e2e database)
	cd $(FRONTEND) && npx playwright test

.PHONY: test-all
test-all: test test-e2e ## Everything, including the browser journey

.PHONY: demo-discover
demo-discover: ## Inspect live demo controls before changing the recording script
	cd $(FRONTEND) && BHARAT_OS_DEMO_MODE=discover npm run --silent demo:assets

.PHONY: demo-rehearse
demo-rehearse: ## Verify every demo selector without recording media
	cd $(FRONTEND) && BHARAT_OS_DEMO_MODE=rehearse npm run --silent demo:assets

.PHONY: demo-assets
demo-assets: demo-rehearse ## Rehearse, then regenerate README screenshots and demo video
	cd $(FRONTEND) && BHARAT_OS_DEMO_MODE=record npm run --silent demo:assets

.PHONY: lint
lint: ## Lint and type-check both sides
	cd $(BACKEND) && .venv/bin/ruff check src tests
	cd $(FRONTEND) && npm run --silent lint && npm run --silent typecheck

.PHONY: format
format: ## Auto-fix formatting
	cd $(BACKEND) && .venv/bin/ruff format src tests && .venv/bin/ruff check --fix src tests

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

.PHONY: migrate
migrate: ## Apply migrations up to head
	cd $(BACKEND) && .venv/bin/alembic upgrade head

.PHONY: migrate-down
migrate-down: ## Roll back one migration
	cd $(BACKEND) && .venv/bin/alembic downgrade -1

.PHONY: revision
revision: ## Autogenerate a migration: make revision m="add widget table"
	@test -n "$(m)" || (echo "usage: make revision m=\"description\"" && exit 1)
	cd $(BACKEND) && .venv/bin/alembic revision --autogenerate -m "$(m)"

.PHONY: seed
seed: ## Load the curated scheme corpus (idempotent)
	cd $(BACKEND) && .venv/bin/python -m bharat_os.seed.load

.PHONY: seed-crawl-sources
seed-crawl-sources: ## Load the curated crawl source list (idempotent)
	cd $(BACKEND) && .venv/bin/python -m bharat_os.seed.load_crawl_sources

.PHONY: crawl
crawl: ## Crawl every active source once, queuing detected changes for review
	cd $(BACKEND) && .venv/bin/python -m bharat_os.scripts.crawl_all

.PHONY: calibration
calibration: ## Report whether stated confidence tracks reality
	cd $(BACKEND) && .venv/bin/python -m bharat_os.scripts.calibration_report

.PHONY: calibration-real
calibration-real: ## Same, against recorded application outcomes
	cd $(BACKEND) && .venv/bin/python -m bharat_os.scripts.calibration_report --real

.PHONY: demo
demo: ## Evaluate sample personas against the whole corpus, no AI involved
	cd $(BACKEND) && .venv/bin/python -m bharat_os.scripts.demo_eligibility

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

.PHONY: dev-backend
dev-backend: ## Run the API with reload on :8000
	cd $(BACKEND) && .venv/bin/uvicorn bharat_os.main:app --reload --port 8000

.PHONY: dev-frontend
dev-frontend: ## Run the dashboard on :3000
	cd $(FRONTEND) && npm run dev

# ---------------------------------------------------------------------------
# Shared type contract
# ---------------------------------------------------------------------------

.PHONY: types
types: ## Regenerate frontend types from the backend OpenAPI spec
	cd $(BACKEND) && .venv/bin/python -m bharat_os.scripts.export_openapi ../openapi.json
	cd $(FRONTEND) && npm run --silent generate-types

.PHONY: clean
clean: ## Remove caches, local databases and generated artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.hypothesis
	rm -f $(BACKEND)/*.db openapi.json
	rm -rf $(FRONTEND)/.next

# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------

.PHONY: docker-build
docker-build: ## Build both container images
	docker build -t bharat-os-backend ./backend
	docker build -t bharat-os-frontend ./frontend

.PHONY: docker-up
docker-up: ## Run the full stack via docker compose (needs .env.production)
	docker compose --env-file .env.production up --build

.PHONY: docker-down
docker-down: ## Stop the docker compose stack
	docker compose down

.PHONY: backup
backup: ## Back up the database (requires BHARAT_OS_DATABASE_URL for Postgres)
	cd $(BACKEND) && ./scripts/backup.sh

.PHONY: restore
restore: ## Restore from a backup: make restore file=backups/bharat_os_....dump
	@test -n "$(file)" || (echo "usage: make restore file=path/to/backup.dump" && exit 1)
	cd $(BACKEND) && ./scripts/restore.sh ../$(file)
