"""Bounded evaluation of explicit controlled numeric experiments."""

from __future__ import annotations

import json
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, JsonValue, model_validator

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.cognition.model_gateway import CognitiveModelGateway
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import ContractModel, EvidenceItem, NonEmptyStr, ReasoningMode, RiskLevel

_SPEC_MARKER = "EXPERIMENT_SPEC:"


class EffectDirection(StrEnum):
    HIGHER = "higher"
    LOWER = "lower"


class ControlledExperimentSpec(ContractModel):
    """Explicit observations and validity assertions for one comparison."""

    metric: NonEmptyStr
    control_values: list[Decimal] = Field(min_length=2, max_length=10_000)
    treatment_values: list[Decimal] = Field(min_length=2, max_length=10_000)
    desired_direction: EffectDirection
    minimum_effect: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    randomized: bool
    independent_observations: bool

    @model_validator(mode="after")
    def controlled_design_is_required(self) -> ControlledExperimentSpec:
        if not self.randomized or not self.independent_observations:
            raise ValueError("controlled evaluation requires randomized independent observations")
        return self


class ControlledExperimentResult(ContractModel):
    """Deterministic effect and approximate 95% interval."""

    metric: NonEmptyStr
    control_count: int = Field(ge=2)
    treatment_count: int = Field(ge=2)
    control_mean: Decimal
    treatment_mean: Decimal
    absolute_effect: Decimal
    relative_effect_percent: Decimal | None = None
    standard_error: Decimal
    confidence_interval_low: Decimal
    confidence_interval_high: Decimal
    desired_effect_observed: bool
    minimum_effect_met: bool
    interval_excludes_zero_in_desired_direction: bool
    interval_method: NonEmptyStr = "normal_approximation_95_percent"
    limitations: list[NonEmptyStr] = Field(
        default_factory=lambda: [
            "The interval is a normal approximation, not an exact small-sample test.",
            "Randomization and independence are asserted by the supplied specification, "
            "not independently observed by PolyaBrain.",
        ]
    )


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values) / Decimal(len(values))


def _sample_variance(values: list[Decimal], mean: Decimal) -> Decimal:
    return sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)


def evaluate_controlled_experiment(
    spec: ControlledExperimentSpec,
) -> ControlledExperimentResult:
    """Compare means with a deterministic normal-approximation interval."""
    control_mean = _mean(spec.control_values)
    treatment_mean = _mean(spec.treatment_values)
    effect = treatment_mean - control_mean
    variance_control = _sample_variance(spec.control_values, control_mean)
    variance_treatment = _sample_variance(spec.treatment_values, treatment_mean)
    standard_error = (
        variance_control / Decimal(len(spec.control_values))
        + variance_treatment / Decimal(len(spec.treatment_values))
    ).sqrt()
    margin = Decimal("1.96") * standard_error
    low = effect - margin
    high = effect + margin
    desired = effect > 0 if spec.desired_direction is EffectDirection.HIGHER else effect < 0
    minimum_met = (
        effect >= spec.minimum_effect
        if spec.desired_direction is EffectDirection.HIGHER
        else -effect >= spec.minimum_effect
    )
    excludes = low > 0 if spec.desired_direction is EffectDirection.HIGHER else high < 0
    relative = (effect / abs(control_mean)) * Decimal(100) if control_mean != 0 else None
    return ControlledExperimentResult(
        metric=spec.metric,
        control_count=len(spec.control_values),
        treatment_count=len(spec.treatment_values),
        control_mean=control_mean,
        treatment_mean=treatment_mean,
        absolute_effect=effect,
        relative_effect_percent=relative,
        standard_error=standard_error,
        confidence_interval_low=low,
        confidence_interval_high=high,
        desired_effect_observed=desired,
        minimum_effect_met=minimum_met,
        interval_excludes_zero_in_desired_direction=excludes,
    )


