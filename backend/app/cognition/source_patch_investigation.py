"""One-call source-patch proposal for governed technical investigations."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from pydantic import Field, JsonValue, model_validator

from app.cognition.capabilities import AuditedCapabilityError, FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CapabilityKind,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.cognition.model_gateway import CognitiveModelGateway
from app.cognition.repair_recovery import recalled_failure_task, supersession_event
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import (
    ContractModel,
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    NonEmptyStr,
    PlanTask,
    ReasoningMode,
    RiskLevel,
)

SOURCE_PATCH_INVESTIGATOR_VERSION = "source_patch_investigator@0.3.0"
SOURCE_PATCH_CONTEXT_PROJECTION_VERSION = "source_patch_context@0.3.0"


class SourcePatchProposal(ContractModel):
    """One bounded exact edit plus the evidence-backed diagnosis it tests."""

    diagnosis: NonEmptyStr
    implicated_source_uri: NonEmptyStr
    old_text: NonEmptyStr = Field(max_length=800)
    new_text: NonEmptyStr = Field(max_length=800)
    correction_rationale: NonEmptyStr
    regression_check_uri: NonEmptyStr
    regression_check_summary: NonEmptyStr
    remaining_uncertainty: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def edit_must_change_text(self) -> SourcePatchProposal:
        if self.old_text == self.new_text:
            raise ValueError("source patch proposal must change the selected text")
        if "\x00" in self.old_text or "\x00" in self.new_text:
            raise ValueError("source patch proposal cannot contain null bytes")
        return self


def _base_uri(uri: str) -> str:
    return uri.split("#", maxsplit=1)[0]


def _artifact_name(reference: str) -> str:
    parsed = urlparse(reference)
    path = parsed.path if parsed.scheme else reference
    return Path(unquote(path)).name


def _resolve_admitted_uri(
    reference: str,
    evidence_by_uri: dict[str, EvidenceItem],
) -> str | None:
    """Resolve exact canonical identity or one unique exact admitted filename."""
    base = _base_uri(reference)
    if base in evidence_by_uri:
        return base
    name = _artifact_name(base)
    matches = [uri for uri in evidence_by_uri if _artifact_name(uri) == name]
    return matches[0] if name and len(matches) == 1 else None


def _executable_excerpt(evidence: EvidenceItem) -> str:
    """Remove inspector display line numbers while retaining source whitespace."""
    return "\n".join(
        re.sub(r"^\s*\d+:\s?", "", line) for line in (evidence.raw_excerpt or "").splitlines()
    )


def _failure_observation(raw_input: str) -> str:
    marker = "The executable buggy reproduction failed with this observation:\n"
    end_marker = "\nSuccess requires:"
    if marker not in raw_input:
        return "The supplied check has not been executed yet; do not assume a failure mechanism."
    observation = raw_input.partition(marker)[2].partition(end_marker)[0].strip()
    return (
        observation[:4_000]
        or "The supplied check has not been executed yet; do not assume a failure mechanism."
    )


def _source_patch_state_projection(
    state: PolyaState,
    evidence_by_uri: dict[str, EvidenceItem],
) -> dict[str, JsonValue]:
    problem = state["structured_problem"]
    if problem is None:
        raise ValueError("source-patch context projection requires a represented problem")
    admitted_evidence: list[JsonValue] = [
        {
            "source_uri": uri,
            "source_type": item.source_type,
            "excerpt": _executable_excerpt(item),
        }
        for uri, item in evidence_by_uri.items()
    ]
    projection: dict[str, JsonValue] = {
        "projection_version": SOURCE_PATCH_CONTEXT_PROJECTION_VERSION,
        "problem": problem.core_question,
        "observed_failure": _failure_observation(state["raw_input"]),
        "constraints": list(problem.constraints),
        "success_criteria": list(problem.success_criteria),
        "admitted_evidence": admitted_evidence,
    }
    rejected = recalled_failure_task(state)
    if rejected is not None and state["verification"] is not None:
        projection["rejected_edit"] = rejected.model_dump(mode="json")
        projection["failed_checks"] = list(state["verification"].failed_checks)
    return projection


def source_patch_investigator_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
    max_output_tokens: int = 2200,
    timeout_seconds: float = 90.0,
) -> FunctionCapability:
    """Propose one exact edit; execution and verification remain deterministic."""
    definition = CapabilityDefinition(
        name="source_patch_investigator",
        version=gateway.capability_version(SOURCE_PATCH_INVESTIGATOR_VERSION),
        supported_actions={CognitiveActionType.HYPOTHESIZE, CognitiveActionType.REPLAN},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=approved_for_sensitive_data,
        estimated_cost=0.28,
        kind=CapabilityKind.MODEL,
        max_model_calls=gateway.max_provider_attempts_per_capability,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        if (
            action.action_type is CognitiveActionType.REPLAN
            and recalled_failure_task(state) is None
        ):
            raise ValueError("Source-patch recovery requires a measured rejected memory edit")
        problem = state["structured_problem"]
        if problem is None or problem.problem_type not in {
            "field_derived_technical_investigation",
            "source_patch_investigation",
        }:
            raise ValueError("source patch investigator requires its declared task shape")
        evidence_by_uri = {
            _base_uri(item.source_uri): item
            for item in state["evidence"]
            if item.source_uri is not None and item.source_uri.startswith("file://")
        }
        if len(evidence_by_uri) < 2:
            raise ValueError("source patch investigator requires admitted source and check files")
        result = gateway.complete(
            capability=definition.name,
            instructions=(
                "Diagnose this source-visible software defect and propose exactly one bounded "
                "text replacement that can be tested against an admitted regression check. "
                "implicated_source_uri and regression_check_uri must exactly match base file "
                "URIs in canonical evidence. old_text must occur exactly once in the implicated "
                "source excerpt; new_text must be its smallest semantic correction. Do not "
                "include line-number prefixes in old_text or new_text. The check must be an "
                "independent admitted Python artifact. State uncertainty honestly. Do not claim "
                "the edit or check was executed; a governed sandbox owns that step. "
                "If rejected_edit is present, its candidate failed the current supplied check. "
                "Use that feedback to propose a different edit against the ORIGINAL source; "
                "do not repeat the rejected edit or ask for execution evidence the sandbox can obtain."
            ),
            output_type=SourcePatchProposal,
            state=state,
            max_output_tokens=max_output_tokens,
            total_timeout_seconds=timeout_seconds,
            context={"admitted_base_file_uris": list(evidence_by_uri)},
            state_projection=_source_patch_state_projection(state, evidence_by_uri),
        )
        proposal = result.output
        failure_payload: dict[str, JsonValue] = {
            "provider": result.provider,
            "model": result.model,
            "usage": result.usage.model_dump(mode="json"),
            "model_calls": result.model_calls,
            "route_attempts": [item.model_dump(mode="json") for item in result.route_attempts],
        }
        observation = proposal_observation(
            proposal, action, state, definition=definition, failure_payload=failure_payload
        )
        if action.action_type is CognitiveActionType.REPLAN:
            try:
                event = supersession_event(state, observation.proposed_update.plan_tasks_to_add[0])
            except ValueError as exc:
                raise AuditedCapabilityError(
                    str(exc), failure_kind="source_patch_recovery_invalid", payload=failure_payload
                ) from exc
            observation.proposed_update.trace_events_to_add.append(event)
        return observation

    return FunctionCapability(definition, execute)


def proposal_observation(
    proposal: SourcePatchProposal,
    action: CognitiveActionCandidate,
    state: PolyaState,
    *,
    definition: CapabilityDefinition,
    failure_payload: dict[str, JsonValue],
    origin: HypothesisOrigin = HypothesisOrigin.DIRECT_REASONING,
) -> CognitiveObservation:
    """Bind model or recalled candidate to current evidence; never reuse a verdict."""
    problem = state["structured_problem"]
    if problem is None:
        raise ValueError("source patch requires a represented problem")
    evidence_by_uri = {
        _base_uri(item.source_uri): item
        for item in state["evidence"]
        if item.source_uri is not None and item.source_uri.startswith("file://")
    }
    source_uri = _resolve_admitted_uri(proposal.implicated_source_uri, evidence_by_uri)
    check_uri = _resolve_admitted_uri(proposal.regression_check_uri, evidence_by_uri)
    if source_uri is None or check_uri is None:
        raise AuditedCapabilityError(
            "Source-patch proposal referenced an artifact outside the admitted set.",
            failure_kind="source_patch_artifact_unadmitted",
            payload=failure_payload,
        )
    source_evidence = evidence_by_uri.get(source_uri)
    check_evidence = evidence_by_uri.get(check_uri)
    if source_evidence is None or check_evidence is None or source_uri == check_uri:
        raise AuditedCapabilityError(
            "Source-patch proposal did not bind distinct admitted source and check files.",
            failure_kind="source_patch_artifact_binding_failed",
            payload=failure_payload,
        )
    old_text_occurrences = _executable_excerpt(source_evidence).count(proposal.old_text)
    if old_text_occurrences != 1:
        failure_payload["old_text_occurrences_in_excerpt"] = old_text_occurrences
        raise AuditedCapabilityError(
            "Source-patch old text was absent or ambiguous in admitted source evidence.",
            failure_kind="source_patch_edit_not_unique",
            payload=failure_payload,
        )
    report = (
        f"Proposed diagnosis: {proposal.diagnosis}\n"
        f"Implicated source: {source_uri}\n"
        f"Correction: replace {proposal.old_text!r} with {proposal.new_text!r}. "
        f"{proposal.correction_rationale}\n"
        f"Regression check: {proposal.regression_check_summary} ({check_uri}).\n"
        "Scope: the supplied check tests this candidate edit. It does not prove the "
        "diagnosis, cover all regressions, or independently attest hostile code."
    )
    if proposal.remaining_uncertainty:
        report += "\nRemaining uncertainty: " + "; ".join(proposal.remaining_uncertainty)
    task_id = (
        "verify-source-patch-recovery"
        if action.action_type is CognitiveActionType.REPLAN
        else "verify-source-patch"
    )
    verification_paths = (
        "diagnosis_grounded",
        "source_admitted",
        "correction_verified",
        "check_admitted_and_passed",
    )
    if len(problem.success_criteria) != len(verification_paths):
        raise AuditedCapabilityError(
            "Source-patch verifier requires the declared four-criterion shape.",
            failure_kind="source_patch_verification_shape_invalid",
            payload=failure_payload,
        )
    verification: list[dict[str, JsonValue]] = [
        {
            "criterion_index": index,
            "operation": "equals",
            "actual_path": path,
            "expected": True,
        }
        for index, path in enumerate(verification_paths)
    ]
    return CognitiveObservation(
        action_id=action.id,
        capability=definition.name,
        capability_version=definition.version,
        status=ObservationStatus.SUCCEEDED,
        summary="Proposed one evidence-bound source edit for isolated verification.",
        payload=failure_payload,
        proposed_update=CognitiveStateUpdate(
            hypotheses_to_add=[
                Hypothesis(
                    statement=report,
                    mechanism=proposal.diagnosis,
                    origin=origin,
                    expected_signals=[proposal.regression_check_summary],
                    evidence_for=[source_uri, check_uri],
                    verification_checks=[proposal.regression_check_summary],
                    falsification_criteria=[
                        "The exact edit is ambiguous or absent from the admitted source.",
                        "The independently supplied regression check fails in isolation.",
                    ],
                    confidence=0.75,
                    selection_rationale=(
                        "Selected for present-case execution; confidence cannot increase "
                        "until the governed check passes."
                    ),
                )
            ],
            plan_tasks_to_add=[
                PlanTask(
                    id=task_id,
                    action="Apply the exact edit in isolation and run the admitted check.",
                    tool_name="source_patch_sandbox",
                    params={
                        "source_uri": source_uri,
                        "check_uri": check_uri,
                        "old_text": proposal.old_text,
                        "new_text": proposal.new_text,
                        "diagnosis": proposal.diagnosis,
                        "verification": verification,
                    },
                    expected_output=(
                        "A structured patch_verified result from the networkless sandbox."
                    ),
                    risk_level=RiskLevel.MEDIUM,
                )
            ],
            trace_events_to_add=[
                StateEvent(
                    engine_name=definition.name,
                    event_type="source_patch_proposed",
                    reasoning_mode=ReasoningMode.EXPLORE,
                    summary="Bound one proposed edit to admitted source and check artifacts.",
                    metadata={
                        "source_uri": source_uri,
                        "check_uri": check_uri,
                        "old_text_occurrences_in_excerpt": old_text_occurrences,
                        "model_calls": failure_payload.get("model_calls", 0),
                        "context_projection": SOURCE_PATCH_CONTEXT_PROJECTION_VERSION,
                    },
                )
            ],
        ),
    )
