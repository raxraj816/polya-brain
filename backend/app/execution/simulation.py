"""Typed deterministic scenario simulation capability."""

from __future__ import annotations

import json
from decimal import Decimal

from pydantic import Field, JsonValue, field_validator

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

_SPEC_MARKER = "SIMULATION_SPEC:"


class ScenarioSimulationSpec(ContractModel):
    """Bounded compound-growth sensitivity model."""

    initial_value: Decimal = Field(ge=Decimal("0"), le=Decimal("1e18"))
    periods: int = Field(ge=1, le=120)
    scenario_rates: dict[NonEmptyStr, Decimal] = Field(min_length=1, max_length=20)
    threshold: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("1e18"))
    unit: NonEmptyStr = "units"

    @field_validator("scenario_rates")
    @classmethod
    def rates_are_bounded(cls, value: dict[str, Decimal]) -> dict[str, Decimal]:
        if any(rate < Decimal("-1") or rate > Decimal("10") for rate in value.values()):
            raise ValueError("scenario rates must be between -1 and 10 per period")
        return value


class ScenarioProjection(ContractModel):
    """One deterministic scenario trajectory."""

    scenario: NonEmptyStr
    rate: Decimal
    values: list[Decimal]
    threshold_crossing_period: int | None = Field(default=None, ge=0)


class ScenarioSimulationResult(ContractModel):
    """Auditable output of all requested scenarios."""

    spec: ScenarioSimulationSpec
    projections: list[ScenarioProjection]


def _extract_spec(raw_input: str) -> ScenarioSimulationSpec | None:
    marker_index = raw_input.rfind(_SPEC_MARKER)
    if marker_index < 0:
        return None
    raw = raw_input[marker_index + len(_SPEC_MARKER) :].lstrip()
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("SIMULATION_SPEC must be followed by one JSON object") from exc
    return ScenarioSimulationSpec.model_validate(payload)


def run_scenario_simulation(spec: ScenarioSimulationSpec) -> ScenarioSimulationResult:
    """Run exact Decimal compound projections with threshold crossings."""
    projections: list[ScenarioProjection] = []
    for scenario, rate in sorted(spec.scenario_rates.items()):
        values = [spec.initial_value]
        crossing = (
            0 if spec.threshold is not None and spec.initial_value >= spec.threshold else None
        )
        current = spec.initial_value
        for period in range(1, spec.periods + 1):
            current *= Decimal(1) + rate
            values.append(current)
            if crossing is None and spec.threshold is not None and current >= spec.threshold:
                crossing = period
        projections.append(
            ScenarioProjection(
                scenario=scenario,
                rate=rate,
                values=values,
                threshold_crossing_period=crossing,
            )
        )
    return ScenarioSimulationResult(spec=spec, projections=projections)


def scenario_simulation_capability(
    gateway: CognitiveModelGateway | None = None,
) -> FunctionCapability:
    """Design a bounded spec when permitted, then execute it deterministically."""
    definition = CapabilityDefinition(
        name="simulator",
        version="scenario_simulator@0.1.0",
        supported_actions={CognitiveActionType.SIMULATE, CognitiveActionType.EXECUTE},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.06,
    )

    def execute(action: CognitiveActionCandidate, state: PolyaState) -> CognitiveObservation:
        task = next((item for item in state["plan"] if item.id == action.target), None)
        raw_spec = task.params.get("simulation_spec") if task is not None else None
        spec: ScenarioSimulationSpec | None
        try:
            if isinstance(raw_spec, dict):
                spec = ScenarioSimulationSpec.model_validate(raw_spec)
                design_source = "plan_task"
            else:
                spec = _extract_spec(state["raw_input"])
                design_source = "explicit_user_spec"
            if spec is None and gateway is not None:
                designed = gateway.complete(
                    capability=definition.name,
                    instructions=(
                        "Translate only explicit numeric assumptions in current state into a "
                        "bounded compound-growth scenario spec. initial_value is the baseline; "
                        "scenario_rates are decimal per-period rates; periods and threshold must "
                        "be explicit or safely derivable. Do not invent missing numbers."
                    ),
                    output_type=ScenarioSimulationSpec,
                    state=state,
                    max_output_tokens=900,
                )
                spec = designed.output
                design_source = "schema_bound_model_design"
        except ValueError as exc:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary=f"Simulation specification was invalid ({type(exc).__name__}).",
                failure_kind="simulation_spec_invalid",
            )
        if spec is None:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.BLOCKED,
                summary="A bounded simulation specification is required before execution.",
                failure_kind="human_input_required",
                proposed_update=CognitiveStateUpdate(
                    questions_to_ask=[
                        "Provide initial_value, periods, scenario_rates, optional threshold, "
                        "and unit as a SIMULATION_SPEC JSON object."
                    ]
                ),
            )
        result = run_scenario_simulation(spec)
        serialized = result.model_dump_json()
        event = StateEvent(
            engine_name=definition.name,
            event_type="scenario_simulation_completed",
            reasoning_mode=ReasoningMode.EXECUTE,
            summary=f"Executed {len(result.projections)} bounded scenario projection(s).",
            metadata={
                "design_source": design_source,
                "scenario_count": len(result.projections),
                "periods": spec.periods,
                "unit": spec.unit,
            },
        )
        update = CognitiveStateUpdate(
            resolved_gap_targets=(
                [action.target] if action.action_type is CognitiveActionType.SIMULATE else []
            ),
            execution_outputs_to_add=(
                [
                    ExecutionOutput(
                        task_id=action.target,
                        summary=event.summary,
                        output=result.model_dump(mode="json"),
                    )
                ]
                if action.action_type is CognitiveActionType.EXECUTE
                else []
            ),
            trace_events_to_add=[event],
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
                    source_type="deterministic_scenario_simulation",
                    source_uri=f"simulation://{action.id}",
                    claim=serialized,
                    raw_excerpt=serialized,
                    reliability_score=1.0,
                    relevance_score=1.0,
                )
            ],
            proposed_update=update,
        )

    return FunctionCapability(definition, execute)
