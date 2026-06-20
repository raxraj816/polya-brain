"""Database-backed Chapter 10 session service tests."""

from __future__ import annotations

import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.models import ProblemSession, ReasoningEvent, utc_now
from app.db.session import create_database_engine, create_session_factory
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import ProductMode, ReasoningMode, VerificationReport
from app.sessions import (
    PolyaSessionService,
    SessionConflictError,
    SessionNotFoundError,
    SessionRunFailedError,
)
from app.sessions.service import (
    SESSION_STATUS_CREATED,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_RUNNING,
    VERIFICATION_STATUS_RUN_EXPIRED,
)

RUN_DB_TESTS = os.environ.get("POLYABRAIN_RUN_DB_TESTS") == "1"
DB_TEST_SKIP_REASON = "set POLYABRAIN_RUN_DB_TESTS=1 with a migrated Postgres/pgvector database"


@pytest.fixture
def session_factory() -> sessionmaker:
    engine = create_database_engine(get_settings().database_url)
    return create_session_factory(engine)


def successful_runner(raw_input: str, *, session_id: str) -> PolyaState:
    state = create_initial_state(raw_input, session_id=session_id)
    state["verification"] = VerificationReport(
        passed=True,
        checks_run=["service test verification"],
        confidence_delta=0.0,
        recommended_route="finalize",
    )
    state["final_answer"] = "Service test completed."
    state["events"] = [
        StateEvent(
            engine_name="problem_representation",
            event_type="started",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Started service test run.",
        ),
        StateEvent(
            engine_name="problem_representation",
            event_type="completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Completed service test run.",
            metadata={
                "status": "ok",
                "recommended_route": "continue",
            },
        ),
    ]
    return state


