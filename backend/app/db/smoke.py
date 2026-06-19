"""Smoke checks for the Chapter 4 database baseline."""

from __future__ import annotations

import os
from collections.abc import Iterable

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, func, inspect, select, text

from app.config import get_settings
from app.db.models import (
    Artifact,
    EvidenceItem,
    Hypothesis,
    KnowledgeChunk,
    KnowledgeGap,
    PlanTask,
    ProblemSession,
    ReasoningEvent,
)
from app.db.seed import SEED_RAW_INPUT, seed_database
from app.db.session import create_database_engine, create_session_factory

SAFE_SEED_ENVIRONMENTS = {"local", "test"}
ALLOW_SEED_ENV_VAR = "POLYABRAIN_ALLOW_DB_SEED"

REQUIRED_TABLES = {
    "problem_sessions",
    "structured_problems",
    "knowledge_gaps",
    "evidence_items",
    "hypotheses",
    "plan_tasks",
    "reasoning_events",
    "verification_reports",
    "artifacts",
    "knowledge_chunks",
}


def _missing_items(required: Iterable[str], actual: Iterable[str]) -> set[str]:
    return set(required).difference(actual)


def can_seed_database(environment: str) -> bool:
    """Return whether smoke checks may write seed data to the configured database."""
    return environment in SAFE_SEED_ENVIRONMENTS or os.environ.get(ALLOW_SEED_ENV_VAR) == "1"


def assert_database_baseline(engine: Engine, *, allow_seed: bool) -> None:
    """Raise AssertionError if the Chapter 4 baseline is not usable."""
    with engine.connect() as connection:
        vector_installed = connection.scalar(
            text("select exists(select 1 from pg_extension where extname = 'vector')")
        )
        assert vector_installed is True, "pgvector extension is not installed"

        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)
        expected_heads = set(script.get_heads())
        migration_context = MigrationContext.configure(connection)
        current_heads = set(migration_context.get_current_heads())
        assert current_heads == expected_heads, (
            f"database migration heads {current_heads} do not match expected {expected_heads}"
        )

        table_names = inspect(connection).get_table_names()
        missing_tables = _missing_items(REQUIRED_TABLES, table_names)
        assert not missing_tables, f"missing Chapter 4 tables: {sorted(missing_tables)}"

    assert allow_seed, (
        "database smoke checks insert local seed data; refusing because this environment is not "
        f"one of {sorted(SAFE_SEED_ENVIRONMENTS)} and {ALLOW_SEED_ENV_VAR}=1 is not set"
    )

    session_factory = create_session_factory(engine)
    with session_factory() as session:
        session_id = seed_database(session)
        problem_session = session.scalar(
            select(ProblemSession).where(ProblemSession.raw_input == SEED_RAW_INPUT)
        )
        assert problem_session is not None, "seed problem session was not inserted"
        assert problem_session.id == session_id, "seed session id mismatch"

        evidence_count = session.scalar(
            select(func.count())
            .select_from(EvidenceItem)
            .where(EvidenceItem.session_id == session_id)
        )
        hypothesis_count = session.scalar(
            select(func.count()).select_from(Hypothesis).where(Hypothesis.session_id == session_id)
        )
        task_count = session.scalar(
            select(func.count()).select_from(PlanTask).where(PlanTask.session_id == session_id)
        )
        trace_count = session.scalar(
            select(func.count())
            .select_from(ReasoningEvent)
            .where(ReasoningEvent.session_id == session_id)
        )
        artifact_count = session.scalar(
            select(func.count()).select_from(Artifact).where(Artifact.session_id == session_id)
        )
        chunk = session.scalar(
            select(KnowledgeChunk).where(KnowledgeChunk.session_id == session_id).limit(1)
        )
        evidence_item = session.scalar(
            select(EvidenceItem).where(EvidenceItem.session_id == session_id).limit(1)
        )
        hypothesis = session.scalar(
            select(Hypothesis).where(Hypothesis.session_id == session_id).limit(1)
        )
        knowledge_gap = session.scalar(
            select(KnowledgeGap).where(KnowledgeGap.session_id == session_id).limit(1)
        )

        assert evidence_count and evidence_count > 0, "seed evidence item was not inserted"
        assert hypothesis_count and hypothesis_count > 0, "seed hypothesis was not inserted"
        assert task_count and task_count > 0, "seed plan task was not inserted"
        assert trace_count and trace_count > 0, "seed reasoning event was not inserted"
        assert artifact_count and artifact_count > 0, "seed artifact was not inserted"
        assert evidence_item is not None, "seed evidence item could not be retrieved"
        assert hypothesis is not None, "seed hypothesis could not be retrieved"
        assert knowledge_gap is not None, "seed knowledge gap could not be retrieved"
        assert str(evidence_item.id) in hypothesis.evidence_for, (
            "seed hypothesis is not linked to supporting evidence"
        )
        assert str(hypothesis.id) in evidence_item.supports_hypothesis_ids, (
            "seed evidence is not linked to supported hypothesis"
        )
        assert str(evidence_item.id) in knowledge_gap.evidence_ids, (
            "seed knowledge gap is not linked to filling evidence"
        )
        assert chunk is not None, "seed knowledge chunk was not inserted"
        assert chunk.content_hash is not None, "seed knowledge chunk content hash was not inserted"
        assert chunk.embedding_provider == "local_seed", "seed embedding provider was not inserted"
        assert chunk.embedding_model == "zero-vector-1536", "seed embedding model was not inserted"
        assert chunk.embedding_dimensions == 1536, (
            "seed embedding dimensions metadata has the wrong value"
        )
        assert chunk.embedding is not None, "seed knowledge chunk embedding was not inserted"
        assert len(chunk.embedding) == 1536, (
            "seed knowledge chunk embedding has the wrong dimension"
        )


def main() -> None:
    """CLI entrypoint for local database smoke checks."""
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    assert_database_baseline(engine, allow_seed=can_seed_database(settings.environment))
    print("Chapter 4 database baseline smoke checks passed.")


if __name__ == "__main__":
    main()
