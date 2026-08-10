"""Canonical persistence for accepted cognitive-run artifacts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import EvidenceItem as EvidenceItemRecord
from app.db.models import Hypothesis as HypothesisRecord
from app.db.models import KnowledgeGap as KnowledgeGapRecord
from app.db.models import PlanTask as PlanTaskRecord
from app.db.models import VerificationReport as VerificationReportRecord
from app.graph.state import PolyaState
from app.models.contracts import EvidenceItem


class SQLAlchemyCognitiveStateRepository:
    """Replace one session's accepted artifacts with its latest canonical state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_evidence(self, session_id: UUID) -> list[EvidenceItem]:
        """Rehydrate canonical evidence so a resumed run cannot forget it."""
        records = list(
            self._session.scalars(
                select(EvidenceItemRecord).where(EvidenceItemRecord.session_id == session_id)
            )
        )
        return [
            EvidenceItem(
                source_type=record.source_type,
                source_uri=record.source_uri,
                claim=record.claim,
                raw_excerpt=record.raw_excerpt,
                reliability_score=record.reliability_score,
                relevance_score=record.relevance_score,
                supports_hypothesis_ids=[str(item) for item in record.supports_hypothesis_ids],
                contradicts_hypothesis_ids=[
                    str(item) for item in record.contradicts_hypothesis_ids
                ],
            )
            for record in records
        ]

    def persist_state(self, *, session_id: UUID, state: PolyaState) -> None:
        """Persist validated state inside the caller-owned transaction."""
        for record_type in (
            KnowledgeGapRecord,
            EvidenceItemRecord,
            HypothesisRecord,
            PlanTaskRecord,
            VerificationReportRecord,
        ):
            self._session.execute(delete(record_type).where(record_type.session_id == session_id))

        self._session.add_all(
            [
                KnowledgeGapRecord(
                    session_id=session_id,
                    description=item.description,
                    gap_type=item.gap_type,
                    priority=item.priority.value,
                    why_needed=item.why_needed,
                    suggested_source=item.suggested_source,
                    filled=item.filled,
                    evidence_ids=list(item.evidence_ids),
                )
                for item in state["gaps"]
            ]
        )
        self._session.add_all(
            [
                EvidenceItemRecord(
                    session_id=session_id,
                    source_type=item.source_type,
                    source_uri=item.source_uri,
                    claim=item.claim,
                    raw_excerpt=item.raw_excerpt,
                    reliability_score=item.reliability_score,
                    relevance_score=item.relevance_score,
                    supports_hypothesis_ids=list(item.supports_hypothesis_ids),
                    contradicts_hypothesis_ids=list(item.contradicts_hypothesis_ids),
                )
                for item in state["evidence"]
            ]
        )
        self._session.add_all(
            [
                HypothesisRecord(
                    session_id=session_id,
                    statement=item.statement,
                    mechanism=item.mechanism,
                    origin=item.origin.value,
                    analogical_source_ids=list(item.analogical_source_ids),
                    expected_signals=list(item.expected_signals),
                    evidence_for=list(item.evidence_for),
                    evidence_against=list(item.evidence_against),
                    verification_checks=list(item.verification_checks),
                    falsification_criteria=list(item.falsification_criteria),
                    confidence=item.confidence,
                    selection_rationale=item.selection_rationale,
                    status=item.status.value,
                )
                for item in state["hypotheses"]
            ]
        )
        self._session.add_all(
            [
                PlanTaskRecord(
                    session_id=session_id,
                    action=item.action,
                    tool_name=item.tool_name,
                    params={**item.params, "_polyabrain_task_id": item.id},
                    depends_on=list(item.depends_on),
                    expected_output=item.expected_output,
                    risk_level=item.risk_level.value,
                )
                for item in state["plan"]
            ]
        )
        verification = state["verification"]
        if verification is not None:
            self._session.add(
                VerificationReportRecord(
                    session_id=session_id,
                    passed=verification.passed,
                    checks_run=list(verification.checks_run),
                    failed_checks=list(verification.failed_checks),
                    contradictions=list(verification.contradictions),
                    confidence_delta=verification.confidence_delta,
                    recommended_route=verification.recommended_route,
                )
            )
