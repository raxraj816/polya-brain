"""Validated persistence boundary for Chapter 13 representation outputs."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ProblemSession
from app.db.models import StructuredProblem as StructuredProblemRecord
from app.engines import EngineRunOutput, EngineStatus
from app.models.contracts import StructuredProblem
from app.tracing.persistence import SQLAlchemyTraceRepository


@dataclass(frozen=True)
class PersistedProblemRepresentationRun:
    """Rows accepted from one engine output inside the caller's transaction."""

    structured_problem: StructuredProblemRecord | None
    event_count: int


class SQLAlchemyStructuredProblemRepository:
    """Persist only successfully validated canonical representation output."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def persist_successful_output(
        self,
        *,
        session_id: UUID,
        output: EngineRunOutput,
    ) -> StructuredProblemRecord:
        """Insert or refresh one canonical row after an accepted engine result."""
        if output.result.status is not EngineStatus.OK:
            raise ValueError("only an ok representation result can be persisted canonically")
        raw_structured_problem = output.state_delta.get("structured_problem")
        if raw_structured_problem is None:
            raise ValueError("ok representation result is missing structured_problem state")
        structured_problem = StructuredProblem.model_validate(raw_structured_problem)
        return self.upsert(session_id=session_id, structured_problem=structured_problem)

    def upsert(
        self,
        *,
        session_id: UUID,
        structured_problem: StructuredProblem,
    ) -> StructuredProblemRecord:
        """Insert or refresh one already validated canonical problem contract."""
        if self._session.get(ProblemSession, session_id) is None:
            raise ValueError(f"problem session does not exist: {session_id}")

        record = self._session.scalar(
            select(StructuredProblemRecord).where(StructuredProblemRecord.session_id == session_id)
        )
        values = structured_problem.model_dump(mode="json")
        if record is None:
            record = StructuredProblemRecord(session_id=session_id, **values)
            self._session.add(record)
        else:
            for field_name, value in values.items():
                setattr(record, field_name, value)
        self._session.flush()
        return record


class SQLAlchemyProblemRepresentationRunRepository:
    """Atomically stage trace plus accepted canonical output in one DB session."""

    def __init__(self, session: Session) -> None:
        self._structured_problem_repository = SQLAlchemyStructuredProblemRepository(session)
        self._trace_repository = SQLAlchemyTraceRepository(session)

    def persist_run_output(
        self,
        *,
        session_id: UUID,
        output: EngineRunOutput,
    ) -> PersistedProblemRepresentationRun:
        """Persist every trace, but only canonicalize successful output."""
        record = None
        if output.result.status is EngineStatus.OK:
            record = self._structured_problem_repository.persist_successful_output(
                session_id=session_id,
                output=output,
            )
        raw_events = output.state_delta.get("events", [])
        events = list(raw_events) if isinstance(raw_events, list) else []
        event_records = self._trace_repository.persist_events(
            session_id=session_id,
            events=events,
        )
        return PersistedProblemRepresentationRun(
            structured_problem=record,
            event_count=len(event_records),
        )