def failing_runner(raw_input: str, *, session_id: str) -> PolyaState:
    del raw_input, session_id
    raise RuntimeError("forced service test failure")


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_create_persists_created_session(
    session_factory: sessionmaker,
) -> None:
    raw_input = f"Create service session {uuid4()}"

    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=successful_runner)
        problem_session = service.create_session(
            raw_input=raw_input,
            mode=ProductMode.INVESTIGATE,
            domain="software_debugging",
        )
        session_id = problem_session.id

    with session_factory() as db_session:
        persisted = db_session.get(ProblemSession, session_id)

        assert persisted is not None
        assert persisted.raw_input == raw_input
        assert persisted.status == SESSION_STATUS_CREATED
        assert persisted.run_started_at is None
        assert persisted.mode == ProductMode.INVESTIGATE.value


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_run_persists_completion_and_ordered_trace(
    session_factory: sessionmaker,
) -> None:
    raw_input = f"Run service session {uuid4()}"

    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=successful_runner)
        problem_session = service.create_session(
            raw_input=raw_input,
            mode=ProductMode.INVESTIGATE,
            domain=None,
        )
        run_result = service.run_session(problem_session.id)
        session_id = problem_session.id

        assert run_result.session.status == "completed"
        assert run_result.session.final_answer == "Service test completed."
        assert run_result.session.verification_status == "stub_passed"
        assert run_result.event_count == 3

    with session_factory() as db_session:
        persisted = db_session.get(ProblemSession, session_id)
        events = list(
            db_session.scalars(
                select(ReasoningEvent)
                .where(ReasoningEvent.session_id == session_id)
                .order_by(ReasoningEvent.sequence_number)
            )
        )

        assert persisted is not None
        assert persisted.status == "completed"
        assert persisted.run_started_at is not None
        assert [event.sequence_number for event in events] == [0, 1, 2]
        assert [event.event_type for event in events] == [
            "started",
            "completed",
            "route_decision",
        ]


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_rejects_missing_and_duplicate_runs(
    session_factory: sessionmaker,
) -> None:
    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=successful_runner)

        with pytest.raises(SessionNotFoundError):
            service.run_session(uuid4())

        problem_session = service.create_session(
            raw_input=f"Duplicate service session {uuid4()}",
            mode=ProductMode.INVESTIGATE,
            domain=None,
        )
        service.run_session(problem_session.id)

        with pytest.raises(SessionConflictError, match="completed"):
            service.run_session(problem_session.id)


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_marks_failed_run_and_does_not_persist_trace(
    session_factory: sessionmaker,
) -> None:
    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=failing_runner)
        problem_session = service.create_session(
            raw_input=f"Failing service session {uuid4()}",
            mode=ProductMode.INVESTIGATE,
            domain=None,
        )
        session_id = problem_session.id

        with pytest.raises(SessionRunFailedError, match="forced service test failure"):
            service.run_session(session_id)

    with session_factory() as db_session:
        persisted = db_session.get(ProblemSession, session_id)
        event_count = db_session.scalar(
            select(func.count(ReasoningEvent.id)).where(ReasoningEvent.session_id == session_id)
        )

        assert persisted is not None
        assert persisted.status == "failed"
        assert persisted.verification_status == "run_failed"
        assert persisted.final_answer is not None
        assert "stopped safely" in persisted.final_answer
        assert event_count == 0


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_commits_running_before_graph_execution(
    session_factory: sessionmaker,
) -> None:
    competing_result: dict[str, str] = {}

    def runner_with_competing_run(raw_input: str, *, session_id: str) -> PolyaState:
        with session_factory() as competing_db_session:
            competing_service = PolyaSessionService(
                competing_db_session,
                runner=successful_runner,
            )
            with pytest.raises(SessionConflictError, match=SESSION_STATUS_RUNNING):
                competing_service.run_session(UUID(session_id))
            competing_result["status"] = SESSION_STATUS_RUNNING
        return successful_runner(raw_input, session_id=session_id)

    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=runner_with_competing_run)
        problem_session = service.create_session(
            raw_input=f"Competing service session {uuid4()}",
            mode=ProductMode.INVESTIGATE,
            domain=None,
        )

        run_result = service.run_session(problem_session.id)

        assert run_result.session.status == "completed"
        assert competing_result == {"status": SESSION_STATUS_RUNNING}


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_expires_stale_running_session_without_rerun(
    session_factory: sessionmaker,
) -> None:
    runner_calls = 0

    def runner_that_must_not_run(raw_input: str, *, session_id: str) -> PolyaState:
        nonlocal runner_calls
        del raw_input, session_id
        runner_calls += 1
        raise AssertionError("expired running sessions must not be rerun")

    with session_factory() as db_session:
        stale_session = ProblemSession(
            raw_input=f"Stale running session {uuid4()}",
            mode=ProductMode.INVESTIGATE.value,
            domain=None,
            status=SESSION_STATUS_RUNNING,
            run_started_at=utc_now() - timedelta(minutes=30),
        )
        db_session.add(stale_session)
        db_session.commit()
        session_id = stale_session.id

    with session_factory() as db_session:
        service = PolyaSessionService(
            db_session,
            runner=runner_that_must_not_run,
            stale_run_timeout_seconds=60,
        )
        with pytest.raises(SessionConflictError, match=SESSION_STATUS_FAILED):
            service.run_session(session_id)

    with session_factory() as db_session:
        persisted = db_session.get(ProblemSession, session_id)

        assert persisted is not None
        assert persisted.status == SESSION_STATUS_FAILED
        assert persisted.verification_status == VERIFICATION_STATUS_RUN_EXPIRED
        assert persisted.final_answer is not None
        assert "expired this run" in persisted.final_answer
        assert persisted.completed_at is not None
        assert runner_calls == 0


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_expires_running_session_without_start_timestamp(
    session_factory: sessionmaker,
) -> None:
    runner_calls = 0

    def runner_that_must_not_run(raw_input: str, *, session_id: str) -> PolyaState:
        nonlocal runner_calls
        del raw_input, session_id
        runner_calls += 1
        raise AssertionError("running sessions without start timestamps must not be rerun")

    with session_factory() as db_session:
        stale_session = ProblemSession(
            raw_input=f"Legacy running session {uuid4()}",
            mode=ProductMode.INVESTIGATE.value,
            domain=None,
            status=SESSION_STATUS_RUNNING,
            run_started_at=None,
        )
        db_session.add(stale_session)
        db_session.commit()
        session_id = stale_session.id

    with session_factory() as db_session:
        service = PolyaSessionService(
            db_session,
            runner=runner_that_must_not_run,
            stale_run_timeout_seconds=60,
        )
        with pytest.raises(SessionConflictError, match=SESSION_STATUS_FAILED):
            service.run_session(session_id)

    with session_factory() as db_session:
        persisted = db_session.get(ProblemSession, session_id)

        assert persisted is not None
        assert persisted.status == SESSION_STATUS_FAILED
        assert persisted.verification_status == VERIFICATION_STATUS_RUN_EXPIRED
        assert persisted.completed_at is not None
        assert runner_calls == 0
