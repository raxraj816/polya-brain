"""Bounded empirical capability health for Chapter 13-F adaptive routing."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from statistics import fmean, median
from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from app.cognition.contracts import (
    CapabilityDefinition,
    CapabilityKind,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveRunStatus,
    ObservationStatus,
)
from app.cognition.task_model import USAGE_EVENT
from app.graph.state import PolyaState
from app.models.contracts import ContractModel, NonEmptyStr, Score

if TYPE_CHECKING:
    from app.cognition.kernel import CognitiveRunResult
    from app.cognition.procedure_executor import ProcedureExecutionResult

PERFORMANCE_POLICY_VERSION = "adaptive-performance@0.1.0"


class CapabilityPerformanceSample(ContractModel):
    """One trace-derived capability attempt and its terminal usefulness label."""

    session_id: NonEmptyStr
    task_family: NonEmptyStr
    action_type: CognitiveActionType
    capability: NonEmptyStr
    capability_version: NonEmptyStr
    capability_kind: CapabilityKind
    operational_success: bool
    contributed_to_verified_outcome: bool
    duration_ms: Annotated[float, Field(ge=0.0, le=3_600_000.0)] = 0.0
    model_calls: Annotated[int, Field(ge=0)] = 0
    external_calls: Annotated[int, Field(ge=0)] = 0
    input_tokens: Annotated[int, Field(ge=0)] = 0
    output_tokens: Annotated[int, Field(ge=0)] = 0
    normalized_cost: Annotated[float, Field(ge=0.0)] = 0.0


class CapabilityPerformanceProfile(ContractModel):
    """Version-scoped empirical summary with conservative smoothed estimates."""

    task_family: NonEmptyStr
    action_type: CognitiveActionType
    capability: NonEmptyStr
    capability_version: NonEmptyStr
    sample_count: Annotated[int, Field(ge=0)]
    operational_successes: Annotated[int, Field(ge=0)]
    verified_contributions: Annotated[int, Field(ge=0)]
    smoothed_operational_reliability: Score
    smoothed_verified_yield: Score
    median_duration_ms: Annotated[float, Field(ge=0.0)]
    p95_duration_ms: Annotated[float, Field(ge=0.0)]
    average_model_calls: Annotated[float, Field(ge=0.0)]
    average_external_calls: Annotated[float, Field(ge=0.0)]
    average_total_tokens: Annotated[float, Field(ge=0.0)]
    average_normalized_cost: Annotated[float, Field(ge=0.0)]


class AdaptiveActionEstimate(ContractModel):
    """Bounded empirical adjustment applied after hard eligibility gates."""

    policy_version: NonEmptyStr = PERFORMANCE_POLICY_VERSION
    sample_count: Annotated[int, Field(ge=0)]
    sample_confidence: Score
    progress_multiplier: Annotated[float, Field(ge=0.35, le=1.0)]
    extra_effective_cost: Annotated[float, Field(ge=0.0, le=2.0)]
    predicted_operational_reliability: Score
    predicted_verified_yield: Score
    predicted_median_duration_ms: Annotated[float, Field(ge=0.0)]
    rationale: NonEmptyStr


type PerformanceKey = tuple[str, CognitiveActionType, str, str]


def _non_negative_int(metadata: Mapping[str, object], name: str) -> int:
    value = metadata.get(name, 0)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


class CapabilityPerformanceLedger:
    """Bounded in-process evidence store and adaptive policy."""

    policy_version = PERFORMANCE_POLICY_VERSION

    def __init__(self, *, max_samples_per_profile: int = 100) -> None:
        if not 5 <= max_samples_per_profile <= 10_000:
            raise ValueError("max_samples_per_profile must be between 5 and 10000")
        self._max_samples = max_samples_per_profile
        self._samples: dict[PerformanceKey, list[CapabilityPerformanceSample]] = defaultdict(list)

    @staticmethod
    def _key(
        task_family: str,
        action_type: CognitiveActionType,
        capability: str,
        capability_version: str,
    ) -> PerformanceKey:
        return (task_family, action_type, capability, capability_version)

    def record(self, sample: CapabilityPerformanceSample) -> None:
        """Append one bounded sample without mixing capability versions."""
        key = self._key(
            sample.task_family,
            sample.action_type,
            sample.capability,
            sample.capability_version,
        )
        samples = self._samples[key]
        samples.append(sample)
        if len(samples) > self._max_samples:
            del samples[: len(samples) - self._max_samples]

    def observe_run(self, result: CognitiveRunResult) -> list[CapabilityPerformanceSample]:
        """Derive samples from audited actions, observations, usage, and final verification."""
        return self._observe_actions(
            result.state,
            [decision.selected for decision in result.decisions],
            list(result.observations),
            terminal_completed=result.status is CognitiveRunStatus.COMPLETED,
        )

    def observe_procedure(
        self,
        result: ProcedureExecutionResult,
    ) -> list[CapabilityPerformanceSample]:
        """Learn from governed procedure steps under the same trace boundary."""
        return self._observe_actions(
            result.state,
            list(result.actions),
            list(result.observations),
            terminal_completed=result.status.value == "completed",
        )

    def _observe_actions(
        self,
        state: PolyaState,
        actions: list[CognitiveActionCandidate],
        observations: list[CognitiveObservation],
        *,
        terminal_completed: bool,
    ) -> list[CapabilityPerformanceSample]:
        problem = state["structured_problem"]
        task_family = problem.problem_type if problem is not None else "unrepresented"
        durations = {
            str(event.metadata.get("action_id")): float(duration)
            for event in state["events"]
            if event.event_type == "capability_observation"
            and isinstance(event.metadata.get("action_id"), str)
            and isinstance((duration := event.metadata.get("duration_ms")), int | float)
            and not isinstance(duration, bool)
        }
        usage_by_action = {
            str(event.metadata.get("action_id")): event.metadata
            for event in state["events"]
            if event.event_type == USAGE_EVENT and isinstance(event.metadata.get("action_id"), str)
        }
        verified_outcome = bool(
            terminal_completed
            and state["verification"] is not None
            and state["verification"].passed
            and state["final_answer"]
        )
        samples: list[CapabilityPerformanceSample] = []
        for action, observation in zip(actions, observations, strict=False):
            usage = usage_by_action.get(action.id, {})

            raw_cost = usage.get("normalized_cost", 0.0)
            normalized_cost = (
                float(raw_cost)
                if isinstance(raw_cost, int | float)
                and not isinstance(raw_cost, bool)
                and raw_cost >= 0
                else 0.0
            )
            raw_kind = usage.get("capability_kind", CapabilityKind.DETERMINISTIC.value)
            try:
                kind = CapabilityKind(str(raw_kind))
            except ValueError:
                kind = CapabilityKind.DETERMINISTIC
            operational_success = observation.status is ObservationStatus.SUCCEEDED
            sample = CapabilityPerformanceSample(
                session_id=state["session_id"],
                task_family=task_family,
                action_type=action.action_type,
                capability=observation.capability,
                capability_version=observation.capability_version,
                capability_kind=kind,
                operational_success=operational_success,
                contributed_to_verified_outcome=operational_success and verified_outcome,
                duration_ms=max(0.0, durations.get(action.id, 0.0)),
                model_calls=_non_negative_int(usage, "model_calls"),
                external_calls=_non_negative_int(usage, "external_calls"),
                input_tokens=_non_negative_int(usage, "input_tokens"),
                output_tokens=_non_negative_int(usage, "output_tokens"),
                normalized_cost=normalized_cost,
            )
            self.record(sample)
            samples.append(sample)
        return samples

    def profile(
        self,
        task_family: str,
        action_type: CognitiveActionType,
        capability: str,
        capability_version: str,
    ) -> CapabilityPerformanceProfile:
        """Return a conservative Beta(1,1)-smoothed profile."""
        samples = self._samples.get(
            self._key(task_family, action_type, capability, capability_version),
            [],
        )
        count = len(samples)
        operational = sum(item.operational_success for item in samples)
        verified = sum(item.contributed_to_verified_outcome for item in samples)
        durations = sorted(item.duration_ms for item in samples)
        p95_index = max(0, math.ceil(0.95 * count) - 1) if count else 0
        return CapabilityPerformanceProfile(
            task_family=task_family,
            action_type=action_type,
            capability=capability,
            capability_version=capability_version,
            sample_count=count,
            operational_successes=operational,
            verified_contributions=verified,
            smoothed_operational_reliability=(operational + 1) / (count + 2),
            smoothed_verified_yield=(verified + 1) / (count + 2),
            median_duration_ms=median(durations) if durations else 0.0,
            p95_duration_ms=durations[p95_index] if durations else 0.0,
            average_model_calls=fmean(item.model_calls for item in samples) if samples else 0.0,
            average_external_calls=(
                fmean(item.external_calls for item in samples) if samples else 0.0
            ),
            average_total_tokens=(
                fmean(item.input_tokens + item.output_tokens for item in samples)
                if samples
                else 0.0
            ),
            average_normalized_cost=(
                fmean(item.normalized_cost for item in samples) if samples else 0.0
            ),
        )

    def estimate(
        self,
        state: PolyaState,
        candidate: CognitiveActionCandidate,
        definition: CapabilityDefinition,
    ) -> AdaptiveActionEstimate:
        """Return a bounded adjustment; eligibility remains controller-owned."""
        problem = state["structured_problem"]
        task_family = problem.problem_type if problem is not None else "unrepresented"
        profile = self.profile(
            task_family,
            candidate.action_type,
            candidate.capability,
            definition.version,
        )
        count = profile.sample_count
        confidence = count / (count + 5)
        joint_success = math.sqrt(
            profile.smoothed_operational_reliability * profile.smoothed_verified_yield
        )
        progress_multiplier = max(0.35, 1.0 - confidence * (1.0 - joint_success))
        latency_cost = min(0.5, profile.median_duration_ms / 60_000.0)
        # Calls already covered by the declared reservation are expected cost,
        # not evidence of degradation. Only observed use above the declaration
        # may add an empirical penalty.
        excess_model_calls = max(
            0.0,
            profile.average_model_calls - definition.max_model_calls,
        )
        excess_external_calls = max(
            0.0,
            profile.average_external_calls - definition.max_external_calls,
        )
        call_cost = min(
            0.5,
            (excess_model_calls * 0.15) + (excess_external_calls * 0.08),
        )
        token_cost = min(0.25, profile.average_total_tokens / 100_000.0)
        observed_cost_delta = max(
            0.0,
            profile.average_normalized_cost - definition.estimated_cost,
        )
        extra_cost = min(
            2.0,
            confidence * (latency_cost + call_cost + token_cost + observed_cost_delta),
        )
        return AdaptiveActionEstimate(
            sample_count=count,
            sample_confidence=confidence,
            progress_multiplier=progress_multiplier,
            extra_effective_cost=extra_cost,
            predicted_operational_reliability=profile.smoothed_operational_reliability,
            predicted_verified_yield=profile.smoothed_verified_yield,
            predicted_median_duration_ms=profile.median_duration_ms,
            rationale=(
                "No version-matched performance samples; retained declared capability estimate."
                if count == 0
                else (
                    f"Used {count} version-matched sample(s): operational reliability "
                    f"{profile.smoothed_operational_reliability:.3f}, verified yield "
                    f"{profile.smoothed_verified_yield:.3f}, median latency "
                    f"{profile.median_duration_ms:.1f} ms."
                )
            ),
        )

    def sample_count(self) -> int:
        return sum(len(items) for items in self._samples.values())
