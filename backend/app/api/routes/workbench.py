"""Bounded read models for the local Investigator workbench."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.db import models as records
from app.models.contracts import (
    ContractModel,
    EvidenceItem,
    Hypothesis,
    KnowledgeGap,
    StructuredProblem,
)
from app.models.sessions import SessionResponse
from app.sessions.write_admission import WriteAdmissionPolicy
from app.tracing.sanitization import sanitize_json_value

router = APIRouter(prefix="/api/v1/sessions", tags=["workbench"])
DB = Depends(get_db_session)


class SessionHistoryResponse(ContractModel):
    sessions: list[SessionResponse]
    has_more: bool
    next_offset: int | None = None


class InvestigationArtifactsResponse(ContractModel):
    session_id: UUID
    structured_problem: StructuredProblem | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    gaps: list[KnowledgeGap] = Field(default_factory=list)


@router.get("", response_model=SessionHistoryResponse)
def list_sessions(
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    q: Annotated[str, Query(max_length=200)] = "",
    status: Annotated[
        str | None, Query(pattern="^(created|running|completed|failed|awaiting_user_input)$")
    ] = None,
    feedback_type: Literal["useful", "wrong", "incomplete", "unsafe"] | None = None,
    db: Session = DB,
) -> SessionHistoryResponse:
    statement = select(records.ProblemSession).where(
        records.ProblemSession.user_id == db.info.get("owner_id")
    )
    if q.strip():
        statement = statement.where(
            records.ProblemSession.raw_input.icontains(q.strip(), autoescape=True)
        )
    if status is not None:
        statement = statement.where(records.ProblemSession.status == status)
    if feedback_type is not None:
        statement = statement.where(
            select(records.HumanFeedback.id)
            .where(
                records.HumanFeedback.session_id == records.ProblemSession.id,
                records.HumanFeedback.feedback_type == feedback_type,
            )
            .exists()
        )
    rows = list(
        db.scalars(
            statement.order_by(
                records.ProblemSession.created_at.desc(), records.ProblemSession.id.desc()
            )
            .offset(offset)
            .limit(limit + 1)
        )
    )
    result = SessionHistoryResponse(
        sessions=[SessionResponse.model_validate(row) for row in rows[:limit]],
        has_more=len(rows) > limit,
        next_offset=offset + limit if len(rows) > limit else None,
    )
    return SessionHistoryResponse.model_validate(
        sanitize_json_value(result.model_dump(mode="json"))
    )


@router.get("/{session_id}/artifacts", response_model=InvestigationArtifactsResponse)
def get_artifacts(session_id: UUID, db: Session = DB) -> InvestigationArtifactsResponse:
    if db.get(records.ProblemSession, session_id) is None:
        raise HTTPException(status_code=404, detail="Problem session not found.")
    problem = db.scalar(
        select(records.StructuredProblem).where(records.StructuredProblem.session_id == session_id)
    )
    evidence = list(
        db.scalars(
            select(records.EvidenceItem)
            .where(records.EvidenceItem.session_id == session_id)
            .order_by(records.EvidenceItem.id)
        )
    )
    hypotheses = list(
        db.scalars(
            select(records.Hypothesis)
            .where(records.Hypothesis.session_id == session_id)
            .order_by(records.Hypothesis.confidence.desc().nullslast(), records.Hypothesis.id)
        )
    )
    gaps = list(
        db.scalars(
            select(records.KnowledgeGap)
            .where(records.KnowledgeGap.session_id == session_id)
            .order_by(records.KnowledgeGap.id)
        )
    )
    result = InvestigationArtifactsResponse(
        session_id=session_id,
        structured_problem=StructuredProblem.model_validate(problem) if problem else None,
        evidence=[EvidenceItem.model_validate(row) for row in evidence],
        hypotheses=[Hypothesis.model_validate(row) for row in hypotheses],
        gaps=[KnowledgeGap.model_validate(row) for row in gaps],
    )
    return InvestigationArtifactsResponse.model_validate(
        sanitize_json_value(result.model_dump(mode="json"))
    )


class FeedbackRequest(ContractModel):
    feedback_type: Literal["useful", "wrong", "incomplete", "unsafe"]
    correction: str | None = Field(default=None, max_length=10000)


class FeedbackResponse(FeedbackRequest):
    id: UUID
    session_id: UUID
    created_at: datetime


@router.post("/{session_id}/feedback", response_model=FeedbackResponse, status_code=201)
def save_feedback(
    session_id: UUID, request: FeedbackRequest, http_request: Request, db: Session = DB
) -> FeedbackResponse:
    session = db.get(records.ProblemSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Problem session not found.")
    if session.status not in {"completed", "failed", "awaiting_user_input"}:
        raise HTTPException(
            status_code=409,
            detail="Wait for the investigation to pause or finish before reviewing it.",
        )
    safe = FeedbackRequest.model_validate(sanitize_json_value(request.model_dump(mode="json")))
    admitted_at = WriteAdmissionPolicy(db, http_request.app.state.settings).acquire(
        "feedback", session_id=session_id
    )
    record = records.HumanFeedback(
        created_at=admitted_at,
        session_id=session_id,
        feedback_type=safe.feedback_type,
        correction=safe.correction or None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FeedbackResponse.model_validate(record)


@router.get("/{session_id}/feedback", response_model=list[FeedbackResponse])
def get_feedback(session_id: UUID, db: Session = DB) -> list[FeedbackResponse]:
    if db.get(records.ProblemSession, session_id) is None:
        raise HTTPException(status_code=404, detail="Problem session not found.")
    rows = db.scalars(
        select(records.HumanFeedback)
        .where(records.HumanFeedback.session_id == session_id)
        .order_by(records.HumanFeedback.created_at.desc(), records.HumanFeedback.id)
        .limit(100)
    )
    return [
        FeedbackResponse.model_validate(
            sanitize_json_value(FeedbackResponse.model_validate(row).model_dump(mode="json"))
        )
        for row in rows
    ]
