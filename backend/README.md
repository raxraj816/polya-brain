# Backend

Python/FastAPI backend for the PolyaBrain Core Platform.

Chapters 3, 4, 5, and 6 implement the local development shell, the first durable
database baseline, the core Pydantic contract layer, and the LangGraph state
object:

- FastAPI app factory at `backend/app/main.py`.
- Environment-backed settings at `backend/app/config.py`.
- `/health` endpoint with typed response model.
- SQLAlchemy 2.0 declarative base and Alembic migrations.
- Postgres/pgvector MVP tables for sessions, evidence, trace, artifacts, and
  semantic knowledge chunks.
- Local database seed and guarded smoke utilities.
- Strict Pydantic contracts for structured problems, gaps, evidence,
  hypotheses, plan tasks, verification reports, and reflections.
- LangGraph-compatible `PolyaState`, state initialization helper, event reducer,
  and state-local event/execution output models.
- Pytest, ruff, and mypy configuration through the repository `pyproject.toml`.

Run locally from the repository root:

```bash
make dev
curl http://127.0.0.1:8000/health
```

Run the local database baseline with Docker Compose:

```bash
make docker-up
make migrate
make db-smoke
make db-test
make docker-down
```

`make db-smoke` writes local seed data only when `POLYABRAIN_ENV` is `local` or
`test`, unless `POLYABRAIN_ALLOW_DB_SEED=1` is explicitly set.

Planned platform responsibilities:

- API shell for solve sessions, trace streaming, feedback, and memory inspection.
- LangGraph orchestration for the stateful Polya loop.
- Typed engine modules for representation, constraints, gaps, research, evidence, hypotheses, execution, verification, and reflection.
- Persistence adapters for Postgres, Redis, artifacts, traces, tool calls, and model-call cost records.