def _extract_spec(raw_input: str) -> ControlledExperimentSpec | None:
    index = raw_input.rfind(_SPEC_MARKER)
    if index < 0:
        return None
    raw = raw_input[index + len(_SPEC_MARKER) :].lstrip()
    try:
        payload, _ = json.JSONDecoder().raw_decode(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("EXPERIMENT_SPEC must be followed by one JSON object") from exc
    return ControlledExperimentSpec.model_validate(payload)


def controlled_experiment_capability(
    gateway: CognitiveModelGateway | None = None,
) -> FunctionCapability:
    """Evaluate explicit observations without performing real-world interventions."""
    definition = CapabilityDefinition(
        name="experiment",
        version="controlled_numeric_experiment@0.1.0",
        supported_actions={CognitiveActionType.EXPERIMENT, CognitiveActionType.EXECUTE},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.07,
    )

    def execute(action: CognitiveActionCandidate, state: PolyaState) -> CognitiveObservation:
        task = next((item for item in state["plan"] if item.id == action.target), None)
        raw_spec = task.params.get("experiment_spec") if task is not None else None
        spec: ControlledExperimentSpec | None
        try:
            if isinstance(raw_spec, dict):
                spec = ControlledExperimentSpec.model_validate(raw_spec)
                design_source = "plan_task"
            else:
                spec = _extract_spec(state["raw_input"])
                design_source = "explicit_user_spec"
            if spec is None and gateway is not None:
                designed = gateway.complete(
                    capability=definition.name,
                    instructions=(
                        "Translate only explicit control and treatment observations into the "
                        "experiment schema. Never invent observations or claim randomization or "
                        "independence unless current state explicitly states them."
                    ),
                    output_type=ControlledExperimentSpec,
                    state=state,
                    max_output_tokens=1000,
                )
                spec = designed.output
                design_source = "schema_bound_model_design"
        except ValueError as exc:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary=f"Controlled experiment specification was invalid ({type(exc).__name__}).",
                failure_kind="experiment_spec_invalid",
            )
        if spec is None:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.BLOCKED,
                summary="Explicit controlled observations are required before evaluation.",
                failure_kind="human_input_required",
                proposed_update=CognitiveStateUpdate(
                    questions_to_ask=[
                        "Provide metric, control_values, treatment_values, desired_direction, "
                        "minimum_effect, randomized, and independent_observations in an "
                        "EXPERIMENT_SPEC JSON object."
                    ]
                ),
            )
        result = evaluate_controlled_experiment(spec)
        serialized = result.model_dump_json()
        event = StateEvent(
            engine_name=definition.name,
            event_type="controlled_experiment_evaluated",
            reasoning_mode=ReasoningMode.EXECUTE,
            summary=(
                f"Evaluated {result.control_count} control and "
                f"{result.treatment_count} treatment observation(s)."
            ),
            metadata={
                "design_source": design_source,
                "metric": spec.metric,
                "desired_effect_observed": result.desired_effect_observed,
                "minimum_effect_met": result.minimum_effect_met,
                "interval_excludes_zero": result.interval_excludes_zero_in_desired_direction,
            },
        )
        payload: JsonValue = result.model_dump(mode="json")
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=event.summary,
            payload=payload,
            evidence=[
                EvidenceItem(
                    source_type="controlled_experiment_evaluation",
                    source_uri=f"experiment://{action.id}",
                    claim=serialized,
                    raw_excerpt=serialized,
                    reliability_score=0.8,
                    relevance_score=1.0,
                )
            ],
            proposed_update=CognitiveStateUpdate(
                resolved_gap_targets=(
                    [action.target] if action.action_type is CognitiveActionType.EXPERIMENT else []
                ),
                execution_outputs_to_add=(
                    [
                        ExecutionOutput(
                            task_id=action.target,
                            summary=event.summary,
                            output=payload,
                        )
                    ]
                    if action.action_type is CognitiveActionType.EXECUTE
                    else []
                ),
                trace_events_to_add=[event],
            ),
        )

    return FunctionCapability(definition, execute)
