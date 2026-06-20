"""Chapter 6 LangGraph state object for the PolyaBrain loop."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, TypeAlias, TypedDict
from uuid import uuid4

from pydantic import Field, JsonValue

from app.models.contracts import (
    ContractModel,
    EvidenceItem,
    Hypothesis,
    KnowledgeGap,
    NonEmptyStr,
    PlanTask,
    ReasoningMode,
    Reflection,
    StructuredProblem,
    VerificationReport,
)

DEFAULT_MAX_ITERATIONS = 3


class StateEvent(ContractModel):
    """Append-only event message carried through graph state."""

    engine_name: NonEmptyStr
    event_type: NonEmptyStr
    reasoning_mode: ReasoningMode
    summary: NonEmptyStr
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class ExecutionOutput(ContractModel):
    """Execution result attached to a planned task before persistence exists."""

    task_id: NonEmptyStr
    summary: NonEmptyStr
    output: JsonValue = None
    artifact_ids: list[NonEmptyStr] = Field(default_factory=list)
    error: NonEmptyStr | None = None


StateEventInput: TypeAlias = StateEvent | Mapping[str, JsonValue]
StateEventUpdate: TypeAlias = StateEventInput | list[StateEventInput] | None


def _validate_state_event(event: StateEventInput) -> StateEvent:
    """Coerce graph event updates into the strict state event contract."""
    if isinstance(event, StateEvent):
        return event
    return StateEvent.model_validate(event)


def append_state_events(
    existing: list[StateEvent] | None,
    new: StateEventUpdate,
) -> list[StateEvent]:
    """Return a new event list with LangGraph updates appended in order."""
    events = list(existing or [])
    if new is None:
        return events
    if isinstance(new, StateEvent | Mapping):
        return [*events, _validate_state_event(new)]
    return [*events, *[_validate_state_event(event) for event in new]]


class PolyaState(TypedDict):
    """Shared state carried by the Chapter 6+ LangGraph loop."""

    session_id: str
    raw_input: str
    structured_problem: StructuredProblem | None
    gaps: list[KnowledgeGap]
    evidence: list[EvidenceItem]
    hypotheses: list[Hypothesis]
    plan: list[PlanTask]
    execution_outputs: list[ExecutionOutput]
    verification: VerificationReport | None
    reflection: Reflection | None
    iteration_count: int
    max_iterations: int
    final_answer: str | None
    events: Annotated[list[StateEvent], append_state_events]


def create_initial_state(
    raw_input: str,
    *,
    session_id: str | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> PolyaState:
    """Create a complete initial Polya state from raw user input."""
    normalized_input = raw_input.strip()
    if not normalized_input:
        raise ValueError("raw_input must not be blank")
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")

    normalized_session_id = session_id.strip() if session_id is not None else str(uuid4())
    if not normalized_session_id:
        raise ValueError("session_id must not be blank")

    return {
        "session_id": normalized_session_id,
        "raw_input": normalized_input,
        "structured_problem": None,
        "gaps": [],
        "evidence": [],
        "hypotheses": [],
        "plan": [],
        "execution_outputs": [],
        "verification": None,
        "reflection": None,
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "final_answer": None,
        "events": [],
    }
