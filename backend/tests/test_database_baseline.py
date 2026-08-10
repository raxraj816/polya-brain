"""Database baseline integration tests."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.cognition.persistence import SQLAlchemyCognitiveStateRepository
from app.config import get_settings
from app.db.models import EvidenceItem as EvidenceItemRecord
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
def test_cognitive_repository_rehydrates_canonical_evidence() -> None:
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        problem_session = ProblemSession(
            raw_input=f"Evidence rehydration {uuid4()}",
            mode="investigate",
            status="awaiting_user_input",
        )
        session.add(problem_session)
        session.flush()
        session.add(
            EvidenceItemRecord(
                session_id=problem_session.id,
                source_type="evaluated_web_source",
                source_uri="https://example.com/prior",
                claim="A prior fact remains relevant.",
                raw_excerpt="Prior source excerpt.",
                reliability_score=0.8,
                relevance_score=0.9,
                supports_hypothesis_ids=[],
                contradicts_hypothesis_ids=[],
            )
        )
        session.commit()
        session_id = problem_session.id

    with session_factory() as session:
        evidence = SQLAlchemyCognitiveStateRepository(session).load_evidence(session_id)

    assert len(evidence) == 1
    assert evidence[0].claim == "A prior fact remains relevant."
    assert evidence[0].source_uri == "https://example.com/prior"


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
        event_page = repository.list_events(session_id)

        assert event_page is not None
        events = event_page.events
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
        assert repository.count_events(session_id, event_type="started") == 2
        assert repository.count_events(session_id, event_type="completed") == 1


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_trace_repository_filters_and_paginates_in_sequence_order() -> None:
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        problem_session = ProblemSession(
            raw_input=f"Trace paging test {uuid4()}",
            domain="software_debugging",
            mode="investigate",
            status="running",
        )
        session.add(problem_session)
        session.flush()
        repository = SQLAlchemyTraceRepository(session)
        repository.persist_events(
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
                    metadata={"status": "ok", "recommended_route": "continue"},
                ),
                StateEvent(
                    engine_name="execution",
                    event_type="started",
                    reasoning_mode=ReasoningMode.EXECUTE,
                    summary="Started execution.",
                ),
            ],
        )
        session.commit()
        session_id = problem_session.id

    with session_factory() as session:
        repository = SQLAlchemyTraceRepository(session)
        first_page = repository.list_events(session_id, limit=2)
        completed_page = repository.list_events(
            session_id,
            after_sequence=0,
            event_type="completed",
            limit=10,
        )

        assert first_page is not None
        assert [event.sequence_number for event in first_page.events] == [0, 1]
        assert first_page.has_more is True
        assert first_page.next_after_sequence == 1
        assert completed_page is not None
        assert [event.event_type for event in completed_page.events] == ["completed"]
        assert completed_page.has_more is False


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_trace_repository_serializes_concurrent_appends_per_session() -> None:
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        problem_session = ProblemSession(
            raw_input=f"Concurrent trace append test {uuid4()}",
            domain="software_debugging",
            mode="investigate",
            status="running",
        )
        session.add(problem_session)
        session.commit()
        session_id = problem_session.id

    barrier = Barrier(2)

    def append_one(worker_id: int) -> list[int]:
        with session_factory() as session:
            repository = SQLAlchemyTraceRepository(session)
            barrier.wait(timeout=10)
            records = repository.persist_events(
                session_id=session_id,
                events=[
                    StateEvent(
                        engine_name=f"worker_{worker_id}",
                        event_type="started",
                        reasoning_mode=ReasoningMode.EXPLORE,
                        summary=f"Worker {worker_id} started.",
                    )
                ],
            )
            session.commit()
            return [record.sequence_number for record in records]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append_one, [1, 2]))

    with session_factory() as session:
        sequence_numbers = list(
            session.scalars(
                select(ReasoningEvent.sequence_number)
                .where(ReasoningEvent.session_id == session_id)
                .order_by(ReasoningEvent.sequence_number)
            )
        )

    assert sorted(sequence for result in results for sequence in result) == [0, 1]
    assert sequence_numbers == [0, 1]


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
