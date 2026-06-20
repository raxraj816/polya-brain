"""API models for user-visible reasoning traces."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, JsonValue

from app.models.contracts import ContractModel, NonEmptyStr, ReasoningMode


class TraceEventResponse(ContractModel):
    """One persisted event in the user-visible reasoning trace."""

    id: UUID
    sequence_number: int = Field(ge=0)
    engine_name: NonEmptyStr
    event_type: NonEmptyStr
    reasoning_mode: ReasoningMode
    summary: NonEmptyStr
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime


class TraceEventsResponse(ContractModel):
    """Ordered trace response for one problem session."""

    session_id: UUID
    events: list[TraceEventResponse] = Field(default_factory=list)
    limit: int = Field(ge=1)
    has_more: bool = False
    next_after_sequence: int | None = Field(default=None, ge=0)
