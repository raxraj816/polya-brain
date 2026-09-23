"""Database-backed Chapter 10 session service tests."""

from __future__ import annotations

import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.cognition.bootstrap import build_representation_session_runner
from app.config import Settings, get_settings
from app.db.models import (
    ClarificationRequest,
    EvidenceItem,
    Hypothesis,
    KnowledgeGap,
    PlanTask,
    ProblemSession,
    ReasoningEvent,
    utc_now,
)
from app.db.models import StructuredProblem as StructuredProblemRecord
from app.db.models import (
    VerificationReport as VerificationReportRecord,
)
from app.db.session import create_database_engine, create_session_factory
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import ProductMode, ReasoningMode, VerificationReport
from app.sessions import (
    PolyaSessionService,
    SessionConflictError,
    SessionExecutionResult,
    SessionNotFoundError,
    SessionRunFailedError,
)
from app.sessions.service import (
    SESSION_STATUS_AWAITING_USER_INPUT,
    SESSION_STATUS_CREATED,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_RUNNING,
    VERIFICATION_STATUS_CLARIFICATION_EXPIRED,
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


def awaiting_runner(raw_input: str, *, session_id: str) -> SessionExecutionResult:
    state = create_initial_state(raw_input, session_id=session_id)
    state["events"] = [
        StateEvent(
            engine_name="problem_representation",
            event_type="needs_input",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="The success criterion is missing.",
        )
    ]
    return SessionExecutionResult(
        state=state,
        awaiting_user_input=True,
        clarifying_questions=("Which measurable success criterion should be used?",),
    )


def successful_resume_runner(
    raw_input: str,
    answer: str,
    *,
    session_id: str,
) -> PolyaState:
    return successful_runner(
        f"{raw_input}\nClarification: {answer}",
        session_id=session_id,
    )


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
        assert run_result.session.verification_status == "passed"
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
def test_session_service_pauses_persists_question_and_resumes_same_trace(
    session_factory: sessionmaker,
) -> None:
    with session_factory() as db_session:
        service = PolyaSessionService(
            db_session,
            runner=awaiting_runner,
            resume_runner=successful_resume_runner,
        )
        problem_session = service.create_session(
            raw_input=f"Choose the best plan {uuid4()}",
            mode=ProductMode.EXPLORE,
            domain="planning",
        )
        session_id = problem_session.id

        paused = service.run_session(session_id)

        assert paused.session.status == SESSION_STATUS_AWAITING_USER_INPUT
        assert paused.session.completed_at is None
        assert paused.session.final_answer is None
        assert paused.clarifying_questions == (
            "Which measurable success criterion should be used?",
        )

        resumed = service.respond_to_session(
            session_id,
            "Minimize risk while staying within the fixed budget.",
        )

        assert resumed.session.status == "completed"
        assert resumed.session.final_answer == "Service test completed."

    with session_factory() as db_session:
        clarification = db_session.scalar(
            select(ClarificationRequest).where(ClarificationRequest.session_id == session_id)
        )
        events = list(
            db_session.scalars(
                select(ReasoningEvent)
                .where(ReasoningEvent.session_id == session_id)
                .order_by(ReasoningEvent.sequence_number)
            )
        )

        assert clarification is not None
        assert clarification.status == "answered"
        assert clarification.answer == "Minimize risk while staying within the fixed budget."
        assert clarification.answered_at is not None
        assert [event.sequence_number for event in events] == list(range(len(events)))
        assert [event.event_type for event in events] == [
            "needs_input",
            "clarification_requested",
            "clarification_answered",
            "started",
            "completed",
            "route_decision",
        ]


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_rejects_duplicate_clarification_response(
    session_factory: sessionmaker,
) -> None:
    with session_factory() as db_session:
        service = PolyaSessionService(
            db_session,
            runner=awaiting_runner,
            resume_runner=successful_resume_runner,
        )
        problem_session = service.create_session(
            raw_input=f"Clarify once {uuid4()}",
            mode=ProductMode.EXPLORE,
            domain=None,
        )
        service.run_session(problem_session.id)
        service.respond_to_session(problem_session.id, "Use the lowest-risk option.")

        with pytest.raises(SessionConflictError, match="completed"):
            service.respond_to_session(problem_session.id, "A second answer.")


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_session_service_expires_abandoned_clarification(
    session_factory: sessionmaker,
) -> None:
    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=awaiting_runner)
        problem_session = service.create_session(
            raw_input=f"Expire clarification {uuid4()}",
            mode=ProductMode.EXPLORE,
            domain=None,
        )
        service.run_session(problem_session.id)
        clarification = db_session.scalar(
            select(ClarificationRequest).where(
                ClarificationRequest.session_id == problem_session.id
            )
        )
        assert clarification is not None
        clarification.expires_at = utc_now() - timedelta(seconds=1)
        db_session.commit()

        with pytest.raises(SessionConflictError, match="expired"):
            service.respond_to_session(problem_session.id, "Late answer.")

        db_session.refresh(problem_session)
        assert problem_session.status == SESSION_STATUS_FAILED
        assert problem_session.verification_status == VERIFICATION_STATUS_CLARIFICATION_EXPIRED
        assert problem_session.final_answer is not None
        assert "expired" in problem_session.final_answer


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_persisted_cognitive_runner_pauses_and_reunderstands_after_answer(
    session_factory: sessionmaker,
) -> None:
    runner = build_representation_session_runner(
        Settings(
            POLYABRAIN_ENV="test",
            OPENROUTER_API_KEY="",
            OPENROUTER_MODEL="",
        )
    )
    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=runner)
        problem_session = service.create_session(
            raw_input="Fix it.",
            mode=ProductMode.EXPLORE,
            domain=None,
        )

        paused = service.run_session(problem_session.id)
        resumed = service.respond_to_session(
            problem_session.id,
            "Reduce checkout p95 latency below 300 ms without increasing payment errors.",
        )

        assert paused.session.id == resumed.session.id
        assert paused.clarifying_questions
        assert resumed.session.status == "completed"
        assert resumed.session.final_answer is not None
        assert "without a verified conclusion" in resumed.session.final_answer

    with session_factory() as db_session:
        events = list(
            db_session.scalars(
                select(ReasoningEvent)
                .where(ReasoningEvent.session_id == problem_session.id)
                .order_by(ReasoningEvent.sequence_number)
            )
        )
        structured_problem = db_session.scalar(
            select(StructuredProblemRecord).where(
                StructuredProblemRecord.session_id == problem_session.id
            )
        )
        assert any(event.event_type == "clarification_requested" for event in events)
        assert any(event.event_type == "clarification_answered" for event in events)
        assert sum(event.event_type == "framing_selected" for event in events) == 2
        assert structured_problem is not None
        assert structured_problem.problem_type == "clarified_request"


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_persisted_cognitive_runner_stores_verified_arithmetic_artifacts(
    session_factory: sessionmaker,
) -> None:
    runner = build_representation_session_runner(
        Settings(
            POLYABRAIN_ENV="test",
            OPENROUTER_API_KEY="",
            OPENROUTER_MODEL="",
        )
    )
    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=runner)
        problem_session = service.create_session(
            raw_input="17 * 6?",
            mode=ProductMode.EXPLORE,
            domain="mathematics",
        )
        session_id = problem_session.id

        completed = service.run_session(session_id)
        report = service.get_report(session_id)

        assert completed.session.final_answer == "17 * 6 = 102."
        assert completed.session.verification_status == "passed"
        assert report.final_conclusion == "17 * 6 = 102."
        assert report.confidence_level == "high"
        # Fused arithmetic retains the calculator evidence once; its independent
        # recalculation is an execution artifact, not a duplicated source.
        assert len(report.evidence_used) == 1
        assert report.evidence_used[0].source_type == "deterministic_calculator"
        assert report.evidence_against == []
        assert report.checks_performed
        assert report.open_questions == []
        assert report.reflection is not None

    with session_factory() as db_session:
        gap = db_session.scalar(select(KnowledgeGap).where(KnowledgeGap.session_id == session_id))
        evidence = list(
            db_session.scalars(select(EvidenceItem).where(EvidenceItem.session_id == session_id))
        )
        hypothesis = db_session.scalar(
            select(Hypothesis).where(Hypothesis.session_id == session_id)
        )
        plan_task = db_session.scalar(select(PlanTask).where(PlanTask.session_id == session_id))
        verification = db_session.scalar(
            select(VerificationReportRecord).where(
                VerificationReportRecord.session_id == session_id
            )
        )
        reflection_event = db_session.scalar(
            select(ReasoningEvent).where(
                ReasoningEvent.session_id == session_id,
                ReasoningEvent.event_type == "reflection_recorded",
            )
        )

        assert gap is not None and gap.filled
        assert len(evidence) == 1
        assert {item.claim for item in evidence} == {"17 * 6 = 102."}
        assert hypothesis is not None and hypothesis.statement == "17 * 6 = 102."
        assert plan_task is not None
        assert plan_task.params["_polyabrain_task_id"] == "independent-recalculation"
        assert verification is not None and verification.passed
        assert reflection_event is not None
        assert reflection_event.event_metadata["strategy_notes"] == ["calculate_then_recalculate"]
        execution_event = db_session.scalar(
            select(ReasoningEvent).where(
                ReasoningEvent.session_id == session_id,
                ReasoningEvent.event_type == "execution_output_recorded",
            )
        )
        assert execution_event is not None
        assert execution_event.event_metadata["task_id"] == "independent-recalculation"
        assert execution_event.event_metadata["output"] == {"expression": "17 * 6", "result": "102"}


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


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_completed_persisted_report_keeps_answer_bound_residual_questions(
    session_factory: sessionmaker,
) -> None:
    from app.cognition.report_metadata import ConclusionReportMetadata, report_metadata_event

    def conditional_runner(raw_input: str, *, session_id: str) -> PolyaState:
        state = successful_runner(raw_input, session_id=session_id)
        state["events"].append(
            report_metadata_event(
                answer=state["final_answer"],
                metadata=ConclusionReportMetadata(open_questions=["Which target version applies?"]),
                engine_name="conclusion_checker",
            )
        )
        return state

    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=conditional_runner)
        session_id = service.create_session(
            raw_input="Give a conditional proposal.", mode=ProductMode.INVESTIGATE, domain=None
        ).id
        service.run_session(session_id)
    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=conditional_runner)
        report = service.get_report(session_id)
        assert report.verification_status == "passed"
        assert report.open_questions == ["Which target version applies?"]
        problem = db_session.get(ProblemSession, session_id)
        problem.final_answer = "A revised conclusion unrelated to the recorded conditions."
        db_session.commit()
        assert service.get_report(session_id).open_questions == []


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_persisted_report_preserves_invalidated_failure_without_reviving_verdict(
    session_factory: sessionmaker,
) -> None:
    from app.cognition.verification_history import (
        HISTORICAL_CHECK_PREFIX,
        HISTORICAL_NEXT_ACTION,
        verification_invalidated_event,
    )

    def stopped_runner(raw_input: str, *, session_id: str) -> PolyaState:
        state = create_initial_state(raw_input, session_id=session_id)
        state["events"] = [
            verification_invalidated_event(
                VerificationReport(
                    passed=False,
                    checks_run=["Looked for executed tests."],
                    failed_checks=["No test results supplied."],
                ),
                action_id="recovery-plan",
            )
        ]
        return state

    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=stopped_runner)
        session_id = service.create_session(
            raw_input="Verify passing tests.", mode=ProductMode.INVESTIGATE, domain=None
        ).id
        service.run_session(session_id)
    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=stopped_runner)
        report = service.get_report(session_id)
        assert report.failed_checks == [HISTORICAL_CHECK_PREFIX + "No test results supplied."]
        assert report.checks_performed == [HISTORICAL_CHECK_PREFIX + "Looked for executed tests."]
        assert report.verification_status == "not_verified"
        assert report.confidence_level == "insufficient_evidence"
        assert report.final_conclusion is None
        assert report.reflection is None
        assert report.recommended_next_action == HISTORICAL_NEXT_ACTION

        # A current passing verification takes precedence over recovery history.
        def recovered_runner(raw_input: str, *, session_id: str) -> PolyaState:
            state = successful_runner(raw_input, session_id=session_id)
            state["events"] = [
                *stopped_runner(raw_input, session_id=session_id)["events"],
                *state["events"],
            ]
            return state

        recovered_service = PolyaSessionService(db_session, runner=recovered_runner)
        recovered_id = recovered_service.create_session(
            raw_input="Verify passing tests after recovery.",
            mode=ProductMode.INVESTIGATE,
            domain=None,
        ).id
        recovered_service.run_session(recovered_id)
        report = recovered_service.get_report(recovered_id)
        assert report.failed_checks == []
        assert report.checks_performed == ["service test verification"]
        assert report.verification_status == "passed"


