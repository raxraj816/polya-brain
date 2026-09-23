"""Guarded trace-to-procedure compilation for Chapter 13-E.

Compiled procedures remain experimental artifacts.  They preserve provenance,
capability versions, verifier programs, and regression evidence; they never
turn a successful trace directly into trusted present-case truth.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated

from pydantic import Field, model_validator

from app.cognition.capabilities import CapabilityRegistry
from app.cognition.contracts import (
    CognitiveActionType,
    CognitiveRunStatus,
    ObservationStatus,
)
from app.cognition.task_model import CognitiveResourceUsage, accumulated_usage
from app.cognition.verification_factory import (
    VERIFIER_SUITE_EVENT,
    VerifierKind,
    VerifierSuite,
)
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import ContractModel, NonEmptyStr, ReasoningMode, RiskLevel

if TYPE_CHECKING:
    from app.cognition.kernel import CognitiveRunResult

PROCEDURE_COMPILED_EVENT = "compiled_procedure_proposed"
PROCEDURE_REPLAYED_EVENT = "compiled_procedure_replay_tested"
PROCEDURE_COMPILER_VERSION = "procedure-compiler@0.1.0"


class ProcedureLifecycle(StrEnum):
    """Trust lifecycle for compiled behavior."""

    OBSERVED = "observed"
    PROPOSED = "proposed"
    REPLAY_TESTED = "replay_tested"
    VERIFIED = "verified"
    DEPLOYED = "deployed"
    MONITORED = "monitored"
    RETIRED = "retired"


class ProcedureApplicabilityStatus(StrEnum):
    """Three-valued applicability outcome."""

    APPLICABLE = "applicable"
    INAPPLICABLE = "inapplicable"
    INCONCLUSIVE = "inconclusive"


class ProcedureStep(ContractModel):
    """One generalized, capability-version-pinned cognitive action."""

    order: Annotated[int, Field(ge=0)]
    action_type: CognitiveActionType
    capability: NonEmptyStr
    capability_version: NonEmptyStr
    target_role: NonEmptyStr
    purpose: NonEmptyStr
    expected_observation: NonEmptyStr
    expected_postconditions: list[NonEmptyStr] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW


class ProcedureRegressionCase(ContractModel):
    """One replay case and the structural boundary it exercised."""

    case_id: NonEmptyStr
    problem_type: NonEmptyStr
    domain: NonEmptyStr | None = None
    constraint_fingerprint: NonEmptyStr
    verifier_suite_version: NonEmptyStr
    verification_passed: bool


class ProcedureReplayResult(ContractModel):
    """Externally obtained replay outcome used for lifecycle promotion."""

    case: ProcedureRegressionCase
    procedure_completed: bool
    verification_passed: bool
    capability_versions_match: bool
    failure_reason: NonEmptyStr | None = None

    @model_validator(mode="after")
    def failed_replay_must_explain_failure(self) -> ProcedureReplayResult:
        passed = (
            self.procedure_completed and self.verification_passed and self.capability_versions_match
        )
        if not passed and self.failure_reason is None:
            raise ValueError("failed procedure replay requires a failure reason")
        return self


class CompiledProcedure(ContractModel):
    """A versioned procedure proposal with its complete trust boundary."""

    id: NonEmptyStr
    compiler_version: NonEmptyStr = PROCEDURE_COMPILER_VERSION
    version: Annotated[int, Field(ge=1)] = 1
    name: NonEmptyStr
    purpose: NonEmptyStr
    task_family: NonEmptyStr
    applicable_gap_types: list[NonEmptyStr] = Field(default_factory=list)
    required_evidence_source_types: list[NonEmptyStr] = Field(default_factory=list)
    required_capabilities: dict[str, NonEmptyStr] = Field(default_factory=dict)
    safety_constraints: list[NonEmptyStr] = Field(default_factory=list)
    steps: list[ProcedureStep] = Field(min_length=1)
    verifier_suite: VerifierSuite
    source_session_ids: list[NonEmptyStr] = Field(min_length=1)
    resource_profile: CognitiveResourceUsage
    known_failure_modes: list[NonEmptyStr] = Field(default_factory=list)
    regression_cases: list[ProcedureRegressionCase] = Field(default_factory=list)
    lifecycle: ProcedureLifecycle = ProcedureLifecycle.PROPOSED
    mechanical_proof: NonEmptyStr | None = None
    invalidation_conditions: list[NonEmptyStr] = Field(default_factory=list)
    integrity_hash: NonEmptyStr

    @model_validator(mode="after")
    def trusted_lifecycle_requires_regression_evidence(self) -> CompiledProcedure:
        orders = [step.order for step in self.steps]
        if len(set(orders)) != len(orders) or orders != sorted(orders):
            raise ValueError("procedure steps require unique ascending order values")
        if self.lifecycle in {
            ProcedureLifecycle.REPLAY_TESTED,
            ProcedureLifecycle.VERIFIED,
            ProcedureLifecycle.DEPLOYED,
            ProcedureLifecycle.MONITORED,
        }:
            passing_cases = {
                item.case_id for item in self.regression_cases if item.verification_passed
            }
            if self.mechanical_proof is None and len(passing_cases) < 2:
                raise ValueError("trusted procedure requires two distinct passing replay cases")
        if self.mechanical_proof is not None and (
            self.task_family != "explicit_artifact_lookup"
            or any(
                item.kind is not VerifierKind.EXACT_EVIDENCE
                for item in self.verifier_suite.specifications
            )
        ):
            raise ValueError("mechanical proof is restricted to exact-artifact procedures")
        return self


class ProcedureApplicability(ContractModel):
    """Inspectable decision about present-case transfer."""

    procedure_id: NonEmptyStr
    status: ProcedureApplicabilityStatus
    reasons: list[NonEmptyStr] = Field(min_length=1)


def _constraint_fingerprint(constraints: list[str]) -> str:
    encoded = json.dumps(sorted(constraints), separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _integrity_payload(procedure: CompiledProcedure) -> dict[str, object]:
    payload = procedure.model_dump(mode="json", exclude={"integrity_hash"})
    return {str(key): value for key, value in payload.items()}


def procedure_integrity_hash(procedure: CompiledProcedure) -> str:
    """Hash every trust-relevant field, including lifecycle and replay evidence."""
    encoded = json.dumps(
        _integrity_payload(procedure),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _with_integrity(procedure: CompiledProcedure) -> CompiledProcedure:
    provisional = procedure.model_copy(update={"integrity_hash": "pending"})
    return provisional.model_copy(update={"integrity_hash": procedure_integrity_hash(provisional)})


def procedure_integrity_valid(procedure: CompiledProcedure) -> bool:
    """Detect mutation or poisoned memory before applicability is considered."""
    return procedure.integrity_hash == procedure_integrity_hash(procedure)


def _target_role(state: PolyaState, target: str) -> str:
    problem = state["structured_problem"]
    if problem is not None and target == problem.core_question:
        return "task_goal"
    for gap in state["gaps"]:
        if target == gap.description:
            return f"gap:{gap.gap_type}"
    if any(task.id == target for task in state["plan"]):
        return "plan_task"
    if target in {"raw problem input", state["raw_input"]}:
        return "task_input"
    return "bounded_obstacle"


def _postconditions(action_type: CognitiveActionType) -> list[str]:
    mapping = {
        CognitiveActionType.INTERPRET: ["structured_problem_exists"],
        CognitiveActionType.DISCOVER_CONSTRAINTS: ["constraints_validated"],
        CognitiveActionType.DETECT_GAPS: ["blocking_gaps_exposed"],
        CognitiveActionType.SEARCH: ["candidate_evidence_acquired"],
        CognitiveActionType.INSPECT: ["candidate_evidence_acquired"],
        CognitiveActionType.EVALUATE_EVIDENCE: ["evidence_admission_decided"],
        CognitiveActionType.HYPOTHESIZE: ["testable_candidate_exists"],
        CognitiveActionType.PLAN: ["observable_plan_exists"],
        CognitiveActionType.EXECUTE: ["execution_output_exists"],
        CognitiveActionType.VERIFY: ["every_success_criterion_checked"],
        CognitiveActionType.REFLECT: ["verified_learning_recorded"],
    }
    return mapping.get(action_type, ["declared_observation_recorded"])


def _safety_constraints(constraints: list[str]) -> list[str]:
    tokens = (
        "privacy",
        "private",
        "confidential",
        "sensitive",
        "pii",
        "read-only",
        "must not",
        "do not",
        "only",
        "approval",
    )
    return [item for item in constraints if any(token in item.casefold() for token in tokens)]


def _suite_from_trace(state: PolyaState) -> VerifierSuite | None:
    for event in reversed(state["events"]):
        if event.event_type != VERIFIER_SUITE_EVENT:
            continue
        try:
            return VerifierSuite.model_validate(event.metadata)
        except ValueError:
            return None
    return None


class ProcedureCompiler:
    """Compile a completed trace without granting it reuse authority."""

    version = PROCEDURE_COMPILER_VERSION

    def compile(
        self,
        result: CognitiveRunResult,
        *,
        mechanically_proven: bool = False,
    ) -> CompiledProcedure:
        state = result.state
        problem = state["structured_problem"]
        verification = state["verification"]
        if (
            result.status is not CognitiveRunStatus.COMPLETED
            or problem is None
            or verification is None
            or not verification.passed
            or state["reflection"] is None
            or not state["final_answer"]
        ):
            raise ValueError("procedure compilation requires a completed verified reflected run")
        suite = _suite_from_trace(state)
        if suite is None or not all(item.executable for item in suite.specifications):
            raise ValueError("procedure compilation requires an executable traced verifier suite")
        if mechanically_proven and (
            problem.problem_type != "explicit_artifact_lookup"
            or any(item.kind is not VerifierKind.EXACT_EVIDENCE for item in suite.specifications)
        ):
            raise ValueError(
                "mechanical proof is restricted to allowlisted exact-artifact verification"
            )

        steps: list[ProcedureStep] = []
        required_capabilities: dict[str, str] = {}
        failure_modes: list[str] = []
        for decision, observation in zip(result.decisions, result.observations, strict=False):
            selected = decision.selected
            if observation.status is not ObservationStatus.SUCCEEDED:
                failure_modes.append(
                    f"{selected.action_type.value} through {selected.capability}: "
                    f"{observation.failure_kind or observation.status.value}"
                )
                continue
            if selected.risk_level is RiskLevel.HIGH:
                raise ValueError("high-risk autonomous steps cannot be compiled")
            previous_version = required_capabilities.get(selected.capability)
            if previous_version is not None and previous_version != observation.capability_version:
                raise ValueError("one procedure cannot pin conflicting capability versions")
            required_capabilities[selected.capability] = observation.capability_version
            steps.append(
                ProcedureStep(
                    order=len(steps),
                    action_type=selected.action_type,
                    capability=selected.capability,
                    capability_version=observation.capability_version,
                    target_role=_target_role(state, selected.target),
                    purpose=selected.purpose,
                    expected_observation=selected.expected_observation,
                    expected_postconditions=_postconditions(selected.action_type),
                    risk_level=selected.risk_level,
                )
            )
        if not steps:
            raise ValueError("verified run contains no successful executable procedure steps")

        source_case = ProcedureRegressionCase(
            case_id=state["session_id"],
            problem_type=problem.problem_type,
            domain=problem.domain,
            constraint_fingerprint=_constraint_fingerprint(problem.constraints),
            verifier_suite_version=suite.version,
            verification_passed=True,
        )
        signature = {
            "task_family": problem.problem_type,
            "gap_types": sorted({gap.gap_type for gap in state["gaps"]}),
            "actions": [step.action_type.value for step in steps],
            "capabilities": required_capabilities,
            "verifier_version": suite.version,
        }
        procedure_id = hashlib.sha256(
            json.dumps(signature, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:20]
        lifecycle = (
            ProcedureLifecycle.VERIFIED if mechanically_proven else ProcedureLifecycle.PROPOSED
        )
        provisional = CompiledProcedure(
            id=procedure_id,
            name=f"{problem.problem_type}:{'-'.join(step.action_type.value for step in steps)}",
            purpose=state["reflection"].outcome_summary,
            task_family=problem.problem_type,
            applicable_gap_types=sorted({gap.gap_type for gap in state["gaps"]}),
            required_evidence_source_types=sorted({item.source_type for item in state["evidence"]}),
            required_capabilities=required_capabilities,
            safety_constraints=_safety_constraints(problem.constraints),
            steps=steps,
            verifier_suite=suite,
            source_session_ids=[state["session_id"]],
            resource_profile=accumulated_usage(state),
            known_failure_modes=list(dict.fromkeys(failure_modes)),
            regression_cases=[source_case],
            lifecycle=lifecycle,
            mechanical_proof=(
                "Allowlisted exact claim/excerpt/provenance invariant was mechanically checked."
                if mechanically_proven
                else None
            ),
            invalidation_conditions=[
                "A required capability version changes.",
                "A safety constraint or evidence provenance requirement is absent.",
                "A present-case verifier fails or remains inconclusive.",
                "A monitored replay reveals a false pass or unsafe transfer.",
            ],
            integrity_hash="pending",
        )
        return _with_integrity(provisional)

    def promote_after_replay(
        self,
        procedure: CompiledProcedure,
        replay_results: list[ProcedureReplayResult],
    ) -> CompiledProcedure:
        """Promote only after two distinct, fully verified replay outcomes."""
        if not procedure_integrity_valid(procedure):
            raise ValueError("procedure integrity check failed")
        if procedure.lifecycle not in {
            ProcedureLifecycle.PROPOSED,
            ProcedureLifecycle.REPLAY_TESTED,
        }:
            raise ValueError("only proposed or replay-tested procedures may be promoted")
        if len({item.case.case_id for item in replay_results}) < 2:
            raise ValueError("procedure promotion requires two distinct replay cases")
        failed = [
            item
            for item in replay_results
            if not (
                item.procedure_completed
                and item.verification_passed
                and item.capability_versions_match
            )
        ]
        if failed:
            raise ValueError("procedure promotion requires every replay to pass independently")
        cases = {
            item.case_id: item
            for item in [*procedure.regression_cases, *(r.case for r in replay_results)]
        }
        promoted = procedure.model_copy(
            update={
                "regression_cases": [cases[key] for key in sorted(cases)],
                "lifecycle": ProcedureLifecycle.VERIFIED,
                "version": procedure.version + 1,
                "integrity_hash": "pending",
            }
        )
        return _with_integrity(promoted)


class ProcedureApplicabilityChecker:
    """Reject unsafe or structurally unsupported transfer before execution."""

    def check(
        self,
        procedure: CompiledProcedure,
        state: PolyaState,
        registry: CapabilityRegistry,
        *,
        allow_unverified_replay: bool = False,
    ) -> ProcedureApplicability:
        reasons: list[str] = []
        if not procedure_integrity_valid(procedure):
            return ProcedureApplicability(
                procedure_id=procedure.id,
                status=ProcedureApplicabilityStatus.INAPPLICABLE,
                reasons=["Procedure integrity hash does not match its trusted contents."],
            )
        trusted_lifecycle = procedure.lifecycle in {
            ProcedureLifecycle.VERIFIED,
            ProcedureLifecycle.DEPLOYED,
            ProcedureLifecycle.MONITORED,
        }
        replay_lifecycle = allow_unverified_replay and procedure.lifecycle in {
            ProcedureLifecycle.PROPOSED,
            ProcedureLifecycle.REPLAY_TESTED,
        }
        if not trusted_lifecycle and not replay_lifecycle:
            return ProcedureApplicability(
                procedure_id=procedure.id,
                status=ProcedureApplicabilityStatus.INAPPLICABLE,
                reasons=["Procedure has not passed the replay or mechanical-proof gate."],
            )
        problem = state["structured_problem"]
        if problem is None:
            return ProcedureApplicability(
                procedure_id=procedure.id,
                status=ProcedureApplicabilityStatus.INCONCLUSIVE,
                reasons=["The current problem has not been represented yet."],
            )
        if problem.problem_type != procedure.task_family:
            reasons.append(
                f"Task family {problem.problem_type!r} does not match {procedure.task_family!r}."
            )
        missing_safety = [
            item for item in procedure.safety_constraints if item not in problem.constraints
        ]
        if missing_safety:
            reasons.append("Required safety constraints are absent from the current task.")
        current_gap_types = {gap.gap_type for gap in state["gaps"] if not gap.filled}
        if (
            procedure.applicable_gap_types
            and current_gap_types
            and not (current_gap_types & set(procedure.applicable_gap_types))
        ):
            reasons.append("Current blocking gap types do not match the compiled procedure.")
        for name, version in procedure.required_capabilities.items():
            capability = registry.get(name)
            if capability is None:
                reasons.append(f"Required capability {name!r} is unavailable.")
            elif capability.definition.version != version:
                reasons.append(
                    f"Capability {name!r} version changed from {version!r} to "
                    f"{capability.definition.version!r}."
                )
        if reasons:
            return ProcedureApplicability(
                procedure_id=procedure.id,
                status=ProcedureApplicabilityStatus.INAPPLICABLE,
                reasons=reasons,
            )
        required_sources = set(procedure.required_evidence_source_types)
        current_sources = {item.source_type for item in state["evidence"]}
        missing_sources = required_sources - current_sources
        acquisition_actions = {
            CognitiveActionType.SEARCH,
            CognitiveActionType.INSPECT,
            CognitiveActionType.OBSERVE,
            CognitiveActionType.MEASURE,
            CognitiveActionType.CALCULATE,
            CognitiveActionType.SIMULATE,
            CognitiveActionType.EXPERIMENT,
            CognitiveActionType.RETRIEVE_MEMORY,
        }
        if missing_sources and not any(
            step.action_type in acquisition_actions for step in procedure.steps
        ):
            return ProcedureApplicability(
                procedure_id=procedure.id,
                status=ProcedureApplicabilityStatus.INCONCLUSIVE,
                reasons=[
                    "Required present-case evidence sources are not yet available: "
                    + ", ".join(sorted(missing_sources))
                ],
            )
        return ProcedureApplicability(
            procedure_id=procedure.id,
            status=ProcedureApplicabilityStatus.APPLICABLE,
            reasons=[
                (
                    "Integrity, replay-only lifecycle, task family, safety, capability versions, and evidence boundary match."
                    if replay_lifecycle
                    else "Integrity, lifecycle, task family, safety, capability versions, and evidence boundary match or are acquired by the procedure."
                )
            ],
        )


class CompiledProcedureLibrary:
    """Minimal in-memory admission boundary for verified compiled procedures."""

    def __init__(self) -> None:
        self._procedures: dict[str, CompiledProcedure] = {}

    def admit(self, procedure: CompiledProcedure) -> None:
        if not procedure_integrity_valid(procedure):
            raise ValueError("cannot admit a procedure with invalid integrity")
        if procedure.lifecycle not in {
            ProcedureLifecycle.VERIFIED,
            ProcedureLifecycle.DEPLOYED,
            ProcedureLifecycle.MONITORED,
        }:
            raise ValueError("cannot admit an unverified procedure for reuse")
        self._procedures[procedure.id] = procedure

    def applicable(
        self,
        state: PolyaState,
        registry: CapabilityRegistry,
    ) -> list[CompiledProcedure]:
        checker = ProcedureApplicabilityChecker()
        return [
            procedure
            for procedure in self._procedures.values()
            if checker.check(procedure, state, registry).status
            is ProcedureApplicabilityStatus.APPLICABLE
        ]

    def procedures(self) -> list[CompiledProcedure]:
        return [self._procedures[key] for key in sorted(self._procedures)]


def procedure_compiled_event(procedure: CompiledProcedure) -> StateEvent:
    """Expose a compiled proposal without silently adding it to trusted memory."""
    return StateEvent(
        engine_name="procedure_compiler",
        event_type=PROCEDURE_COMPILED_EVENT,
        reasoning_mode=ReasoningMode.REFLECT,
        summary=f"Compiled procedure {procedure.id} in {procedure.lifecycle.value} lifecycle.",
        metadata=procedure.model_dump(mode="json"),
    )


def procedure_replayed_event(procedure: CompiledProcedure) -> StateEvent:
    """Expose successful replay promotion in the audit trace."""
    return StateEvent(
        engine_name="procedure_compiler",
        event_type=PROCEDURE_REPLAYED_EVENT,
        reasoning_mode=ReasoningMode.VERIFY,
        summary=f"Procedure {procedure.id} passed replay and is {procedure.lifecycle.value}.",
        metadata=procedure.model_dump(mode="json"),
    )
