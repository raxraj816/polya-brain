# Chapter Backlog

This is the local implementation tracker until a project board exists. The source of truth remains `../../PolyaBrain_Product_Implementation_Master_Plan.md`.

## Chapter 1: Product Lock And Repository Foundation

Status: complete on `feature/chapter-1-foundation`.

Done:

- Product source of truth exists in the master plan.
- Chapter 1 start document exists.
- Cognitive doctrine, architecture decisions, data contracts, benchmark categories, and acceleration playbook exist.
- Pre-platform proof harness runs through the local CLI.
- Stored pre-platform proof runs verify with deterministic checks.
- Repository foundation files exist for README, environment template, editor config, pre-commit config, and planned top-level directories.
- Local chapter backlog exists until a GitHub project board is needed.
- Final verification pass completed with `python3 proofs/pre_platform/verify_pre_platform_proof.py --all`.
- No real secrets are stored in the environment template.

Exit criteria:

- Repo can be cloned by a new developer.
- MVP scope is visible in the README.
- No secret values are committed.
- Local proof command is documented and verified.

## Chapter 2: Architecture Decisions And Risk Register

Status: not started.

Planned:

- Add `docs/architecture_decisions.md`.
- Add `docs/risk_register.md`.
- Add a lightweight ADR template.
- Record the reasons for Python monolith first, Postgres plus pgvector first, LangGraph orchestration, core-first architecture, and mixed benchmark suite.
- Document mitigations for hallucination, bad data, LLM cost, PII leakage, tool misuse, infinite loops, and poor UX trust.

## Chapter 3: Local Development Environment

Status: not started.

Planned:

- Create Python backend package and dependency files.
- Add FastAPI, Pydantic, SQLAlchemy, Alembic, pytest, ruff, mypy, LangGraph, Redis client, and Postgres driver.
- Add Docker Compose for Postgres, Redis, and backend.
- Add Makefile commands for dev, test, lint, and migrate.
- Add `/health`.
- Add CI lint and test workflow.