@pytest.mark.skipif(not RUN_DB_TESTS, reason=DB_TEST_SKIP_REASON)
def test_persisted_report_preserves_current_scope_limitations(session_factory: sessionmaker):
    from app.cognition.report_metadata import SCOPE_LIMITATION_PREFIX
    from app.models.contracts import StructuredProblem

    def scoped_runner(raw_input: str, *, session_id: str) -> PolyaState:
        state = successful_runner(raw_input, session_id=session_id)
        state["structured_problem"] = StructuredProblem(
            core_question="Explain and propose a check.",
            problem_type="research",
            knowns=[],
            unknowns=[],
            constraints=[SCOPE_LIMITATION_PREFIX + "Actual cause is still unknown."],
            success_criteria=["Give an explanation, not an observed diagnosis."],
        )
        return state

    with session_factory() as db_session:
        service = PolyaSessionService(db_session, runner=scoped_runner)
        sid = service.create_session(
            raw_input="Explain the mechanism.", mode=ProductMode.INVESTIGATE, domain=None
        ).id
        service.run_session(sid)
    with session_factory() as db_session:
        report = PolyaSessionService(db_session, runner=scoped_runner).get_report(sid)
        assert report.verification_status == "passed"
        assert report.open_questions == ["Actual cause is still unknown."]
