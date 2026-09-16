"""Chapter 10 session creation and synchronous stub-run service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.cognition.persistence import SQLAlchemyCognitiveStateRepository
from app.cognition.source_patch_report import source_patch_checks, source_patch_conclusion
from app.config import get_settings
from app.db.models import (
    ClarificationRequest,
    EvidenceItem,
    KnowledgeGap,
    PlanTask,
    ProblemSession,
    ReasoningEvent,
    VerificationReport,
    utc_now,
)
from app.graph.chapter10_stub import run_chapter10_stub_graph
from app.graph.state import PolyaState, StateEvent
from app.memory.repository import SQLAlchemyMemoryRepository
from app.models.contracts import ProductMode, ReasoningMode
from app.models.sessions import (
    SessionReportEvidence,
    SessionReportResponse,
)
from app.problem_understanding.persistence import SQLAlchemyStructuredProblemRepository
from app.sessions.admission import RunAdmissionPolicy, UsageLimitError, resource_limits
from app.tracing.persistence import SQLAlchemyTraceRepository
from app.tracing.sanitization import sanitize_text

SESSION_STATUS_CREATED = "created"
SESSION_STATUS_RUNNING = "running"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_FAILED = "failed"
SESSION_STATUS_AWAITING_USER_INPUT = "awaiting_user_input"
VERIFICATION_STATUS_RUN_EXPIRED = "run_expired"
VERIFICATION_STATUS_AWAITING_USER_INPUT = "awaiting_user_input"
VERIFICATION_STATUS_CLARIFICATION_EXPIRED = "clarification_expired"
CLARIFICATION_STATUS_PENDING = "pending"
CLARIFICATION_STATUS_ANSWERED = "answered"
CLARIFICATION_STATUS_EXPIRED = "expired"


class SessionRunner(Protocol):
    """Callable graph runner used by the session service."""

    def __call__(
        self,
        raw_input: str,
        *,
        session_id: str,
    ) -> PolyaState | SessionExecutionResult:
        """Run a graph for a persisted session id."""
        ...


class SessionResumeRunner(Protocol):
    """Callable that re-runs understanding with one user clarification."""

    def __call__(
        self,
        raw_input: str,
        answer: str,
        *,
        session_id: str,
    ) -> PolyaState | SessionExecutionResult:
        """Resume the same logical session with the user's answer."""
        ...


class SessionNotFoundError(Exception):
    """Raised when a requested problem session does not exist."""


class SessionConflictError(Exception):
    """Raised when a session cannot accept the requested state transition."""


class SessionRunFailedError(Exception):
    """Raised after a run failure has been recorded on the session."""


@dataclass(frozen=True)
class SessionRunResult:
    """A completed run and its persisted trace count."""

    session: ProblemSession
    event_count: int
    clarifying_questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionExecutionResult:
    """Runner output with an explicit durable session disposition."""

    state: PolyaState
    awaiting_user_input: bool = False
    clarifying_questions: tuple[str, ...] = ()
    persisted_event_count: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.persisted_event_count <= len(self.state["events"]):
            raise ValueError("persisted trace prefix must fit the returned state")
        if self.awaiting_user_input and not self.clarifying_questions:
            raise ValueError("awaiting_user_input requires clarifying_questions")
        if not self.awaiting_user_input and self.clarifying_questions:
            raise ValueError("completed execution cannot carry clarifying_questions")


def _verification_status(state: PolyaState) -> str:
    verification = state["verification"]
    if verification is None:
        return "not_verified"
    return "passed" if verification.passed else "failed"


def _session_conflict_message(problem_session: ProblemSession) -> str:
    return f"problem session {problem_session.id} is {problem_session.status}, not created"


