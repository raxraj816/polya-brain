# Chapter 3 Local Development Environment

Status: complete on `feature/chapter-3-local-dev-env`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 3 turns the repository from a pre-platform proof harness into a local
platform development environment. It does not implement the Chapter 4 database
schema or the Chapter 5 core Pydantic contracts.

## Implemented

- Python project metadata and dependency groups in `pyproject.toml`.
- FastAPI backend package under `backend/app`.
- Typed `/health` endpoint.
- Environment-backed settings through Pydantic Settings.
- SQLAlchemy metadata placeholder and Alembic environment.
- Docker Compose stack for Postgres with pgvector, Redis, and backend.
- Backend Dockerfile.
- Makefile targets for setup, dev, lint, test, migrate, Docker up/down, and proof verification.
- GitHub Actions CI for lint, test, and pre-platform proof verification.

## Commands

```bash
make dev
curl http://127.0.0.1:8000/health
```

```bash
make lint
make test
make proof
```

```bash
make docker-up
make migrate
make docker-down
```

## Verification Completed

- `make lint`
- `make test`
- `make proof`
- `make dev` plus live `/health` request
- `docker compose config --quiet`
- `docker compose up -d --build` plus live `/health` request
- `make migrate`
- `make docker-down`

## Deferred To Chapter 4

- Durable database tables.
- pgvector extension migration.
- Seed script.
- Insert/retrieve database smoke test.
- Migration tests.
