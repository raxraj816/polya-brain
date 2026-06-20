"""Chapter 10 problem session API routes."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.db.models import ProblemSession
from app.models.contracts import ProductMode
from app.models.sessions import CreateSessionRequest, RunSessionResponse, SessionResponse
from app.sessions import (
    PolyaSessionService,
    SessionConflictError,
    SessionNotFoundError,
    SessionRunFailedError,
)
from app.sessions.service import SessionRunResult

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

    def run_session(self, session_id: UUID) -> SessionRunResult:
        """Run a persisted problem session."""
        ...


def get_session_service(
    db_session: Session = DB_SESSION_DEPENDENCY,
) -> PolyaSessionService:
    """Build the database-backed session service for request handling."""
    return PolyaSessionService(db_session)


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


@router.post(
    "/{session_id}/run",
    response_model=RunSessionResponse,
    summary="Run a problem session through the Chapter 10 stub graph",
)
def run_session(
    session_id: UUID,
    session_service: SessionService = SESSION_SERVICE_DEPENDENCY,
) -> RunSessionResponse:
    """Run a created session synchronously through the deterministic stub graph."""
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
        {**session_payload, "event_count": run_result.event_count}
    )
