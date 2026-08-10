"""Verified procedural memory for experimental cognitive-action transfer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.cognition.contracts import (
    CognitiveActionType,
    CognitiveRunStatus,
    LearnedActionPreference,
    ObservationStatus,
    ProceduralActionStrategy,
)

if TYPE_CHECKING:
    from app.cognition.kernel import CognitiveRunResult

_LEARNABLE_ACTIONS = {
    CognitiveActionType.CLARIFY,
    CognitiveActionType.REFRAME,
    CognitiveActionType.RECALL,
    CognitiveActionType.RETRIEVE_MEMORY,
    CognitiveActionType.SEARCH,
    CognitiveActionType.ASK_HUMAN,
    CognitiveActionType.INSPECT,
    CognitiveActionType.OBSERVE,
    CognitiveActionType.MEASURE,
    CognitiveActionType.CALCULATE,
    CognitiveActionType.COMPARE,
    CognitiveActionType.SIMULATE,
    CognitiveActionType.EXPERIMENT,
}


class ProceduralMemory:
    """In-memory proof store that learns no strategy without verification."""

    def __init__(self) -> None:
        self._strategies: dict[tuple[str, str], ProceduralActionStrategy] = {}

    def learn(self, result: CognitiveRunResult) -> list[ProceduralActionStrategy]:
        """Learn successful gap actions only from completed verified runs."""
        verification = result.state["verification"]
        if (
            result.status is not CognitiveRunStatus.COMPLETED
            or verification is None
            or not verification.passed
            or result.state["reflection"] is None
        ):
            return []

        problem = result.state["structured_problem"]
        if problem is None:
            return []

        successful_by_target = {
            decision.selected.target: decision.selected
            for decision, observation in zip(
                result.decisions,
                result.observations,
                strict=False,
            )
            if observation.status is ObservationStatus.SUCCEEDED
            and decision.selected.action_type in _LEARNABLE_ACTIONS
        }
        learned: list[ProceduralActionStrategy] = []
        for gap in result.state["gaps"]:
            if not gap.filled:
                continue
            selected = successful_by_target.get(gap.description)
            if selected is None:
                continue
            key = (problem.problem_type, gap.gap_type)
            existing = self._strategies.get(key)
            source_ids = list(
                dict.fromkeys(
                    [
                        *(existing.source_session_ids if existing is not None else []),
                        result.state["session_id"],
                    ]
                )
            )
            strategy = ProceduralActionStrategy(
                problem_type=problem.problem_type,
                gap_type=gap.gap_type,
                action_type=selected.action_type,
                capability=selected.capability,
                verified_successes=(existing.verified_successes + 1 if existing is not None else 1),
                verified_failures=(existing.verified_failures if existing is not None else 0),
                source_session_ids=source_ids,
            )
            self._strategies[key] = strategy
            learned.append(strategy)
        return learned

    def preference(
        self,
        problem_type: str,
        gap_type: str,
    ) -> LearnedActionPreference | None:
        """Return a verified action preference for the same structural gap."""
        strategy = self._strategies.get((problem_type, gap_type))
        if strategy is None:
            return None
        return LearnedActionPreference(
            action_type=strategy.action_type,
            capability=strategy.capability,
            source_session_ids=strategy.source_session_ids,
            verified_successes=strategy.verified_successes,
        )

    def strategies(self) -> list[ProceduralActionStrategy]:
        """Expose deterministic snapshots for audit and tests."""
        return [self._strategies[key] for key in sorted(self._strategies)]
