"""Trace-derived evidence requirements and residual acquisition needs.

These contracts are experimental Chapter 13-J artifacts. They deliberately do
not add fields to canonical ``PolyaState``: the current epistemic status is
recomputed from the active gap and append-only acquisition/evaluation trace.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, JsonValue

from app.graph.state import PolyaState, StateEvent
from app.models.contracts import ContractModel, KnowledgeGap, NonEmptyStr

EPISTEMIC_CONTROL_POLICY_VERSION = "epistemic-control-v0.1.0"


class ResidualEpistemicNeed(StrEnum):
    """What kind of observation can still reduce the blocking uncertainty."""

    INITIAL_EVIDENCE = "initial_evidence"
    CORROBORATION = "corroboration"
    CURRENT_AUTHORITY = "current_authority"
    CONFLICT_RESOLUTION = "conflict_resolution"
    DISCRIMINATING_EVIDENCE = "discriminating_evidence"
    SATISFIED = "satisfied"


class EpistemicRequirement(ContractModel):
    """Deterministically derived evidence boundary for one unresolved gap."""

    policy_version: NonEmptyStr = EPISTEMIC_CONTROL_POLICY_VERSION
    target: NonEmptyStr
    minimum_independent_sources: Annotated[int, Field(ge=1, le=5)]
    requires_current_evidence: bool
    requires_authoritative_source: bool
    success_criteria: list[NonEmptyStr]


class EpistemicStatus(ContractModel):
    """Current trace-derived progress toward an epistemic requirement."""

    requirement: EpistemicRequirement
    residual_need: ResidualEpistemicNeed
    evaluated_batches: Annotated[int, Field(ge=0)] = 0
    accepted_candidates: Annotated[int, Field(ge=0)] = 0
    independent_sources: Annotated[int, Field(ge=0)] = 0
    current_supporting_sources: Annotated[int, Field(ge=0)] = 0
    authoritative_sources: Annotated[int, Field(ge=0)] = 0
    contradiction_count: Annotated[int, Field(ge=0)] = 0
    no_progress_batches: Annotated[int, Field(ge=0)] = 0
    temporal_gate_passed: bool = False
    authority_gate_passed: bool = False
    semantic_gate_passed: bool = False
    rationale: NonEmptyStr


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    normalized = text.casefold()
    return any(token in normalized for token in tokens)


def derive_epistemic_requirement(
    state: PolyaState,
    gap: KnowledgeGap,
) -> EpistemicRequirement:
    """Derive a conservative source/freshness requirement without an LLM."""
    problem = state["structured_problem"]
    problem_constraints = " ".join(problem.constraints) if problem is not None else ""
    required_sources = " ".join(problem.required_data_sources) if problem is not None else ""
    source_hint_text = " ".join(
        part for part in (gap.suggested_source or "", required_sources) if part
    )
    gap_source_text = " ".join(
        part for part in (gap.description, gap.gap_type, gap.suggested_source or "") if part
    )
    source_text = " ".join(part for part in (gap_source_text, problem_constraints) if part)
    local_or_procedural = _contains_any(
        source_hint_text,
        (
            "artifact",
            "calculator",
            "code",
            "corpus",
            "database",
            "dataset",
            "experiment",
            "file",
            "local",
            "manual",
            "measurement",
            "repository",
            "simulation",
        ),
    )
    web_or_public = _contains_any(
        source_hint_text,
        ("web", "public", "external", "official", "research"),
    )
    explicitly_independent = _contains_any(
        source_text,
        ("independent", "corroborat", "cross-check", "cross check", "multiple sources"),
    )
    requires_current = _contains_any(
        source_text,
        ("current", "latest", "today", "recent", "as of", "right now", "dynamic"),
    )
    requires_authority = _contains_any(
        source_text,
        ("official", "authoritative", "primary source", "specification", "standard"),
    )
    return EpistemicRequirement(
        target=gap.description,
        minimum_independent_sources=(
            1 if local_or_procedural else 2 if web_or_public or explicitly_independent else 1
        ),
        requires_current_evidence=requires_current,
        requires_authoritative_source=requires_authority,
        success_criteria=list(problem.success_criteria) if problem is not None else [],
    )


def _acquisition_ids_for_target(state: PolyaState, target: str) -> set[str]:
    return {
        acquisition_id
        for event in state["events"]
        if event.event_type == "evidence_candidates_acquired"
        and event.metadata.get("target_gap") == target
        and isinstance((acquisition_id := event.metadata.get("acquisition_id")), str)
    }


def _evaluation_events(state: PolyaState, target: str) -> list[StateEvent]:
    acquisition_ids = _acquisition_ids_for_target(state, target)
    return [
        event
        for event in state["events"]
        if event.event_type == "evidence_evaluation_completed"
        and event.metadata.get("acquisition_id") in acquisition_ids
    ]


def _metadata_int(event: StateEvent, key: str) -> int:
    value = event.metadata.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _metadata_bool(event: StateEvent, key: str) -> bool:
    value = event.metadata.get(key)
    return value if isinstance(value, bool) else False


def _metadata_list_count(event: StateEvent, key: str) -> int:
    value = event.metadata.get(key)
    return len(value) if isinstance(value, list) else 0


def _metadata_list(event: StateEvent, key: str) -> list[JsonValue]:
    value = event.metadata.get(key)
    return value if isinstance(value, list) else []


def _no_progress_count(events: list[StateEvent]) -> int:
    """Count consecutive evaluated batches that did not improve source coverage."""
    best_independent_count = 0
    consecutive = 0
    for event in events:
        independent_count = _metadata_int(event, "independent_source_count")
        resolved = _metadata_bool(event, "gap_resolved")
        if resolved:
            consecutive = 0
            best_independent_count = max(best_independent_count, independent_count)
            continue
        if independent_count > best_independent_count:
            best_independent_count = independent_count
            consecutive = 0
        else:
            consecutive += 1
    return consecutive


def derive_epistemic_status(state: PolyaState, gap: KnowledgeGap) -> EpistemicStatus:
    """Explain the next information need from admitted trace evidence."""
    requirement = derive_epistemic_requirement(state, gap)
    if gap.filled:
        return EpistemicStatus(
            requirement=requirement,
            residual_need=ResidualEpistemicNeed.SATISFIED,
            temporal_gate_passed=True,
            authority_gate_passed=True,
            semantic_gate_passed=True,
            rationale="The active gap is already resolved by admitted evidence.",
        )

    evaluations = _evaluation_events(state, gap.description)
    if not evaluations:
        return EpistemicStatus(
            requirement=requirement,
            residual_need=ResidualEpistemicNeed.INITIAL_EVIDENCE,
            rationale="No evaluated evidence batch exists for the active gap.",
        )

    latest = evaluations[-1]
    accepted = _metadata_int(latest, "accepted_count")
    independent = _metadata_int(latest, "independent_source_count")
    contradiction_pairs = {
        str(pair) for event in evaluations for pair in _metadata_list(event, "contradiction_pairs")
    }
    contradictions = len(contradiction_pairs)
    current_supporting_sources = _metadata_list_count(
        latest,
        "current_supporting_source_keys",
    )
    authoritative_sources = _metadata_list_count(latest, "authoritative_source_keys")
    temporal_gate = _metadata_bool(latest, "temporal_gate_passed")
    authority_gate = _metadata_bool(latest, "authority_gate_passed")
    semantic_gate = _metadata_bool(latest, "semantic_gate_passed")

    if contradictions:
        need = ResidualEpistemicNeed.CONFLICT_RESOLUTION
        rationale = "Accepted evidence still contains an unresolved contradiction."
    elif requirement.requires_authoritative_source and not authority_gate:
        need = ResidualEpistemicNeed.CURRENT_AUTHORITY
        rationale = "The evidence set lacks a source that passed the authority gate."
    elif requirement.requires_current_evidence and not temporal_gate:
        if current_supporting_sources:
            need = ResidualEpistemicNeed.CORROBORATION
            rationale = (
                f"Only {current_supporting_sources} of "
                f"{requirement.minimum_independent_sources} required current sources "
                "have passed evaluation."
            )
        else:
            need = ResidualEpistemicNeed.CURRENT_AUTHORITY
            rationale = "The current-fact requirement lacks temporally valid evidence."
    elif independent < requirement.minimum_independent_sources:
        need = ResidualEpistemicNeed.CORROBORATION
        rationale = (
            f"Only {independent} of {requirement.minimum_independent_sources} required "
            "independent sources have passed evaluation."
        )
    elif not semantic_gate:
        need = ResidualEpistemicNeed.DISCRIMINATING_EVIDENCE
        rationale = "Available sources do not yet semantically support one unconflicted claim."
    else:
        # The evaluator owns gap resolution. If every visible gate appears to pass but
        # the gap remains open, seek discriminating evidence rather than infer closure.
        need = ResidualEpistemicNeed.DISCRIMINATING_EVIDENCE
        rationale = "The evaluator left the gap unresolved despite passing surface gates."

    return EpistemicStatus(
        requirement=requirement,
        residual_need=need,
        evaluated_batches=len(evaluations),
        accepted_candidates=accepted,
        independent_sources=independent,
        current_supporting_sources=current_supporting_sources,
        authoritative_sources=authoritative_sources,
        contradiction_count=contradictions,
        no_progress_batches=_no_progress_count(evaluations),
        temporal_gate_passed=temporal_gate,
        authority_gate_passed=authority_gate,
        semantic_gate_passed=semantic_gate,
        rationale=rationale,
    )


def epistemic_query_directive(status: EpistemicStatus) -> str:
    """Return a bounded, auditable search revision for the residual need."""
    directive = {
        ResidualEpistemicNeed.INITIAL_EVIDENCE: "primary authoritative source exact evidence",
        ResidualEpistemicNeed.CORROBORATION: (
            "independent corroborating source from a different publisher"
        ),
        ResidualEpistemicNeed.CURRENT_AUTHORITY: (
            "current official documentation latest revision date"
        ),
        ResidualEpistemicNeed.CONFLICT_RESOLUTION: (
            "resolve conflicting claims with a primary authoritative record"
        ),
        ResidualEpistemicNeed.DISCRIMINATING_EVIDENCE: (
            "exact discriminating evidence that can falsify alternatives"
        ),
        ResidualEpistemicNeed.SATISFIED: "",
    }[status.residual_need]
    if status.no_progress_batches == 1:
        directive = f"{directive} alternative source domain".strip()
    elif status.no_progress_batches >= 2:
        directive = f"{directive} direct specification dataset or changelog".strip()
    return directive
