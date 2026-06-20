"""Read-only reasoning trace API routes."""

from __future__ import annotations

from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.db.models import ReasoningEvent
from app.models.contracts import ReasoningMode
from app.models.trace import TraceEventResponse, TraceEventsResponse
from app.tracing.persistence import SQLAlchemyTraceRepository, TraceEventPage
from app.tracing.sanitization import sanitize_json_mapping, sanitize_text

router = APIRouter(prefix="/api/v1/sessions", tags=["events"])
DB_SESSION_DEPENDENCY = Depends(get_db_session)


class TraceReader(Protocol):
    """Read side of the trace repository used by the API route."""

    def list_events(
        self,
        session_id: UUID,
        *,
        after_sequence: int | None = None,
        limit: int = 100,
        engine_name: str | None = None,
        event_type: str | None = None,
        reasoning_mode: str | None = None,
    ) -> TraceEventPage | None:
        """Return ordered event page, or None when the session is missing."""
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
    after_sequence: Annotated[int | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    engine_name: Annotated[str | None, Query(min_length=1)] = None,
    event_type: Annotated[str | None, Query(min_length=1)] = None,
    reasoning_mode: ReasoningMode | None = None,
    trace_reader: TraceReader = TRACE_REPOSITORY_DEPENDENCY,
) -> TraceEventsResponse:
    """Fetch the deterministic reasoning trace for one problem session."""
    event_page = trace_reader.list_events(
        session_id,
        after_sequence=after_sequence,
        limit=limit,
        engine_name=engine_name,
        event_type=event_type,
        reasoning_mode=reasoning_mode.value if reasoning_mode is not None else None,
    )
    if event_page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"problem session not found: {session_id}",
        )

    return TraceEventsResponse(
        session_id=session_id,
        events=[_trace_event_response(event) for event in event_page.events],
        limit=limit,
        has_more=event_page.has_more,
        next_after_sequence=event_page.next_after_sequence,
    )
