PYTHON ?= python3.12
NPM ?= npm
BACKEND := backend
FRONTEND := frontend
PY := $(BACKEND)/.venv/bin
API := $(PY)/python
ALEMBIC := $(PY)/alembic

.PHONY: help setup setup-backend setup-frontend dev-backend dev-frontend \
        migrate migration test test-backend test-frontend lint lint-backend \
        lint-frontend typecheck typecheck-backend typecheck-frontend build \
        check-migrations check

help:
	@grep -E '^[a-z-]+:' $(MAKEFILE_LIST) | sed 's/:.*//' | sort | column -c 100

setup: setup-backend setup-frontend

$(BACKEND)/.venv/.installed: $(BACKEND)/pyproject.toml
	$(PYTHON) -m venv $(BACKEND)/.venv
	$(PY)/pip install --upgrade pip
	$(PY)/pip install -e '$(BACKEND)[dev]'
	@touch $@

setup-backend: $(BACKEND)/.venv/.installed

dev-backend:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

migrate:
	cd $(BACKEND) && .venv/bin/alembic upgrade head

migration:
	@test -n "$(m)" || (echo 'usage: make migration m="description"' && exit 1)
	cd $(BACKEND) && .venv/bin/alembic revision --autogenerate -m "$(m)"

check-migrations:
	cd $(BACKEND) && .venv/bin/python scripts/check_migrations.py

test-backend:
	cd $(BACKEND) && .venv/bin/pytest -q

lint-backend:
	cd $(BACKEND) && .venv/bin/ruff check . && .venv/bin/ruff format --check .

typecheck-backend:
	cd $(BACKEND) && .venv/bin/mypy app

setup-frontend:
	cd $(FRONTEND) && $(NPM) ci

dev-frontend:
	cd $(FRONTEND) && $(NPM) run dev

test-frontend:
	cd $(FRONTEND) && $(NPM) run test

lint-frontend:
	cd $(FRONTEND) && $(NPM) run lint && $(NPM) run format:check

typecheck-frontend:
	cd $(FRONTEND) && $(NPM) run typecheck

build:
	cd $(FRONTEND) && $(NPM) run build

