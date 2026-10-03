"""Chapter 10 problem session API routes."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.cognition.bootstrap import build_representation_session_runner
from app.cognition.persistence import SQLAlchemyCognitiveStateRepository
from app.db.models import Artifact, ProblemSession
from app.graph.state import StateEvent
from app.memory import SQLAlchemyMemoryRepository
from app.models.contracts import ProductMode
from app.models.sessions import (
    ClarificationAnswerRequest,
    CreateSessionRequest,
    RunSessionResponse,
    SessionReportResponse,
    SessionResponse,
)
from app.sessions import (
    PolyaSessionService,
    SessionConflictError,
    SessionNotFoundError,
    SessionRunFailedError,
)
from app.sessions.admission import RunAdmissionPolicy, UsageLimitError
from app.sessions.service import SessionRunResult
from app.sessions.source_check import SourceCheckSessionRunner
from app.sessions.write_admission import WriteAdmissionPolicy
from app.tracing.persistence import SQLAlchemyTraceRepository

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
DB_SESSION_DEPENDENCY = Depends(get_db_session)


class SessionService(Protocol):
    """API-facing session service behavior."""

    def create_session(
        self,
        *,
        raw_input: str,
        mode: ProductMode,
        domain: str | None,
    ) -> ProblemSession:
        """Create a persisted problem session."""
        ...

    def get_session(self, session_id: UUID) -> ProblemSession:
        """Read a persisted problem session."""
        ...

    def get_report(self, session_id: UUID) -> SessionReportResponse:
        """Read the auditable report assembled from canonical artifacts."""
        ...

    def run_session(self, session_id: UUID) -> SessionRunResult:
        """Run a persisted problem session."""
        ...

    def respond_to_session(self, session_id: UUID, answer: str) -> SessionRunResult:
        """Persist a clarification answer and resume a paused session."""
        ...


def get_session_service(
    request: Request,
    db_session: Session = DB_SESSION_DEPENDENCY,
) -> PolyaSessionService:
    """Build the database-backed cognitive session service for request handling."""
    trace_repository = SQLAlchemyTraceRepository(db_session)
    cognitive_repository = SQLAlchemyCognitiveStateRepository(db_session)
    memory_repository = SQLAlchemyMemoryRepository(db_session)

    def publish_progress(session_id: str, events: list[StateEvent]) -> None:
        if not events:
            return
        with request.app.state.session_factory() as progress_session:
            SQLAlchemyTraceRepository(progress_session).persist_events(
                session_id=UUID(session_id), events=events
            )
            progress_session.commit()

    source_input = None
    stored_session = None
    path_session_id = request.path_params.get("session_id")
    if path_session_id:
        try:
            parsed_session_id = UUID(str(path_session_id))
        except ValueError:
            parsed_session_id = None
        if parsed_session_id is not None:
            stored_session = db_session.get(ProblemSession, parsed_session_id)
            source_input = db_session.scalar(
                select(Artifact).where(
                    Artifact.session_id == parsed_session_id,
                    Artifact.artifact_type == "source_check_input",
                )
            )
    settings = request.app.state.settings
    if settings.auth_required:
        # Uploaded snapshots have their own explicitly consented temporary root.
        # Global host roots are operator-only until project permissions exist.
        settings = settings.model_copy(update={"artifact_allowed_roots": ""})
    runner = build_representation_session_runner(
        settings,
        mode_hint=ProductMode(stored_session.mode) if stored_session is not None else None,
        domain_hint=stored_session.domain if stored_session is not None else None,
        prior_research_query_count=lambda session_id: trace_repository.count_events(
            UUID(session_id),
            event_type="research_query_started",
        ),
        prior_evidence_loader=lambda session_id: cognitive_repository.load_evidence(
            UUID(session_id)
        ),
        semantic_memory=memory_repository,
        procedural_memory=memory_repository,
        performance_ledger=request.app.state.capability_performance_ledger,
        semantic_route_health_ledger=request.app.state.semantic_route_health_ledger,
        progress_writer=publish_progress,
    )
    return PolyaSessionService(
        db_session,
        write_policy=WriteAdmissionPolicy(db_session, settings),
        runner=(
            SourceCheckSessionRunner(
                request.app.state.settings,
                source_input.artifact_metadata,
                progress_writer=publish_progress,
                repair_lesson_loader=memory_repository.load_repair_lessons,
            )
            if source_input is not None
            else runner
        ),
        memory_repository=memory_repository,
        stale_run_timeout_seconds=settings.session_run_timeout_seconds,
        clarification_timeout_seconds=settings.clarification_timeout_seconds,
        admission_policy=(
            RunAdmissionPolicy(db_session, settings, db_session.info["owner_id"])
            if settings.auth_required
            else None
        ),
    )


SESSION_SERVICE_DEPENDENCY = Depends(get_session_service)


def _session_response(problem_session: ProblemSession) -> SessionResponse:
    return SessionResponse.model_validate(problem_session)


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a problem session",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "technical_investigation": {
                            "summary": "Technical investigation",
                            "value": {
                                "raw_input": (
                                    "Our API p95 latency jumped after deploy. "
                                    "Should we add Redis or inspect queries first?"
                                ),
                                "mode": "investigate",
                                "domain": "software_debugging",
                            },
                        }
                    }
                }
            }
        }
    },
)
def create_session(
    request: CreateSessionRequest,
    session_service: SessionService = SESSION_SERVICE_DEPENDENCY,
) -> SessionResponse:
    """Create a durable problem session before running the Polya loop."""
    problem_session = session_service.create_session(
        raw_input=request.raw_input,
        mode=request.mode,
        domain=request.domain,
    )
    return _session_response(problem_session)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Read a problem session",
)
def get_session(
    session_id: UUID,
    session_service: SessionService = SESSION_SERVICE_DEPENDENCY,
) -> SessionResponse:
    """Read one problem session summary."""
    try:
        problem_session = session_service.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _session_response(problem_session)


@router.get(
    "/{session_id}/report",
    response_model=SessionReportResponse,
    summary="Read an auditable problem-solving report",
)
def get_session_report(
    session_id: UUID,
    session_service: SessionService = SESSION_SERVICE_DEPENDENCY,
) -> SessionReportResponse:
    """Expose conclusion, evidence, checks, uncertainty, and next action."""
    try:
        return session_service.get_report(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{session_id}/run",
    response_model=RunSessionResponse,
    summary="Run a problem session through the cognitive runtime",
)
def run_session(
    session_id: UUID,
    session_service: SessionService = SESSION_SERVICE_DEPENDENCY,
) -> RunSessionResponse:
    """Run a created session synchronously through the available capabilities."""
    try:
        run_result = session_service.run_session(session_id)
    except UsageLimitError as exc:
        raise HTTPException(
            429, detail=str(exc), headers={"Retry-After": str(exc.retry_after)}
        ) from exc
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SessionRunFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"session run failed safely: {exc}",
        ) from exc

    session_payload = _session_response(run_result.session).model_dump()
    return RunSessionResponse.model_validate(
        {
            **session_payload,
            "event_count": run_result.event_count,
            "clarifying_questions": list(run_result.clarifying_questions),
        }
    )


@router.post(
    "/{session_id}/respond",
    response_model=RunSessionResponse,
    summary="Answer a clarification and resume a problem session",
)
def respond_to_session(
    session_id: UUID,
    request: ClarificationAnswerRequest,
    session_service: SessionService = SESSION_SERVICE_DEPENDENCY,
) -> RunSessionResponse:
    """Resume an awaiting session without discarding its persisted trace."""
    try:
        run_result = session_service.respond_to_session(session_id, request.answer)
    except UsageLimitError as exc:
        raise HTTPException(
            429, detail=str(exc), headers={"Retry-After": str(exc.retry_after)}
        ) from exc
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SessionRunFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"session resume failed safely: {exc}",
        ) from exc

    session_payload = _session_response(run_result.session).model_dump()
    return RunSessionResponse.model_validate(
        {
            **session_payload,
            "event_count": run_result.event_count,
            "clarifying_questions": list(run_result.clarifying_questions),
        }
    )
