"""Typed capability registry used by the cognitive kernel."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveObservation,
    ObservationStatus,
)
from app.graph.state import PolyaState


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
        except Exception as exc:  # noqa: BLE001 - capability boundary must fail closed
            return CognitiveObservation(
                action_id=action.id,
                capability=action.capability,
                capability_version=capability.definition.version,
                status=ObservationStatus.FAILED,
                summary=f"Capability execution failed with {type(exc).__name__}.",
                failure_kind="capability_exception",
            )
