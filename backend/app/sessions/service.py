"""Chapter 10 session creation and synchronous stub-run service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import ProblemSession, utc_now
from app.graph.chapter10_stub import run_chapter10_stub_graph
from app.graph.state import PolyaState
from app.models.contracts import ProductMode
from app.tracing.persistence import SQLAlchemyTraceRepository
from app.tracing.sanitization import sanitize_text

SESSION_STATUS_CREATED = "created"
SESSION_STATUS_RUNNING = "running"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_FAILED = "failed"


class SessionRunner(Protocol):
    """Callable graph runner used by the session service."""

    def __call__(self, raw_input: str, *, session_id: str) -> PolyaState:
        """Run a graph for a persisted session id."""
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


def _verification_status(state: PolyaState) -> str:
    verification = state["verification"]
    if verification is None:
        return "stub_not_verified"
    return "stub_passed" if verification.passed else "stub_failed"


def _session_conflict_message(problem_session: ProblemSession) -> str:
    return f"problem session {problem_session.id} is {problem_session.status}, not created"


class PolyaSessionService:
    """Database-backed session workflow for the Chapter 10 API shell."""

    def __init__(
        self,
        db_session: Session,
        *,
        runner: SessionRunner = run_chapter10_stub_graph,
    ) -> None:
        self._db_session = db_session
        self._runner = runner
        self._trace_repository = SQLAlchemyTraceRepository(db_session)

    def create_session(
        self,
        *,
        raw_input: str,
        mode: ProductMode,
        domain: str | None,
    ) -> ProblemSession:
        """Create and commit a durable problem session."""
        problem_session = ProblemSession(
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

    def _claim_created_session_for_run(self, session_id: UUID) -> ProblemSession:
        """Atomically move one created session to running, or raise."""
        claimed_session_id = self._db_session.scalar(
            update(ProblemSession)
            .where(
                ProblemSession.id == session_id,
                ProblemSession.status == SESSION_STATUS_CREATED,
            )
            .values(status=SESSION_STATUS_RUNNING)
            .returning(ProblemSession.id)
        )
        if claimed_session_id is None:
            problem_session = self._db_session.get(ProblemSession, session_id)
            if problem_session is None:
                self._db_session.rollback()
                raise SessionNotFoundError(f"problem session not found: {session_id}")
            conflict_message = _session_conflict_message(problem_session)
            self._db_session.rollback()
            raise SessionConflictError(conflict_message)

        self._db_session.commit()
        problem_session = self._db_session.get(ProblemSession, claimed_session_id)
        if problem_session is None:
            raise SessionNotFoundError(f"problem session not found after claim: {session_id}")
        return problem_session

    def run_session(self, session_id: UUID) -> SessionRunResult:
        """Run a created session through the deterministic Chapter 10 graph."""
        problem_session = self._claim_created_session_for_run(session_id)

        try:
            state = self._runner(problem_session.raw_input, session_id=str(problem_session.id))
            records = self._trace_repository.persist_events(
                session_id=problem_session.id,
                events=state["events"],
            )
            problem_session.status = SESSION_STATUS_COMPLETED
            problem_session.completed_at = utc_now()
            problem_session.final_answer = state["final_answer"]
            problem_session.confidence = None
            problem_session.verification_status = _verification_status(state)
            self._db_session.commit()
            self._db_session.refresh(problem_session)
            return SessionRunResult(session=problem_session, event_count=len(records))
        except Exception as exc:
            self._db_session.rollback()
            failed_session = self._db_session.get(ProblemSession, session_id)
            if failed_session is not None:
                failed_session.status = SESSION_STATUS_FAILED
                failed_session.completed_at = utc_now()
                failed_session.final_answer = (
                    "PolyaBrain could not complete the Chapter 10 stub graph run. "
                    "The session stopped safely before returning an investigation result."
                )
                failed_session.confidence = None
                failed_session.verification_status = "run_failed"
                self._db_session.commit()
            sanitized_error = sanitize_text(f"{type(exc).__name__}: {exc}")
            raise SessionRunFailedError(sanitized_error) from exc
