PYTHON ?= python3
VENV ?= .venv
PYTHON_BIN := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
ALEMBIC := $(VENV)/bin/alembic
INSTALL_STAMP := $(VENV)/.installed

.PHONY: check-python check-venv setup install dev test lint format typecheck migrate db-seed db-smoke db-test docker-up docker-down proof chapter11-proof clean

check-python:
	@$(PYTHON) -c 'import sys; v=sys.version_info; ok=(3, 14) <= v[:2] < (3, 15); sys.exit(0 if ok else f"PolyaBrain requires Python >=3.14,<3.15; {sys.executable} is {v.major}.{v.minor}.{v.micro}.")'

check-venv: $(PYTHON_BIN)
	@$(PYTHON_BIN) -c 'import sys; v=sys.version_info; ok=(3, 14) <= v[:2] < (3, 15); sys.exit(0 if ok else f"Existing virtualenv uses Python {v.major}.{v.minor}.{v.micro}. Run `make clean` and recreate it with Python 3.14.")'

$(PYTHON_BIN):
	$(MAKE) check-python
	$(PYTHON) -m venv $(VENV)

$(INSTALL_STAMP): pyproject.toml $(PYTHON_BIN)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	touch $(INSTALL_STAMP)

setup: check-venv $(INSTALL_STAMP)

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
	POLYABRAIN_RUN_DB_TESTS=1 $(PYTHON_BIN) -m pytest backend/tests/test_database_baseline.py backend/tests/test_sessions_service.py

docker-up:
	docker compose up --build --wait --wait-timeout 60

docker-down:
	docker compose down

proof: check-python
	$(PYTHON) proofs/pre_platform/verify_pre_platform_proof.py --all

chapter11-proof: setup
	$(PYTHON_BIN) scripts/verify_chapter11_examples.py

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache
