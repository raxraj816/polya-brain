"""Chapter 10 problem session API routes."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.cognition.bootstrap import build_representation_session_runner
from app.cognition.persistence import SQLAlchemyCognitiveStateRepository
from app.db.models import ProblemSession
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
from app.sessions.service import SessionRunResult
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
    runner = build_representation_session_runner(
        request.app.state.settings,
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
    )
    return PolyaSessionService(
        db_session,
        runner=runner,
        memory_repository=memory_repository,
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
