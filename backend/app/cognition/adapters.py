"""Adapters that expose existing PolyaBrain engines as cognitive capabilities."""

from __future__ import annotations

from typing import cast

from pydantic import JsonValue

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.engines import EngineStatus, PolyaEngine, engine_event_metadata, run_engine
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import RiskLevel, StructuredProblem
from app.tracing.sanitization import sanitize_text


def problem_representation_capability(engine: PolyaEngine) -> FunctionCapability:
    """Wrap the Chapter 13 representation engine without giving it loop control."""
    definition = CapabilityDefinition(
        name="problem_representation",
        version=engine.version.engine,
        supported_actions={CognitiveActionType.INTERPRET},
        risk_level=RiskLevel.LOW,
        estimated_cost=0.1,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        output = run_engine(engine, state)
        result = output.result
        raw_events = output.state_delta.get("events", [])
        trace_events = (
            [StateEvent.model_validate(item) for item in raw_events]
            if isinstance(raw_events, list)
            else []
        )
        payload = cast(
            JsonValue,
            {
                "engine_result": engine_event_metadata(result),
                "summary": sanitize_text(result.summary),
            },
        )

        if result.status is EngineStatus.NEEDS_INPUT:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.BLOCKED,
                summary=result.summary,
                payload=payload,
                proposed_update=CognitiveStateUpdate(
                    questions_to_ask=list(result.missing_inputs),
                    trace_events_to_add=trace_events,
                ),
                failure_kind="human_input_required",
            )

        structured_problem = output.state_delta.get("structured_problem")
        if result.status is not EngineStatus.OK or not isinstance(
            structured_problem,
            StructuredProblem,
        ):
            inconclusive_statuses = {
                EngineStatus.NEEDS_EVIDENCE,
                EngineStatus.LOW_CONFIDENCE,
                EngineStatus.INSUFFICIENT_EVIDENCE,
            }
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=(
                    ObservationStatus.INCONCLUSIVE
                    if result.status in inconclusive_statuses
                    else ObservationStatus.FAILED
                ),
                summary=result.summary,
                payload=payload,
                proposed_update=CognitiveStateUpdate(trace_events_to_add=trace_events),
                failure_kind=f"engine_{result.status.value}",
            )

        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=result.summary,
            payload=payload,
            proposed_update=CognitiveStateUpdate(
                structured_problem=structured_problem,
                trace_events_to_add=trace_events,
            ),
        )

    return FunctionCapability(definition, execute)


def constraint_discovery_capability(engine: PolyaEngine) -> FunctionCapability:
    """Wrap Chapter 14 constraint discovery as a controller-owned action."""
    definition = CapabilityDefinition(
        name="constraint_discovery",
        version=engine.version.engine,
        supported_actions={CognitiveActionType.DISCOVER_CONSTRAINTS},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.02,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        output = run_engine(engine, state)
        result = output.result
        raw_events = output.state_delta.get("events", [])
        trace_events = (
            [StateEvent.model_validate(item) for item in raw_events]
            if isinstance(raw_events, list)
            else []
        )
        payload = cast(
            JsonValue,
            {
                "engine_result": engine_event_metadata(result),
                "summary": sanitize_text(result.summary),
            },
        )
        if result.status is EngineStatus.NEEDS_INPUT:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.BLOCKED,
                summary=result.summary,
                payload=payload,
                proposed_update=CognitiveStateUpdate(
                    questions_to_ask=list(result.missing_inputs),
                    trace_events_to_add=trace_events,
                ),
                failure_kind="human_input_required",
            )

        structured_problem = output.state_delta.get("structured_problem")
        if result.status is not EngineStatus.OK or not isinstance(
            structured_problem,
            StructuredProblem,
        ):
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary=result.summary,
                payload=payload,
                proposed_update=CognitiveStateUpdate(trace_events_to_add=trace_events),
                failure_kind=f"engine_{result.status.value}",
            )

        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=result.summary,
            payload=payload,
            proposed_update=CognitiveStateUpdate(
                structured_problem=structured_problem,
                trace_events_to_add=trace_events,
            ),
        )

    return FunctionCapability(definition, execute)
