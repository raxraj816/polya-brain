"""SQLAlchemy-backed trace persistence and reads."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ProblemSession, ReasoningEvent
from app.graph.state import StateEvent
from app.tracing.events import ROUTE_DECISION_EVENT_TYPE, prepare_trace_event_writes
from app.tracing.metrics import trace_metrics
from app.tracing.sanitization import sanitize_json_mapping, sanitize_text


@dataclass(frozen=True)
class TraceEventPage:
    """A bounded ordered page of trace events."""

    events: list[ReasoningEvent]
    has_more: bool
    next_after_sequence: int | None


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
        trace_metrics.record_append_attempt()
        start_time = perf_counter()
        if not events:
            trace_metrics.record_append_success(
                persisted_events=0,
                route_decision_events=0,
                redactions=0,
                duration_ms=(perf_counter() - start_time) * 1000,
            )
            return []

        try:
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
            trace_metrics.record_append_success(
                persisted_events=len(records),
                route_decision_events=sum(
                    1 for write in writes if write.event_type == ROUTE_DECISION_EVENT_TYPE
                ),
                redactions=sum(write.redaction_count for write in writes),
                duration_ms=(perf_counter() - start_time) * 1000,
            )
            return records
        except Exception:
            trace_metrics.record_append_failure(
                duration_ms=(perf_counter() - start_time) * 1000,
            )
            raise

    def session_exists(self, session_id: UUID) -> bool:
        """Return whether a problem session exists."""
        return (
            self._session.scalar(select(ProblemSession.id).where(ProblemSession.id == session_id))
            is not None
        )

    def count_events(self, session_id: UUID, *, event_type: str) -> int:
        """Count one durable event type for cross-resume safety budgets."""
        value = self._session.scalar(
            select(func.count(ReasoningEvent.id)).where(
                ReasoningEvent.session_id == session_id,
                ReasoningEvent.event_type == event_type,
            )
        )
        return int(value or 0)

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
        """Return a bounded ordered page of persisted trace events."""
        if not self.session_exists(session_id):
            return None

        statement = select(ReasoningEvent).where(ReasoningEvent.session_id == session_id)
        if after_sequence is not None:
            statement = statement.where(ReasoningEvent.sequence_number > after_sequence)
        if engine_name is not None:
            statement = statement.where(ReasoningEvent.engine_name == engine_name)
        if event_type is not None:
            statement = statement.where(ReasoningEvent.event_type == event_type)
        if reasoning_mode is not None:
            statement = statement.where(ReasoningEvent.reasoning_mode == reasoning_mode)

        records = list(
            self._session.scalars(
                statement.order_by(ReasoningEvent.sequence_number).limit(limit + 1)
            )
        )
        events = records[:limit]
        next_after_sequence = (
            events[-1].sequence_number if len(records) > limit and events else None
        )
        return TraceEventPage(
            events=events,
            has_more=len(records) > limit,
            next_after_sequence=next_after_sequence,
        )

    @staticmethod
    def sanitize_record(record: ReasoningEvent) -> ReasoningEvent:
        """Sanitize an already-loaded record before exposing it."""
        record.summary = sanitize_text(record.summary)
        record.event_metadata = sanitize_json_mapping(record.event_metadata)
        return record
