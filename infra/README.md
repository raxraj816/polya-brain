# Infra

Local and deployment infrastructure notes for PolyaBrain.

Chapter 3 adds the local Docker Compose stack at the repository root:

- `postgres`: Postgres with pgvector.
- `redis`: runtime cache and future streaming state support.
- `backend`: FastAPI backend container.

Run from the repository root:

```bash
make docker-up
make migrate
make docker-down
```

Later infrastructure assets should stay boring until the local investigation
loop proves product value.

Keep infrastructure boring until the investigation loop is useful.
