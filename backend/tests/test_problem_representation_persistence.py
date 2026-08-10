"""Persistence guardrails for accepted Chapter 13 engine output."""

from __future__ import annotations

import os
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ProblemSession, ReasoningEvent
from app.db.models import StructuredProblem as StructuredProblemRecord
from app.db.session import create_database_engine, create_session_factory
from app.engines import (
    EngineResult,
    EngineRoute,
    EngineRunOutput,
    EngineStatus,
    EngineVersion,
    ProblemRepresentationEngine,
    run_engine,
)
from app.graph.state import create_initial_state
from app.llm import FakeLLMClient
from app.problem_understanding.persistence import (
    SQLAlchemyProblemRepresentationRunRepository,
    SQLAlchemyStructuredProblemRepository,
)

RUN_DB_TESTS = os.environ.get("POLYABRAIN_RUN_DB_TESTS") == "1"
DB_TEST_SKIP_REASON = "set POLYABRAIN_RUN_DB_TESTS=1 with a migrated Postgres/pgvector database"


def non_success_output() -> EngineRunOutput:
    return EngineRunOutput(
        state_delta={},
        result=EngineResult(
            status=EngineStatus.NEEDS_INPUT,
            confidence=0.4,
            missing_inputs=["Which service is affected?"],
            recommended_route=EngineRoute.CLARIFY,
            versions=EngineVersion(engine="problem_representation@1.0.0"),
            summary="Clarification is required.",
        ),
    )


def test_repository_rejects_non_success_before_touching_database() -> None:
    session = MagicMock(spec=Session)
    repository = SQLAlchemyStructuredProblemRepository(session)

    with pytest.raises(ValueError, match="only an ok representation result"):
        repository.persist_successful_output(session_id=uuid4(), output=non_success_output())

    session.get.assert_not_called()
    session.flush.assert_not_called()


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_successful_representation_is_canonicalized_with_trace() -> None:
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    raw_input = "What is 17 * 6?"

    with session_factory() as session:
        problem_session = ProblemSession(
            raw_input=raw_input,
            domain="mathematics",
            mode="explore",
            status="running",
        )
        session.add(problem_session)
        session.flush()
        output = run_engine(
            ProblemRepresentationEngine(
                client=FakeLLMClient([]),
                model="unused-fake-model",
            ),
            create_initial_state(raw_input, session_id=str(problem_session.id)),
        )
        persisted = SQLAlchemyProblemRepresentationRunRepository(session).persist_run_output(
            session_id=problem_session.id,
            output=output,
        )
        session.commit()
        session_id = problem_session.id

    with session_factory() as session:
        record = session.scalar(
            select(StructuredProblemRecord).where(StructuredProblemRecord.session_id == session_id)
        )
        event_count = session.scalar(
            select(func.count(ReasoningEvent.id)).where(ReasoningEvent.session_id == session_id)
        )

    assert persisted.structured_problem is not None
    assert persisted.event_count >= 5
    assert record is not None
    assert record.problem_type == "simple_arithmetic"
    assert record.knowns == ["Expression: 17 * 6."]
    assert event_count == persisted.event_count


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_clarification_trace_is_persisted_without_canonical_problem() -> None:
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    raw_input = "Fix it."

    with session_factory() as session:
        problem_session = ProblemSession(
            raw_input=raw_input,
            mode="explore",
            status="running",
        )
        session.add(problem_session)
        session.flush()
        output = run_engine(
            ProblemRepresentationEngine(
                client=FakeLLMClient([]),
                model="unused-fake-model",
            ),
            create_initial_state(raw_input, session_id=str(problem_session.id)),
        )
        persisted = SQLAlchemyProblemRepresentationRunRepository(session).persist_run_output(
            session_id=problem_session.id,
            output=output,
        )
        session.commit()
        session_id = problem_session.id

    with session_factory() as session:
        record = session.scalar(
            select(StructuredProblemRecord).where(StructuredProblemRecord.session_id == session_id)
        )

    assert output.result.status is EngineStatus.NEEDS_INPUT
    assert persisted.structured_problem is None
    assert persisted.event_count >= 5
    assert record is None
