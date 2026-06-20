"""API models for Chapter 10 problem sessions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.contracts import ContractModel, NonEmptyStr, ProductMode, Score


class CreateSessionRequest(ContractModel):
    """Create a new PolyaBrain problem session."""

    raw_input: NonEmptyStr = Field(
        examples=[
            "Our API p95 latency jumped after deploy. Should we add Redis or inspect queries first?"
        ]
    )
    mode: ProductMode = ProductMode.INVESTIGATE
    domain: NonEmptyStr | None = None


class SessionResponse(ContractModel):
    """Public summary for one problem session."""

    id: UUID
    raw_input: NonEmptyStr
    domain: NonEmptyStr | None = None
    mode: ProductMode
    status: NonEmptyStr
    created_at: datetime
    completed_at: datetime | None = None
    final_answer: NonEmptyStr | None = None
    confidence: Score | None = None
    verification_status: NonEmptyStr | None = None


class RunSessionResponse(SessionResponse):
    """Session summary returned after a synchronous Chapter 10 run."""

    event_count: int = Field(ge=0)
