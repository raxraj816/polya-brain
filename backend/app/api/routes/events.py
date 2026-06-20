"""Read-only reasoning trace API routes."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.db.models import ReasoningEvent
from app.models.contracts import ReasoningMode
from app.models.trace import TraceEventResponse, TraceEventsResponse
from app.tracing.persistence import SQLAlchemyTraceRepository
from app.tracing.sanitization import sanitize_json_mapping, sanitize_text

router = APIRouter(prefix="/api/v1/sessions", tags=["events"])
DB_SESSION_DEPENDENCY = Depends(get_db_session)


class TraceReader(Protocol):
    """Read side of the trace repository used by the API route."""

    def list_events(self, session_id: UUID) -> list[ReasoningEvent] | None:
        """Return ordered events, or None when the session is missing."""
        ...


def get_trace_repository(
    db_session: Session = DB_SESSION_DEPENDENCY,
) -> SQLAlchemyTraceRepository:
    """Build the SQLAlchemy trace repository for request handling."""
    return SQLAlchemyTraceRepository(db_session)


TRACE_REPOSITORY_DEPENDENCY = Depends(get_trace_repository)


def _trace_event_response(record: ReasoningEvent) -> TraceEventResponse:
    return TraceEventResponse(
        id=record.id,
        sequence_number=record.sequence_number,
        engine_name=record.engine_name,
        event_type=record.event_type,
        reasoning_mode=ReasoningMode(record.reasoning_mode),
        summary=sanitize_text(record.summary),
        metadata=sanitize_json_mapping(record.event_metadata),
        created_at=record.created_at,
    )


@router.get("/{session_id}/events", response_model=TraceEventsResponse)
def list_session_events(
    session_id: UUID,
    trace_reader: TraceReader = TRACE_REPOSITORY_DEPENDENCY,
) -> TraceEventsResponse:
    """Fetch the deterministic reasoning trace for one problem session."""
    events = trace_reader.list_events(session_id)
    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"problem session not found: {session_id}",
        )

    return TraceEventsResponse(
        session_id=session_id,
        events=[_trace_event_response(event) for event in events],
    )
