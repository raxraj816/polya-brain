"""Adapters that expose existing PolyaBrain engines as cognitive capabilities."""

from __future__ import annotations

from typing import cast

from pydantic import JsonValue

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
from app.engines import EngineStatus, PolyaEngine, engine_event_metadata, run_engine
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import RiskLevel, StructuredProblem
from app.problem_understanding.fallbacks import deterministic_problem_understanding
from app.problem_understanding.prompt import PROBLEM_UNDERSTANDING_MAX_OUTPUT_TOKENS
from app.tracing.sanitization import sanitize_text


def problem_representation_capability(
    engine: PolyaEngine,
    *,
    deterministic_only: bool = False,
) -> FunctionCapability:
    """Wrap the Chapter 13 representation engine without giving it loop control."""
    raw_max_model_calls = getattr(engine, "max_provider_attempts", 4)
    max_model_calls = (
        raw_max_model_calls
        if type(raw_max_model_calls) is int and 1 <= raw_max_model_calls <= 10
        else 4
    )
    definition = CapabilityDefinition(
        name="deterministic_problem_representation"
        if deterministic_only
        else "problem_representation",
        version=f"deterministic:{engine.version.engine}"
        if deterministic_only
        else engine.version.engine,
        supported_actions={CognitiveActionType.INTERPRET},
        risk_level=RiskLevel.LOW,
        estimated_cost=0.1,
        approved_for_sensitive_data=deterministic_only,
        kind=CapabilityKind.DETERMINISTIC if deterministic_only else CapabilityKind.MODEL,
        max_model_calls=0 if deterministic_only else max_model_calls,
        max_output_tokens=0 if deterministic_only else PROBLEM_UNDERSTANDING_MAX_OUTPUT_TOKENS,
        timeout_seconds=1.0 if deterministic_only else 90.0,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        if deterministic_only and deterministic_problem_understanding(state) is None:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.INCONCLUSIVE,
                summary="The input requires semantic representation; no model was called.",
                failure_kind="deterministic_representation_inapplicable",
                payload={"model_calls": 0},
            )
        output = run_engine(engine, state)
        result = output.result
        raw_events = output.state_delta.get("events", [])
        trace_events = (
            [StateEvent.model_validate(item) for item in raw_events]
            if isinstance(raw_events, list)
            else []
        )
        fallback_used = any(
            event.event_type == "deterministic_fallback_used" for event in trace_events
        )
        observed_call_counts: list[int] = []
        for event in trace_events:
            for key in ("llm_call_count", "model_calls"):
                raw_call_count = event.metadata.get(key, 0)
                if type(raw_call_count) is int:
                    observed_call_counts.append(raw_call_count)
        model_calls = max(observed_call_counts, default=0)
        if not fallback_used and model_calls == 0:
            model_calls = definition.max_model_calls
        route_event = next(
            (event for event in trace_events if event.event_type == "semantic_routes_attempted"),
            None,
        )
        route_attempts = (
            route_event.metadata.get("route_attempts", []) if route_event is not None else []
        )
        route_failure_kind = (
            route_event.metadata.get("failure_kind") if route_event is not None else None
        )
        payload = cast(
            JsonValue,
            {
                "engine_result": engine_event_metadata(result),
                "summary": sanitize_text(result.summary),
                "usage": result.token_usage.model_dump(mode="json"),
                "model_calls": model_calls,
                "procedure": "deterministic" if fallback_used else "model",
                "route_attempts": route_attempts,
                "terminal_failure_kind": route_failure_kind,
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
                failure_kind=(
                    route_failure_kind
                    if isinstance(route_failure_kind, str) and route_failure_kind
                    else f"engine_{result.status.value}"
                ),
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
