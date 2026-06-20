"""SQLAlchemy-backed trace persistence and reads."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ProblemSession, ReasoningEvent
from app.graph.state import StateEvent
from app.tracing.events import prepare_trace_event_writes
from app.tracing.sanitization import sanitize_json_mapping, sanitize_text


class SQLAlchemyTraceRepository:
    """Persist and read durable user-visible reasoning events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def persist_events(
        self,
        *,
        session_id: UUID,
        events: list[StateEvent],
    ) -> list[ReasoningEvent]:
        """Append state events and derived route events for one problem session."""
        if not events:
            return []

        locked_session_id = self._session.scalar(
            select(ProblemSession.id).where(ProblemSession.id == session_id).with_for_update()
        )
        if locked_session_id is None:
            raise ValueError(f"problem session does not exist: {session_id}")

        latest_sequence_number = self._session.scalar(
            select(func.max(ReasoningEvent.sequence_number)).where(
                ReasoningEvent.session_id == session_id
            )
        )
        start_sequence_number = (
            0 if latest_sequence_number is None else int(latest_sequence_number) + 1
        )
        writes = prepare_trace_event_writes(
            events,
            start_sequence_number=start_sequence_number,
        )
        records = [
            ReasoningEvent(
                session_id=session_id,
                sequence_number=write.sequence_number,
                engine_name=write.engine_name,
                event_type=write.event_type,
                reasoning_mode=write.reasoning_mode.value,
                summary=write.summary,
                event_metadata=write.metadata,
            )
            for write in writes
        ]
        self._session.add_all(records)
        self._session.flush()
        return records

    def session_exists(self, session_id: UUID) -> bool:
        """Return whether a problem session exists."""
        return (
            self._session.scalar(select(ProblemSession.id).where(ProblemSession.id == session_id))
            is not None
        )

    def list_events(self, session_id: UUID) -> list[ReasoningEvent] | None:
        """Return ordered persisted trace events, or None for a missing session."""
        if not self.session_exists(session_id):
            return None

        return list(
            self._session.scalars(
                select(ReasoningEvent)
                .where(ReasoningEvent.session_id == session_id)
                .order_by(ReasoningEvent.sequence_number)
            )
        )

    @staticmethod
    def sanitize_record(record: ReasoningEvent) -> ReasoningEvent:
        """Sanitize an already-loaded record before exposing it."""
        record.summary = sanitize_text(record.summary)
        record.event_metadata = sanitize_json_mapping(record.event_metadata)
        return record
