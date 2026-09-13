"""Deterministic closure for fully attested evidence contracts."""

from __future__ import annotations

import hashlib
from typing import Annotated

from pydantic import Field, JsonValue

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CapabilityKind,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import (
    ContractModel,
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    NonEmptyStr,
    PlanTask,
    ReasoningMode,
    Reflection,
    RiskLevel,
    VerificationReport,
)

DETERMINISTIC_EVIDENCE_ATTESTATION_EVENT = "deterministic_evidence_attested"
EVIDENCE_CLOSURE_POLICY_VERSION = "evidence-closure@0.1.0"


class TrustedEvidenceAttester(ContractModel):
    """One deterministic producer version permitted to attest exact closure."""

    capability: NonEmptyStr
    version: NonEmptyStr
    allowed_source_types: set[NonEmptyStr] = Field(min_length=1)


class DeterministicEvidenceAttestation(ContractModel):
    """Trace-only binding from a trusted tool result to current success criteria."""

    policy_version: NonEmptyStr = EVIDENCE_CLOSURE_POLICY_VERSION
    producer_capability: NonEmptyStr
    producer_version: NonEmptyStr
    source_type: NonEmptyStr
    source_uri: NonEmptyStr
    evidence_claim_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    covered_success_criteria: list[NonEmptyStr] = Field(min_length=1)
    checks_run: list[NonEmptyStr] = Field(min_length=1)


def evidence_claim_sha256(claim: str) -> str:
    """Return the stable exact-claim integrity binding."""
    return hashlib.sha256(claim.encode()).hexdigest()


def deterministic_evidence_attestation_event(
    evidence: EvidenceItem,
    *,
    producer_capability: str,
    producer_version: str,
    covered_success_criteria: list[str],
    checks_run: list[str],
) -> StateEvent:
    """Create a typed trace attestation for one deterministic tool result."""
    if evidence.source_uri is None:
        raise ValueError("deterministic evidence attestation requires source provenance")
    attestation = DeterministicEvidenceAttestation(
        producer_capability=producer_capability,
        producer_version=producer_version,
        source_type=evidence.source_type,
        source_uri=evidence.source_uri,
        evidence_claim_sha256=evidence_claim_sha256(evidence.claim),
        covered_success_criteria=covered_success_criteria,
        checks_run=checks_run,
    )
    return StateEvent(
        engine_name=producer_capability,
        event_type=DETERMINISTIC_EVIDENCE_ATTESTATION_EVENT,
        reasoning_mode=ReasoningMode.VERIFY,
        summary="A deterministic capability attested exact evidence closure bindings.",
        metadata=attestation.model_dump(mode="json"),
    )


def deterministic_evidence_attestation_available(state: PolyaState) -> bool:
    """Return whether the state contains a candidate closure attestation."""
    return bool(
        len(state["evidence"]) == 1
        and any(
            event.event_type == DETERMINISTIC_EVIDENCE_ATTESTATION_EVENT
            for event in state["events"]
        )
    )


def _trusted_rule(
    attestation: DeterministicEvidenceAttestation,
    trusted_attesters: tuple[TrustedEvidenceAttester, ...],
) -> TrustedEvidenceAttester | None:
    return next(
        (
            rule
            for rule in trusted_attesters
            if rule.capability == attestation.producer_capability
            and rule.version == attestation.producer_version
            and attestation.source_type in rule.allowed_source_types
        ),
        None,
    )


def _validated_attested_evidence(
    state: PolyaState,
    trusted_attesters: tuple[TrustedEvidenceAttester, ...],
) -> tuple[EvidenceItem, DeterministicEvidenceAttestation]:
    problem = state["structured_problem"]
    if problem is None:
        raise ValueError("evidence closure requires a structured problem")
    raw_attestations = [
        event.metadata
        for event in state["events"]
        if event.event_type == DETERMINISTIC_EVIDENCE_ATTESTATION_EVENT
    ]
    if len(raw_attestations) != 1:
        raise ValueError("evidence closure requires exactly one attestation")
    attestation = DeterministicEvidenceAttestation.model_validate(raw_attestations[0])
    if _trusted_rule(attestation, trusted_attesters) is None:
        raise ValueError("evidence attester capability, version, or source type is not trusted")
    if attestation.covered_success_criteria != list(problem.success_criteria):
        raise ValueError("evidence attestation does not cover every current success criterion")
    if len(attestation.checks_run) < len(problem.success_criteria):
        raise ValueError("evidence attestation has insufficient independent checks")
    if len(state["evidence"]) != 1:
        raise ValueError("evidence closure requires exactly one unambiguous evidence claim")
    evidence = state["evidence"][0]
    if evidence.source_type != attestation.source_type:
        raise ValueError("attested source type does not match admitted evidence")
    if evidence.source_uri != attestation.source_uri:
        raise ValueError("attested provenance does not match admitted evidence")
    if evidence.raw_excerpt != evidence.claim:
        raise ValueError("deterministic closure requires exact claim and excerpt identity")
    if evidence.reliability_score != 1.0 or evidence.relevance_score != 1.0:
        raise ValueError("deterministic closure requires maximum admitted evidence quality")
    if evidence_claim_sha256(evidence.claim) != attestation.evidence_claim_sha256:
        raise ValueError("attested claim integrity check failed")
    return evidence, attestation