class PolyaSessionService:
    """Database-backed session workflow for the Chapter 10 API shell."""

    def __init__(
        self,
        db_session: Session,
        *,
        runner: SessionRunner = run_chapter10_stub_graph,
        resume_runner: SessionResumeRunner | None = None,
        stale_run_timeout_seconds: int | None = None,
        clarification_timeout_seconds: int | None = None,
        memory_repository: SQLAlchemyMemoryRepository | None = None,
        admission_policy: RunAdmissionPolicy | None = None,
    ) -> None:
        self._db_session = db_session
        self._runner = runner
        self._resume_runner = resume_runner or self._default_resume_runner
        self._trace_repository = SQLAlchemyTraceRepository(db_session)
        self._structured_problem_repository = SQLAlchemyStructuredProblemRepository(db_session)
        self._cognitive_state_repository = SQLAlchemyCognitiveStateRepository(db_session)
        self._memory_repository = memory_repository
        self._admission_policy = admission_policy
        self._admission_id: UUID | None = None
        timeout_seconds = (
            get_settings().session_run_timeout_seconds
            if stale_run_timeout_seconds is None
            else stale_run_timeout_seconds
        )
        self._stale_run_timeout = timedelta(seconds=timeout_seconds)
        clarification_seconds = (
            get_settings().clarification_timeout_seconds
            if clarification_timeout_seconds is None
            else clarification_timeout_seconds
        )
        if clarification_seconds < 60:
            raise ValueError("clarification_timeout_seconds must be at least 60")
        self._clarification_timeout = timedelta(seconds=clarification_seconds)

    def _default_resume_runner(
        self,
        raw_input: str,
        answer: str,
        *,
        session_id: str,
    ) -> PolyaState | SessionExecutionResult:
        resumed_input = (
            f"{raw_input}\n\n"
            "USER CLARIFICATION (treat as additional problem information):\n"
            f"{answer}"
        )
        return self._runner(resumed_input, session_id=session_id)

    def create_session(
        self,
        *,
        raw_input: str,
        mode: ProductMode,
        domain: str | None,
    ) -> ProblemSession:
        """Create and commit a durable problem session."""
        problem_session = ProblemSession(
            user_id=self._db_session.info.get("owner_id"),
            raw_input=raw_input.strip(),
            mode=mode.value,
            domain=domain.strip() if domain is not None else None,
            status=SESSION_STATUS_CREATED,
        )
        self._db_session.add(problem_session)
        self._db_session.commit()
        self._db_session.refresh(problem_session)
        return problem_session

    def get_session(self, session_id: UUID) -> ProblemSession:
        """Return a persisted problem session or raise not found."""
        problem_session = self._db_session.get(ProblemSession, session_id)
        if problem_session is None:
            raise SessionNotFoundError(f"problem session not found: {session_id}")
        return problem_session

    def get_report(self, session_id: UUID) -> SessionReportResponse:
        """Assemble an auditable report from canonical persisted artifacts."""
        problem_session = self.get_session(session_id)
        evidence = list(
            self._db_session.scalars(
                select(EvidenceItem).where(EvidenceItem.session_id == session_id)
            )
        )
        gaps = list(
            self._db_session.scalars(
                select(KnowledgeGap).where(KnowledgeGap.session_id == session_id)
            )
        )
        verification = self._db_session.scalar(
            select(VerificationReport)
            .where(VerificationReport.session_id == session_id)
            .order_by(VerificationReport.created_at.desc())
            .limit(1)
        )
        reflection_event = self._db_session.scalar(
            select(ReasoningEvent)
            .where(
                ReasoningEvent.session_id == session_id,
                ReasoningEvent.event_type == "reflection_recorded",
            )
            .order_by(ReasoningEvent.sequence_number.desc())
            .limit(1)
        )

        evidence_used = [item for item in evidence if not item.contradicts_hypothesis_ids]
        evidence_against = [item for item in evidence if item.contradicts_hypothesis_ids]
        if verification is not None and verification.passed:
            reliable = bool(evidence_used) and all(
                item.reliability_score is not None and item.reliability_score >= 0.9
                for item in evidence_used
            )
            confidence_level = "high" if reliable else "medium"
        elif verification is not None:
            confidence_level = "low"
        else:
            confidence_level = "insufficient_evidence"

        source_patch_plan = self._db_session.scalar(
            select(PlanTask).where(
                PlanTask.session_id == session_id, PlanTask.tool_name == "source_patch_sandbox"
            )
        )
        if source_patch_plan is not None and verification is not None and verification.passed:
            confidence_level = "medium"
        reflection = reflection_event.event_metadata if reflection_event is not None else None
        questions = [item.description for item in gaps if not item.filled]
        if problem_session.status == SESSION_STATUS_AWAITING_USER_INPUT:
            clarification = self._db_session.scalar(
                select(ClarificationRequest)
                .where(
                    ClarificationRequest.session_id == session_id,
                    ClarificationRequest.status == CLARIFICATION_STATUS_PENDING,
                )
                .order_by(ClarificationRequest.requested_at.desc())
                .limit(1)
            )
            if clarification is not None:
                questions = list(dict.fromkeys([*clarification.questions, *questions]))
        if source_patch_plan is not None:
            questions.append(
                "Do additional integration or regression checks support this candidate edit?"
            )
        follow_ups = reflection.get("follow_up_actions", []) if reflection else []
        if isinstance(follow_ups, list) and follow_ups and isinstance(follow_ups[0], str):
            recommended_next_action = follow_ups[0]
        elif verification is not None and verification.passed:
            recommended_next_action = (
                "No further action is required for the stated success criteria."
            )
        elif verification is not None and verification.recommended_route:
            recommended_next_action = verification.recommended_route
        else:
            recommended_next_action = "Gather the missing evidence before drawing a conclusion."

        if source_patch_plan is not None:
            recommended_next_action = (
                "Review the candidate diff and run broader integration checks before applying it."
            )

        def report_evidence(item: EvidenceItem) -> SessionReportEvidence:
            return SessionReportEvidence(
                source_type=item.source_type,
                source_uri=item.source_uri,
                claim=item.claim,
                reliability_score=item.reliability_score,
                relevance_score=item.relevance_score,
            )

        return SessionReportResponse(
            session_id=session_id,
            final_conclusion=problem_session.final_answer,
            confidence_level=confidence_level,
            verification_status=problem_session.verification_status or "not_verified",
            evidence_used=[report_evidence(item) for item in evidence_used],
            evidence_against=[report_evidence(item) for item in evidence_against],
            checks_performed=(
                source_patch_checks()
                if source_patch_plan is not None
                and verification is not None
                and verification.passed
                else list(verification.checks_run)
                if verification
                else []
            ),
            failed_checks=list(verification.failed_checks) if verification else [],
            contradictions=list(verification.contradictions) if verification else [],
            open_questions=questions,
            recommended_next_action=recommended_next_action,
            reflection=reflection,
            audit_trace_path=f"/api/v1/sessions/{session_id}/events",
        )

    def _admit_run(self, session_id: UUID) -> None:
        if self._admission_policy is None:
            return
        try:
            self._admission_id = self._admission_policy.acquire(session_id)
        except UsageLimitError:
            self._db_session.rollback()
            raise
        self._trace_repository.persist_events(
            session_id=session_id,
            events=[
                StateEvent(
                    engine_name="run_admission",
                    event_type="run_admitted",
                    reasoning_mode=ReasoningMode.EXECUTE,
                    summary="Reserved one daily invocation and an active run slot before dispatch.",
                    metadata={
                        "admission_id": str(self._admission_id),
                        "allowance_unit": "bounded_invocation",
                        "resource_limits": resource_limits(self._admission_policy.settings),
                    },
                )
            ],
        )

    def _finish_admission(self, session_id: UUID) -> None:
        if self._admission_policy is None or self._admission_id is None:
            return
        record = self._db_session.get(ProblemSession, session_id)
        if record is None or record.status == SESSION_STATUS_RUNNING:
            # An interrupted or unrecorded outcome must retain its concurrency slot.
            return
        self._admission_policy.finish(self._admission_id, record.status)
        self._admission_id = None

    def _claim_created_session_for_run(self, session_id: UUID) -> ProblemSession:
        """Atomically move one created session to running, or raise."""
        now = utc_now()
        claimed_session_id = self._db_session.scalar(
            update(ProblemSession)
            .where(
                ProblemSession.id == session_id,
                ProblemSession.status == SESSION_STATUS_CREATED,
            )
            .values(status=SESSION_STATUS_RUNNING, run_started_at=now)
            .returning(ProblemSession.id)
        )
        if claimed_session_id is None:
            problem_session = self._db_session.get(ProblemSession, session_id)
            if problem_session is None:
                self._db_session.rollback()
                raise SessionNotFoundError(f"problem session not found: {session_id}")
            if self._expire_stale_running_session(problem_session, now=now):
                self._db_session.commit()
                self._db_session.refresh(problem_session)
                raise SessionConflictError(_session_conflict_message(problem_session))
            conflict_message = _session_conflict_message(problem_session)
            self._db_session.rollback()
            raise SessionConflictError(conflict_message)

        self._admit_run(session_id)
        self._db_session.commit()
        problem_session = self._db_session.get(ProblemSession, claimed_session_id)
        if problem_session is None:
            raise SessionNotFoundError(f"problem session not found after claim: {session_id}")
        return problem_session

    def _expire_stale_running_session(
        self,
        problem_session: ProblemSession,
        *,
        now: datetime,
    ) -> bool:
        """Mark a stale running session failed without running it again."""
        if problem_session.status != SESSION_STATUS_RUNNING:
            return False
        if problem_session.run_started_at is None:
            # Legacy or interrupted Chapter 10 claims may be running without a start timestamp.
            # Treat them as stale so the run stops safely instead of remaining wedged.
            should_expire = True
        else:
            elapsed = now - problem_session.run_started_at
            should_expire = elapsed >= self._stale_run_timeout
        if not should_expire:
            return False

        problem_session.status = SESSION_STATUS_FAILED
        problem_session.completed_at = now
        problem_session.final_answer = (
            "PolyaBrain expired this run because it stayed in running state beyond "
            "the configured timeout. The session stopped safely and was not retried "
            "automatically."
        )
        problem_session.confidence = None
        problem_session.verification_status = VERIFICATION_STATUS_RUN_EXPIRED
        return True

    @staticmethod
    def _normalize_execution(
        result: PolyaState | SessionExecutionResult,
    ) -> SessionExecutionResult:
        if isinstance(result, SessionExecutionResult):
            return result
        return SessionExecutionResult(state=result)

    def _persist_pending_clarification(
        self,
        problem_session: ProblemSession,
        questions: tuple[str, ...],
        *,
        now: datetime,
    ) -> ClarificationRequest:
        request = ClarificationRequest(
            session_id=problem_session.id,
            questions=list(questions),
            status=CLARIFICATION_STATUS_PENDING,
            requested_at=now,
            expires_at=now + self._clarification_timeout,
        )
        self._db_session.add(request)
        return request

    def _apply_execution_result(
        self,
        problem_session: ProblemSession,
        execution: SessionExecutionResult,
    ) -> SessionRunResult:
        events = list(execution.state["events"])
        # Persist the accepted state, independent of each producer's event name.
        # Fused and deterministic capabilities do not necessarily emit the
        # legacy reflection/execution events themselves.
        for output in execution.state["execution_outputs"]:
            metadata = output.model_dump(mode="json")
            if not any(
                event.event_type == "execution_output_recorded" and event.metadata == metadata
                for event in events
            ):
                events.append(
                    StateEvent(
                        engine_name="cognitive_runtime",
                        event_type="execution_output_recorded",
                        reasoning_mode=ReasoningMode.EXECUTE,
                        summary=output.summary,
                        metadata=metadata,
                    )
                )
        reflection = execution.state["reflection"]
        if reflection is not None:
            metadata = reflection.model_dump(mode="json")
            if not any(
                event.event_type == "reflection_recorded" and event.metadata == metadata
                for event in events
            ):
                events.append(
                    StateEvent(
                        engine_name="cognitive_runtime",
                        event_type="reflection_recorded",
                        reasoning_mode=ReasoningMode.REFLECT,
                        summary=reflection.outcome_summary,
                        metadata=metadata,
                    )
                )
        if execution.awaiting_user_input:
            events.append(
                StateEvent(
                    engine_name="cognitive_controller",
                    event_type="clarification_requested",
                    reasoning_mode=ReasoningMode.EXPLORE,
                    summary="Paused the session to request missing user-owned information.",
                    metadata={"questions": list(execution.clarifying_questions)},
                )
            )
        self._trace_repository.persist_events(
            session_id=problem_session.id,
            events=events[execution.persisted_event_count :],
        )
        structured_problem = execution.state["structured_problem"]
        if structured_problem is not None:
            self._structured_problem_repository.upsert(
                session_id=problem_session.id,
                structured_problem=structured_problem,
            )
        self._cognitive_state_repository.persist_state(
            session_id=problem_session.id,
            state=execution.state,
        )
        now = utc_now()
        if execution.awaiting_user_input:
            self._persist_pending_clarification(
                problem_session,
                execution.clarifying_questions,
                now=now,
            )
            problem_session.status = SESSION_STATUS_AWAITING_USER_INPUT
            problem_session.run_started_at = None
            problem_session.completed_at = None
            problem_session.final_answer = None
            problem_session.confidence = None
            problem_session.verification_status = VERIFICATION_STATUS_AWAITING_USER_INPUT
        else:
            problem_session.status = SESSION_STATUS_COMPLETED
            problem_session.completed_at = now
            problem_session.final_answer = execution.state["final_answer"]
            patch_task = next(
                (
                    task
                    for task in execution.state["plan"]
                    if task.tool_name == "source_patch_sandbox"
                ),
                None,
            )
            if (
                patch_task is not None
                and execution.state["verification"]
                and execution.state["verification"].passed
            ):
                problem_session.final_answer = source_patch_conclusion(patch_task.params)
            problem_session.confidence = None
            problem_session.verification_status = _verification_status(execution.state)
            if self._memory_repository is not None:
                self._memory_repository.learn_verified_outcome(
                    problem_session.id,
                    execution.state,
                )
        self._db_session.commit()
        self._db_session.refresh(problem_session)
        return SessionRunResult(
            session=problem_session,
            event_count=int(
                self._db_session.scalar(
                    select(func.count(ReasoningEvent.id)).where(
                        ReasoningEvent.session_id == problem_session.id
                    )
                )
                or 0
            ),
            clarifying_questions=execution.clarifying_questions,
        )

    def _pending_clarification(self, session_id: UUID) -> ClarificationRequest | None:
        return self._db_session.scalar(
            select(ClarificationRequest)
            .where(
                ClarificationRequest.session_id == session_id,
                ClarificationRequest.status == CLARIFICATION_STATUS_PENDING,
            )
            .order_by(ClarificationRequest.requested_at.desc())
            .with_for_update()
        )

    def run_session(self, session_id: UUID) -> SessionRunResult:
        """Run a created session through the deterministic Chapter 10 graph."""
        problem_session = self._claim_created_session_for_run(session_id)

        try:
            execution = self._normalize_execution(
                self._runner(
                    problem_session.raw_input,
                    session_id=str(problem_session.id),
                )
            )
            return self._apply_execution_result(problem_session, execution)
        except Exception as exc:
            self._db_session.rollback()
            failed_session = self._db_session.get(ProblemSession, session_id)
            if failed_session is not None:
                failed_session.status = SESSION_STATUS_FAILED
                failed_session.completed_at = utc_now()
                failed_session.final_answer = (
                    "PolyaBrain could not complete the cognitive session run. "
                    "The session stopped safely before returning a conclusion."
                )
                failed_session.confidence = None
                failed_session.verification_status = "run_failed"
                self._db_session.commit()
            sanitized_error = sanitize_text(f"{type(exc).__name__}: {exc}")
            raise SessionRunFailedError(sanitized_error) from exc
        finally:
            self._finish_admission(session_id)

    def respond_to_session(self, session_id: UUID, answer: str) -> SessionRunResult:
        """Persist one clarification answer and resume the same session."""
        normalized_answer = answer.strip()
        if not normalized_answer:
            raise ValueError("clarification answer must not be blank")

        problem_session = self._db_session.scalar(
            select(ProblemSession).where(ProblemSession.id == session_id).with_for_update()
        )
        if problem_session is None:
            self._db_session.rollback()
            raise SessionNotFoundError(f"problem session not found: {session_id}")
        if problem_session.status != SESSION_STATUS_AWAITING_USER_INPUT:
            conflict_message = (
                f"problem session {session_id} is {problem_session.status}, "
                f"not {SESSION_STATUS_AWAITING_USER_INPUT}"
            )
            self._db_session.rollback()
            raise SessionConflictError(conflict_message)

        clarification = self._pending_clarification(session_id)
        if clarification is None:
            self._db_session.rollback()
            raise SessionConflictError(f"problem session {session_id} has no pending clarification")

        now = utc_now()
        if now >= clarification.expires_at:
            clarification.status = CLARIFICATION_STATUS_EXPIRED
            problem_session.status = SESSION_STATUS_FAILED
            problem_session.completed_at = now
            problem_session.final_answer = (
                "PolyaBrain stopped safely because the clarification request expired "
                "before the missing information was provided."
            )
            problem_session.verification_status = VERIFICATION_STATUS_CLARIFICATION_EXPIRED
            self._db_session.commit()
            raise SessionConflictError(
                f"clarification request expired for problem session {session_id}"
            )

        self._admit_run(session_id)
        clarification.answer = normalized_answer
        clarification.answered_at = now
        clarification.status = CLARIFICATION_STATUS_ANSWERED
        problem_session.status = SESSION_STATUS_RUNNING
        problem_session.run_started_at = now
        response_event = StateEvent(
            engine_name="human_input",
            event_type="clarification_answered",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Received user clarification and resumed the problem-solving session.",
            metadata={
                "clarification_request_id": str(clarification.id),
                "answer": sanitize_text(normalized_answer),
            },
        )
        self._trace_repository.persist_events(
            session_id=session_id,
            events=[response_event],
        )
        self._db_session.commit()

        try:
            execution = self._normalize_execution(
                self._resume_runner(
                    problem_session.raw_input,
                    normalized_answer,
                    session_id=str(problem_session.id),
                )
            )
            return self._apply_execution_result(problem_session, execution)
        except Exception as exc:
            self._db_session.rollback()
            failed_session = self._db_session.get(ProblemSession, session_id)
            if failed_session is not None:
                failed_session.status = SESSION_STATUS_FAILED
                failed_session.completed_at = utc_now()
                failed_session.final_answer = (
                    "PolyaBrain could not resume after receiving clarification. "
                    "The session stopped safely before returning a conclusion."
                )
                failed_session.confidence = None
                failed_session.verification_status = "resume_failed"
                self._db_session.commit()
            sanitized_error = sanitize_text(f"{type(exc).__name__}: {exc}")
            raise SessionRunFailedError(sanitized_error) from exc
        finally:
            self._finish_admission(session_id)
