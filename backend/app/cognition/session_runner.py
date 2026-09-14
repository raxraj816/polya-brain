"""Persisted-session adapter for the raw-input cognitive runtime."""

from __future__ import annotations

from collections.abc import Callable

from app.cognition.contracts import CognitiveRunStatus
from app.cognition.runtime import CognitiveRuntime
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import EvidenceItem
from app.sessions.service import SessionExecutionResult


class CognitiveSessionRunner:
    """Translate cognitive terminal states into session-service dispositions."""

    def __init__(
        self,
        runtime: CognitiveRuntime,
        *,
        max_cycles: int = 12,
        evidence_loader: Callable[[str], list[EvidenceItem]] | None = None,
        progress_writer: Callable[[str, list[StateEvent]], None] | None = None,
    ) -> None:
        if max_cycles < 1:
            raise ValueError("max_cycles must be at least 1")
        self._runtime = runtime
        self._max_cycles = max_cycles
        self._evidence_loader = evidence_loader
        self._progress_writer = progress_writer

    def __call__(self, raw_input: str, *, session_id: str) -> SessionExecutionResult:
        persisted = 0

        def publish(state: PolyaState, in_flight: bool) -> None:
            nonlocal persisted
            if self._progress_writer is not None:
                self._progress_writer(session_id, state["events"][persisted:])
                persisted = len(state["events"])

        result = self._runtime.run_problem(
            raw_input,
            session_id=session_id,
            max_cycles=self._max_cycles,
            seed_evidence=(self._evidence_loader(session_id) if self._evidence_loader else None),
            checkpoint=publish if self._progress_writer is not None else None,
        )
        if result.status is CognitiveRunStatus.NEEDS_INPUT:
            questions: list[str] = []
            for observation in reversed(result.observations):
                questions.extend(observation.proposed_update.questions_to_ask)
                if questions:
                    break
            if not questions:
                questions = ["What missing information should PolyaBrain use before continuing?"]
            return SessionExecutionResult(
                state=result.state,
                awaiting_user_input=True,
                clarifying_questions=tuple(dict.fromkeys(questions)),
                persisted_event_count=persisted,
            )

        state: PolyaState = result.state
        if state["final_answer"] is None:
            next_state = dict(state)
            next_state["final_answer"] = (
                "PolyaBrain stopped without a verified conclusion. "
                f"Terminal status: {result.status.value}."
            )
            state = next_state  # type: ignore[assignment]
        return SessionExecutionResult(state=state, persisted_event_count=persisted)
