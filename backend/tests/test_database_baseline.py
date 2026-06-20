"""Database baseline integration tests."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db.models import ProblemSession, ReasoningEvent
from app.db.session import create_database_engine, create_session_factory
from app.db.smoke import assert_database_baseline, can_seed_database
from app.graph.state import StateEvent
from app.models.contracts import ReasoningMode
from app.tracing.persistence import SQLAlchemyTraceRepository

RUN_DB_TESTS = os.environ.get("POLYABRAIN_RUN_DB_TESTS") == "1"
DB_TEST_SKIP_REASON = "set POLYABRAIN_RUN_DB_TESTS=1 with a migrated Postgres/pgvector database"


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_chapter_4_database_baseline_supports_seed_graph_and_vector_storage() -> None:
    engine = create_database_engine(get_settings().database_url)

    assert_database_baseline(engine, allow_seed=True)


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_trace_repository_appends_route_decisions_and_reads_in_sequence_order() -> None:
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    raw_input = f"Repository trace append test {uuid4()}"

    with session_factory() as session:
        problem_session = ProblemSession(
            raw_input=raw_input,
            domain="software_debugging",
            mode="investigate",
            status="running",
        )
        session.add(problem_session)
        session.flush()

        repository = SQLAlchemyTraceRepository(session)
        first_records = repository.persist_events(
            session_id=problem_session.id,
            events=[
                StateEvent(
                    engine_name="problem_representation",
                    event_type="started",
                    reasoning_mode=ReasoningMode.EXPLORE,
                    summary="Started representation.",
                ),
                StateEvent(
                    engine_name="problem_representation",
                    event_type="completed",
                    reasoning_mode=ReasoningMode.EXPLORE,
                    summary="Completed representation.",
                    metadata={
                        "status": "ok",
                        "recommended_route": "continue",
                        "api_key": "sk-proj-secret1234567890",
                    },
                ),
            ],
        )
        second_records = repository.persist_events(
            session_id=problem_session.id,
            events=[
                StateEvent(
                    engine_name="constraint_discovery",
                    event_type="started",
                    reasoning_mode=ReasoningMode.EXPLORE,
                    summary="Started constraints.",
                )
            ],
        )
        session.commit()
        session_id = problem_session.id

    with session_factory() as session:
        repository = SQLAlchemyTraceRepository(session)
        events = repository.list_events(session_id)

        assert events is not None
        assert [record.sequence_number for record in events] == [0, 1, 2, 3]
        assert [record.event_type for record in events] == [
            "started",
            "completed",
            "route_decision",
            "started",
        ]
        assert [record.sequence_number for record in first_records] == [0, 1, 2]
        assert [record.sequence_number for record in second_records] == [3]
        assert events[1].event_metadata["api_key"] == "[REDACTED]"
        assert events[2].engine_name == "graph_router"
        assert events[2].event_metadata["source_engine"] == "problem_representation"


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_trace_repository_rejects_missing_session_writes() -> None:
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        repository = SQLAlchemyTraceRepository(session)
        missing_session_id = uuid4()

        with pytest.raises(ValueError, match="problem session does not exist"):
            repository.persist_events(
                session_id=missing_session_id,
                events=[
                    StateEvent(
                        engine_name="problem_representation",
                        event_type="started",
                        reasoning_mode=ReasoningMode.EXPLORE,
                        summary="Started representation.",
                    )
                ],
            )

        assert (
            session.scalar(
                select(ReasoningEvent.id).where(ReasoningEvent.session_id == missing_session_id)
            )
            is None
        )


def test_database_smoke_seed_guard_blocks_non_local_environments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("POLYABRAIN_ALLOW_DB_SEED", raising=False)

    assert can_seed_database("local") is True
    assert can_seed_database("test") is True
    assert can_seed_database("production") is False


def test_database_smoke_seed_guard_allows_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POLYABRAIN_ALLOW_DB_SEED", "1")

    assert can_seed_database("production") is True