def attested_evidence_procedure_capability(
    trusted_attesters: tuple[TrustedEvidenceAttester, ...] = (),
) -> FunctionCapability:
    """Close one fully attested deterministic claim without a semantic call."""
    definition = CapabilityDefinition(
        name="attested_evidence_procedure",
        version=EVIDENCE_CLOSURE_POLICY_VERSION,
        supported_actions={CognitiveActionType.HYPOTHESIZE, CognitiveActionType.VERIFY},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.01,
        kind=CapabilityKind.DETERMINISTIC,
    )
    trusted = tuple(trusted_attesters)

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        evidence, attestation = _validated_attested_evidence(state, trusted)
        task_id = f"verify-attested-evidence-{attestation.evidence_claim_sha256[:12]}"
        payload: JsonValue = {
            "procedure": "deterministic",
            "policy_version": EVIDENCE_CLOSURE_POLICY_VERSION,
            "model_calls": 0,
            "attester_capability": attestation.producer_capability,
            "attester_version": attestation.producer_version,
        }
        if action.action_type is CognitiveActionType.HYPOTHESIZE:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.SUCCEEDED,
                summary="Constructed a candidate from fully attested deterministic evidence.",
                payload=payload,
                proposed_update=CognitiveStateUpdate(
                    hypotheses_to_add=[
                        Hypothesis(
                            statement=evidence.claim,
                            mechanism=(
                                "Reuse the exact output of an allowlisted deterministic "
                                "capability after integrity and coverage checks."
                            ),
                            origin=HypothesisOrigin.DIRECT_REASONING,
                            expected_signals=[evidence.claim],
                            evidence_for=[attestation.source_uri],
                            verification_checks=list(attestation.checks_run),
                            falsification_criteria=[
                                "Any producer, version, provenance, hash, quality, ambiguity, "
                                "or success-criterion binding fails."
                            ],
                        )
                    ],
                    plan_tasks_to_add=[
                        PlanTask(
                            id=task_id,
                            action="Recompute every deterministic evidence attestation binding.",
                            tool_name=definition.name,
                            expected_output="All trust, integrity, provenance, and coverage checks pass.",
                        )
                    ],
                    execution_outputs_to_add=[
                        ExecutionOutput(
                            task_id=task_id,
                            summary="Recomputed the attested claim hash and source bindings.",
                            output={
                                "claim_sha256": attestation.evidence_claim_sha256,
                                "source_uri": attestation.source_uri,
                                "criteria_covered": len(attestation.covered_success_criteria),
                            },
                        )
                    ],
                    trace_events_to_add=[
                        StateEvent(
                            engine_name=definition.name,
                            event_type="deterministic_evidence_closure_started",
                            reasoning_mode=ReasoningMode.EXECUTE,
                            summary="Selected deterministic closure before semantic cognition.",
                            metadata={
                                "policy_version": EVIDENCE_CLOSURE_POLICY_VERSION,
                                "model_calls": 0,
                                "claim_sha256": attestation.evidence_claim_sha256,
                            },
                        )
                    ],
                ),
            )
        if action.action_type is not CognitiveActionType.VERIFY:
            raise ValueError("attested evidence procedure received an unsupported action")

        matching_outputs = [
            item
            for item in state["execution_outputs"]
            if item.task_id == task_id
            and isinstance(item.output, dict)
            and item.output.get("claim_sha256") == attestation.evidence_claim_sha256
            and item.output.get("source_uri") == attestation.source_uri
        ]
        if len(matching_outputs) != 1:
            raise ValueError("attested evidence replay output is missing or changed")
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary="Deterministic evidence closure passed every current binding.",
            payload=payload,
            proposed_update=CognitiveStateUpdate(
                verification=VerificationReport(
                    passed=True,
                    checks_run=list(attestation.checks_run),
                    confidence_delta=0.25,
                    recommended_route="finalize",
                ),
                final_answer=evidence.claim,
                reflection=Reflection(
                    outcome_summary="Closed the task from fully attested deterministic evidence.",
                    what_worked=[
                        "A trusted tool result covered every criterion and passed replayed bindings."
                    ],
                    reusable_lessons=[
                        "Prefer exact attested evidence closure before semantic restatement."
                    ],
                    strategy_notes=[EVIDENCE_CLOSURE_POLICY_VERSION],
                ),
                trace_events_to_add=[
                    StateEvent(
                        engine_name=definition.name,
                        event_type="deterministic_evidence_closure_verified",
                        reasoning_mode=ReasoningMode.VERIFY,
                        summary="Finalized only after replaying every evidence attestation binding.",
                        metadata={
                            "policy_version": EVIDENCE_CLOSURE_POLICY_VERSION,
                            "model_calls": 0,
                            "claim_sha256": attestation.evidence_claim_sha256,
                            "criteria_covered": len(attestation.covered_success_criteria),
                        },
                    )
                ],
            ),
        )

    return FunctionCapability(definition, execute)
