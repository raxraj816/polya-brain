# Backend

Python/FastAPI backend for the PolyaBrain Core Platform.

Chapter 3 implements the local development shell:

- FastAPI app factory at `backend/app/main.py`.
- Environment-backed settings at `backend/app/config.py`.
- `/health` endpoint with typed response model.
- Alembic migration scaffold wired to shared SQLAlchemy metadata.
- Pytest, ruff, and mypy configuration through the repository `pyproject.toml`.

Run locally from the repository root:

```bash
make dev
curl http://127.0.0.1:8000/health
```

Planned platform responsibilities:

- API shell for solve sessions, trace streaming, feedback, and memory inspection.
- LangGraph orchestration for the stateful Polya loop.
- Typed engine modules for representation, constraints, gaps, research, evidence, hypotheses, execution, verification, and reflection.
- Persistence adapters for Postgres, Redis, artifacts, traces, tool calls, and model-call cost records.
