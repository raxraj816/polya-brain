PYTHON ?= python3
VENV ?= .venv
PYTHON_BIN := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
ALEMBIC := $(VENV)/bin/alembic
INSTALL_STAMP := $(VENV)/.installed

.PHONY: setup install dev test lint format typecheck migrate db-seed db-smoke db-test docker-up docker-down proof clean

$(PYTHON_BIN):
	$(PYTHON) -m venv $(VENV)

$(INSTALL_STAMP): pyproject.toml $(PYTHON_BIN)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	touch $(INSTALL_STAMP)

setup: $(INSTALL_STAMP)

install: setup

dev: setup
	$(UVICORN) app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

test: setup
	$(PYTHON_BIN) -m pytest

lint: setup
	$(PYTHON_BIN) -m ruff check .
	$(PYTHON_BIN) -m ruff format --check backend
	$(PYTHON_BIN) -m mypy

format: setup
	$(PYTHON_BIN) -m ruff check . --fix
	$(PYTHON_BIN) -m ruff format backend

typecheck: setup
	$(PYTHON_BIN) -m mypy

migrate: setup
	$(ALEMBIC) upgrade head

db-seed: setup
	$(PYTHON_BIN) -m app.db.seed

db-smoke: setup
	$(PYTHON_BIN) -m app.db.smoke

db-test: setup
	POLYABRAIN_RUN_DB_TESTS=1 $(PYTHON_BIN) -m pytest backend/tests/test_database_baseline.py

docker-up:
	docker compose up --build --wait --wait-timeout 60

docker-down:
	docker compose down

proof:
	$(PYTHON) proofs/pre_platform/verify_pre_platform_proof.py --all

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache
