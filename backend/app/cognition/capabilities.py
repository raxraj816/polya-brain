"""Typed capability registry used by the cognitive kernel."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pydantic import JsonValue

from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveObservation,
    ObservationStatus,
)
from app.graph.state import PolyaState
from app.tracing.sanitization import sanitize_text


class AuditedCapabilityError(RuntimeError):
    """Safe capability failure carrying bounded non-content telemetry."""

    def __init__(
        self,
        summary: str,
        *,
        failure_kind: str,
        payload: JsonValue = None,
    ) -> None:
        self.safe_summary = sanitize_text(summary).strip() or "Capability failed safely."
        self.failure_kind = sanitize_text(failure_kind).strip() or "capability_failure"
        self.payload = payload
        super().__init__(self.safe_summary)


class CognitiveCapability(Protocol):
    """A replaceable tool that executes one selected cognitive action."""

    definition: CapabilityDefinition

    def execute(
        self,
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        """Return an observation without directly mutating canonical state."""
        ...


type CapabilityExecutor = Callable[[CognitiveActionCandidate, PolyaState], CognitiveObservation]


def safe_observation_trace_telemetry(payload: JsonValue) -> dict[str, JsonValue]:
    """Extract bounded non-content telemetry for the durable audit trace."""
    if not isinstance(payload, dict):
        return {}

    telemetry: dict[str, JsonValue] = {}
    for key in ("provider", "model", "procedure", "policy_version", "terminal_failure_kind"):
        value = payload.get(key)
        if isinstance(value, str):
            sanitized = sanitize_text(value).strip()[:200]
            if sanitized:
                telemetry[key] = sanitized

    model_calls = payload.get("model_calls")
    if type(model_calls) is int and model_calls >= 0:
        telemetry["model_calls"] = model_calls

    raw_attempts = payload.get("route_attempts")
    if not isinstance(raw_attempts, list):
        return telemetry

    attempts: list[JsonValue] = []
    for raw_attempt in raw_attempts[:2]:
        if not isinstance(raw_attempt, dict):
            continue
        attempt: dict[str, JsonValue] = {}
        route = raw_attempt.get("route")
        if isinstance(route, str):
            sanitized_route = sanitize_text(route).strip()[:200]
            if sanitized_route:
                attempt["route"] = sanitized_route
        succeeded = raw_attempt.get("succeeded")
        if isinstance(succeeded, bool):
            attempt["succeeded"] = succeeded
        duration_ms = raw_attempt.get("duration_ms")
        if (
            isinstance(duration_ms, int | float)
            and not isinstance(duration_ms, bool)
            and duration_ms >= 0
        ):
            attempt["duration_ms"] = round(float(duration_ms), 3)
        provider_attempts = raw_attempt.get("provider_attempts")
        if type(provider_attempts) is int and provider_attempts >= 0:
            attempt["provider_attempts"] = provider_attempts
        failure_kind = raw_attempt.get("failure_kind")
        if isinstance(failure_kind, str):
            sanitized_failure = sanitize_text(failure_kind).strip()[:100]
            if sanitized_failure:
                attempt["failure_kind"] = sanitized_failure
        if "route" in attempt:
            attempts.append(attempt)
    if attempts:
        telemetry["route_attempts"] = attempts
    return telemetry


class FunctionCapability:
    """Small adapter for deterministic tools and test capabilities."""

    def __init__(
        self,
        definition: CapabilityDefinition,
        executor: CapabilityExecutor,
    ) -> None:
        self.definition = definition
        self._executor = executor

    def execute(
        self,
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        """Execute only action types declared by this capability."""
        if action.action_type not in self.definition.supported_actions:
            return CognitiveObservation(
                action_id=action.id,
                capability=self.definition.name,
                capability_version=self.definition.version,
                status=ObservationStatus.FAILED,
                summary=(
                    f"Capability {self.definition.name} does not support "
                    f"{action.action_type.value}."
                ),
                failure_kind="unsupported_action",
            )
        return self._executor(action, state)


class CapabilityRegistry:
    """Registry that prevents the controller from calling undeclared tools."""

    def __init__(self) -> None:
        self._capabilities: dict[str, CognitiveCapability] = {}

    def register(self, capability: CognitiveCapability) -> None:
        """Register a unique capability by its stable name."""
        name = capability.definition.name
        if name in self._capabilities:
            raise ValueError(f"capability already registered: {name}")
        self._capabilities[name] = capability

    def get(self, name: str) -> CognitiveCapability | None:
        """Return a capability without guessing or falling back silently."""
        return self._capabilities.get(name)

    def supports(self, name: str, action_type: object) -> bool:
        """Return whether a named capability explicitly supports an action."""
        capability = self.get(name)
        return bool(
            capability is not None and action_type in capability.definition.supported_actions
        )

    def definitions(self) -> list[CapabilityDefinition]:
        """Expose sorted metadata for action generation and audit."""
        return [self._capabilities[name].definition for name in sorted(self._capabilities)]

    def execute(
        self,
        action: CognitiveActionCandidate,
        state: PolyaState,
        *,
        approved: bool = False,
    ) -> CognitiveObservation:
        """Execute through the declared boundary and enforce approval."""
        capability = self.get(action.capability)
        if capability is None:
            return CognitiveObservation(
                action_id=action.id,
                capability=action.capability,
                capability_version="unavailable",
                status=ObservationStatus.BLOCKED,
                summary=f"Capability {action.capability} is not registered.",
                failure_kind="capability_unavailable",
            )
        if capability.definition.requires_approval and not approved:
            return CognitiveObservation(
                action_id=action.id,
                capability=action.capability,
                capability_version=capability.definition.version,
                status=ObservationStatus.BLOCKED,
                summary=f"Capability {action.capability} requires approval.",
                failure_kind="approval_required",
            )
        try:
            return capability.execute(action, state)
        except AuditedCapabilityError as exc:
            return CognitiveObservation(
                action_id=action.id,
                capability=action.capability,
                capability_version=capability.definition.version,
                status=ObservationStatus.FAILED,
                summary=exc.safe_summary,
                payload=exc.payload,
                failure_kind=exc.failure_kind,
            )
        except Exception as exc:  # noqa: BLE001 - capability boundary must fail closed
            return CognitiveObservation(
                action_id=action.id,
                capability=action.capability,
                capability_version=capability.definition.version,
                status=ObservationStatus.FAILED,
                summary=f"Capability execution failed with {type(exc).__name__}.",
                failure_kind="capability_exception",
            )
