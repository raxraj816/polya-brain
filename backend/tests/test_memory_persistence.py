"""Postgres/pgvector integration tests for long-term memory."""

from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.config import get_settings
from app.db.models import (
    EpisodicMemory,
    KnowledgeChunk,
    ProblemSession,
    ProceduralStrategy,
    utc_now,
)
from app.db.session import create_database_engine, create_session_factory
from app.graph.state import StateEvent, create_initial_state
from app.memory import SQLAlchemyMemoryRepository
from app.models.contracts import (
    KnowledgeGap,
    ReasoningMode,
    Reflection,
    StructuredProblem,
    VerificationReport,
)

RUN_DB_TESTS = os.environ.get("POLYABRAIN_RUN_DB_TESTS") == "1"
DB_TEST_SKIP_REASON = "set POLYABRAIN_RUN_DB_TESTS=1 with a migrated Postgres/pgvector database"
EPISODE_FIXTURES = Path(__file__).with_name("fixtures") / "verified_episodes.json"


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_semantic_memory_similarity_filters_stale_and_low_reliability_chunks() -> None:
    session_factory = create_session_factory(create_database_engine(get_settings().database_url))
    marker = str(uuid4())
    domain = f"memory-test-{marker}"
    with session_factory() as session:
        repository = SQLAlchemyMemoryRepository(session)
        current = repository.ingest_semantic(
            "Database query latency increased after an index change.",
            source_type="test_source",
            source_uri=f"test://{marker}/current",
            reliability_score=0.95,
            domain=domain,
            valid_until=utc_now() + timedelta(days=1),
            tags=["database", "latency"],
        )
        repository.ingest_semantic(
            "Database query latency increased after an index change.",
            source_type="test_source",
            source_uri=f"test://{marker}/stale",
            reliability_score=0.95,
            domain=domain,
            valid_until=utc_now() - timedelta(days=1),
        )
        repository.ingest_semantic(
            "Database query latency increased after an index change.",
            source_type="test_source",
            source_uri=f"test://{marker}/weak",
            reliability_score=0.2,
            domain=domain,
        )
        session.commit()

        results = repository.search_semantic(
            "database query latency index",
            domain=domain,
            minimum_reliability=0.5,
        )

        assert [item.id for item in results] == [current.id]
        assert results[0].source_uri == f"test://{marker}/current"
        assert results[0].tags == ["database", "latency"]
        assert (
            repository.search_semantic(
                "botanical watercolor pigments",
                domain=domain,
                minimum_reliability=0.5,
            )
            == []
        )
        session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.domain == domain))
        session.commit()


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_only_verified_reflected_runs_create_episode_and_procedure_memory() -> None:
    session_factory = create_session_factory(create_database_engine(get_settings().database_url))
    marker = str(uuid4())
    with session_factory() as session:
        problem_session = ProblemSession(
            raw_input=f"Calculate a verified outcome {marker}",
            mode="solve",
            status="completed",
        )
        unverified_session = ProblemSession(
            raw_input=f"Unverified outcome {marker}",
            mode="solve",
            status="completed",
        )
        session.add_all([problem_session, unverified_session])
        session.flush()
        repository = SQLAlchemyMemoryRepository(session)

        unverified = create_initial_state(
            unverified_session.raw_input, session_id=str(unverified_session.id)
        )
        assert repository.learn_verified_outcome(unverified_session.id, unverified) is False

        state = create_initial_state(problem_session.raw_input, session_id=str(problem_session.id))
        state["structured_problem"] = StructuredProblem(
            core_question="What is the exact calculation?",
            problem_type=f"calculation-{marker}",
            domain="mathematics",
            constraints=["Use exact arithmetic."],
        )
        state["gaps"] = [
            KnowledgeGap(
                description="Compute the exact expression.",
                gap_type="arithmetic",
                why_needed="The answer depends on the exact result.",
                filled=True,
                evidence_ids=["calculation:evidence:1"],
            )
        ]
        state["verification"] = VerificationReport(
            passed=True,
            checks_run=["Recomputed the expression independently."],
        )
        state["reflection"] = Reflection(
            outcome_summary="Exact arithmetic produced and verified the result.",
            what_worked=["Use the deterministic calculator."],
            reusable_lessons=["Prefer exact arithmetic for exact expressions."],
        )
        state["final_answer"] = "The exact result is 102."
        state["events"] = [
            StateEvent(
                engine_name="cognitive_controller",
                event_type="cognitive_action_decision",
                reasoning_mode=ReasoningMode.EXPLORE,
                summary="Selected memory retrieval.",
                metadata={
                    "selected": {
                        "id": "action-memory",
                        "target": "Compute the exact expression.",
                        "action_type": "retrieve_memory",
                        "capability": "memory",
                    }
                },
            ),
            StateEvent(
                engine_name="memory",
                event_type="capability_observation",
                reasoning_mode=ReasoningMode.EXECUTE,
                summary="No relevant memory was found.",
                metadata={
                    "action_id": "action-memory",
                    "status": "inconclusive",
                },
            ),
            StateEvent(
                engine_name="cognitive_controller",
                event_type="cognitive_action_decision",
                reasoning_mode=ReasoningMode.EXPLORE,
                summary="Selected calculation.",
                metadata={
                    "selected": {
                        "id": "action-calculate",
                        "target": "Compute the exact expression.",
                        "action_type": "calculate",
                        "capability": "calculator",
                    }
                },
            ),
            StateEvent(
                engine_name="calculator",
                event_type="capability_observation",
                reasoning_mode=ReasoningMode.EXECUTE,
                summary="Calculation succeeded.",
                metadata={
                    "action_id": "action-calculate",
                    "status": "succeeded",
                },
            ),
        ]

        assert repository.learn_verified_outcome(problem_session.id, state) is True
        assert repository.learn_verified_outcome(problem_session.id, state) is True
        session.commit()

        episode = session.scalar(
            select(EpisodicMemory).where(EpisodicMemory.source_session_id == problem_session.id)
        )
        assert episode is not None
        assert episode.final_answer == "The exact result is 102."
        assert (
            session.scalar(
                select(EpisodicMemory).where(
                    EpisodicMemory.source_session_id == unverified_session.id
                )
            )
            is None
        )

        preference = repository.preference(f"calculation-{marker}", "arithmetic")
        assert preference is not None
        assert preference.action_type.value == "calculate"
        assert preference.capability == "calculator"
        assert preference.verified_successes == 1

        procedure = session.scalar(
            select(ProceduralStrategy).where(
                ProceduralStrategy.problem_type == f"calculation-{marker}"
            )
        )
        assert procedure is not None
        assert procedure.source_session_ids == [str(problem_session.id)]
        failed_procedure = session.scalar(
            select(ProceduralStrategy).where(
                ProceduralStrategy.problem_type == f"calculation-{marker}",
                ProceduralStrategy.action_type == "retrieve_memory",
            )
        )
        assert failed_procedure is not None
        assert failed_procedure.verified_successes == 0
        assert failed_procedure.verified_failures == 1
        assert failed_procedure.success_rate == 0.0

        session.execute(
            delete(ProceduralStrategy).where(
                ProceduralStrategy.problem_type == f"calculation-{marker}"
            )
        )
        session.execute(
            delete(ProblemSession).where(
                ProblemSession.id.in_([problem_session.id, unverified_session.id])
            )
        )
        session.commit()


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_similar_episode_retrieval_spans_five_problem_categories() -> None:
    fixtures = json.loads(EPISODE_FIXTURES.read_text(encoding="utf-8"))
    session_factory = create_session_factory(create_database_engine(get_settings().database_url))
    session_ids = []
    with session_factory() as session:
        repository = SQLAlchemyMemoryRepository(session)
        for item in fixtures:
            problem_session = ProblemSession(
                raw_input=item["core_question"],
                mode="solve",
                status="completed",
            )
            session.add(problem_session)
            session.flush()
            session_ids.append(problem_session.id)
            state = create_initial_state(item["core_question"], session_id=str(problem_session.id))
            state["structured_problem"] = StructuredProblem(
                core_question=item["core_question"],
                problem_type=item["problem_type"],
                domain=item["domain"],
            )
            state["verification"] = VerificationReport(
                passed=True,
                checks_run=["Fixture outcome independently checked."],
            )
            state["reflection"] = Reflection(outcome_summary=item["outcome_summary"])
            state["final_answer"] = item["final_answer"]
            assert repository.learn_verified_outcome(problem_session.id, state)
        session.commit()

        for item, session_id in zip(fixtures, session_ids, strict=True):
            results = repository.search_episodes(
                item["query"],
                problem_type=item["problem_type"],
                domain=item["domain"],
                minimum_similarity=0.08,
            )
            assert results
            assert results[0].source_session_id == session_id

        session.execute(delete(ProblemSession).where(ProblemSession.id.in_(session_ids)))
        session.commit()
