"""Experimental reporting metadata for nonblocking residual uncertainty.

This does not change canonical gaps, completion criteria, confidence, or memory.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Annotated, Any

from pydantic import Field, StringConstraints, ValidationError

from app.graph.state import StateEvent
from app.models.contracts import ContractModel, ReasoningMode
from app.tracing.sanitization import sanitize_text

REPORT_METADATA_EVENT = "conclusion_report_metadata_recorded"
REPORT_METADATA_VERSION = "conclusion_report_metadata@0.1.0"
SCOPE_LIMITATION_PREFIX = "Unresolved, nonblocking for this deliverable: "
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


def scope_limitations(constraints: Iterable[object]) -> list[str]:
    """Display current scoped-out questions without promoting them to facts."""
    return [
        item.removeprefix(SCOPE_LIMITATION_PREFIX)
        for item in constraints
        if isinstance(item, str) and item.startswith(SCOPE_LIMITATION_PREFIX)
    ]


class ConclusionReportMetadata(ContractModel):
    """Optional presentation metadata produced by the final conclusion checker."""

    open_questions: list[Question] = Field(default_factory=list, max_length=8)


def _answer_hash(answer: str) -> str:
    return hashlib.sha256(sanitize_text(answer).strip().encode()).hexdigest()


def report_metadata_event(
    *, answer: str, metadata: ConclusionReportMetadata, engine_name: str
) -> StateEvent:
    questions = list(dict.fromkeys(metadata.open_questions))
    return StateEvent(
        engine_name=engine_name,
        event_type=REPORT_METADATA_EVENT,
        reasoning_mode=ReasoningMode.VERIFY,
        summary=f"Recorded {len(questions)} residual question(s) for the completed deliverable.",
        metadata={
            "version": REPORT_METADATA_VERSION,
            "answer_sha256": _answer_hash(answer),
            "open_questions": list(questions),
            "scope": "nonblocking uncertainty; not verified facts or execution evidence",
        },
    )


def report_questions(metadata: Mapping[str, Any] | None, answer: str | None) -> list[str]:
    """Read a known bounded event only when it belongs to the displayed answer."""
    if (
        not metadata
        or not answer
        or metadata.get("version") != REPORT_METADATA_VERSION
        or metadata.get("answer_sha256") != _answer_hash(answer)
    ):
        return []
    try:
        parsed = ConclusionReportMetadata.model_validate(
            {"open_questions": metadata.get("open_questions")}
        )
    except ValidationError:
        return []
    return list(dict.fromkeys(parsed.open_questions))
