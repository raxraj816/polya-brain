"""Route self-contained implementation tasks to lean-first differential verification."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import replace

from app.cognition.contracts import CognitiveRunStatus
from app.cognition.kernel import CognitiveRunResult
from app.cognition.task_model import CognitiveResourceBudget, budget_event
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.llm import LLMClient
from app.memory.failure_patterns import FailurePatternStore
from app.models.contracts import EvidenceItem, ReasoningMode
from app.verified_coding.pipeline import PipelineLimits, VerifiedCodingPipeline
from app.verified_coding.projection import project
from app.verified_coding.prompts import PROMPT_VERSION

logger = logging.getLogger(__name__)

ROUTE_VERSION = "verified_coding_route@0.1.0"
MAX_INPUT_CHARS = 8_000
MIN_MODEL_CALLS = 4

_REQUEST = re.compile(r"\b(implement|write|create|build|code)\b", re.IGNORECASE)
# A Python signature with a return annotation, e.g. ``first_slot(calendars: ...) -> int``.
_SIGNATURE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]|\([^()]*\)|\[[^\]]*\])*\)\s*->")
_CLASS_METHOD = re.compile(
    r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\s+with\s+(?:a\s+)?method\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
# Work that depends on the user's existing code or environment is investigation, not a
# self-contained implementation task.
_EXTERNAL = re.compile(
    r"\b(our|my|the existing|this)\s+(repo|repository|codebase|service|project|module|app)\b"
    r"|traceback|stack trace|\.py\b|pull request|production|deploy",
    re.IGNORECASE,
)


def route_reason(raw_input: str) -> str | None:
    """Return why the input qualifies for verified coding, or None."""
    text = raw_input.strip()
    if not text or len(text) > MAX_INPUT_CHARS or not _REQUEST.search(text):
        return None
    if _EXTERNAL.search(text):
        return None
    if _CLASS_METHOD.search(text):
        return "requested class method with a stated signature"
    match = _SIGNATURE.search(text)
    if match is not None:
        return f"requested function {match.group(1)} with a stated signature"
    return None


class VerifiedCodingFastPath:
    """Run the verified-coding pipeline in place of the kernel for qualifying input."""

    def __init__(
        self,
        client: LLMClient,
        model: str,
        *,
        image: str,
        memory_megabytes: int,
        budget: CognitiveResourceBudget,
        limits: PipelineLimits | None = None,
        sandbox_factory: Callable[[], DockerPythonSandbox] | None = None,
        patterns: FailurePatternStore | None = None,
    ) -> None:
        self._patterns = patterns
        self._client = client
        self._model = model
        self._budget = budget
        self._limits = limits or PipelineLimits()
        self._sandbox_factory = sandbox_factory or (
            lambda: DockerPythonSandbox(
                image=image,
                limits=DockerSandboxLimits(timeout_seconds=10, memory_megabytes=memory_megabytes),
            )
        )

    def accepts(self, raw_input: str, seed_evidence: list[EvidenceItem] | None) -> str | None:
        if seed_evidence:
            return None
        if self._budget.max_model_calls < MIN_MODEL_CALLS:
            return None
        return route_reason(raw_input)

    def _limits_for_budget(self) -> PipelineLimits:
        calls = self._budget.max_model_calls
        limits = self._limits
        # Reserve the oracle call(s) and at least one repair round inside the run budget.
        solve_calls = max(1, min(limits.solve_calls, calls - limits.oracle_attempts - 1))
        rounds = max(0, min(limits.repair_rounds, calls - solve_calls - limits.oracle_attempts))
        per_request = min(
            limits.per_request_output_tokens,
            max(1_000, self._budget.max_output_tokens // max(1, solve_calls + 2)),
        )
        return replace(
            limits,
            solve_calls=solve_calls,
            repair_rounds=rounds,
            per_request_output_tokens=per_request,
        )

    def __call__(
        self,
        raw_input: str,
        *,
        session_id: str | None,
        seed_evidence: list[EvidenceItem] | None,
        checkpoint: Callable[[PolyaState, bool], None] | None,
    ) -> CognitiveRunResult | None:
        reason = self.accepts(raw_input, seed_evidence)
        if reason is None:
            return None
        initial = create_initial_state(raw_input, session_id=session_id)
        prior = [
            budget_event(self._budget),
            StateEvent(
                engine_name="verified_coding",
                event_type="verified_coding_routed",
                reasoning_mode=ReasoningMode.EXPLORE,
                summary=(
                    "Routed to lean-first differential verification: solve once, then test the "
                    "result against an independent reference before delivering it."
                ),
                metadata={
                    "route_version": ROUTE_VERSION,
                    "prompt_version": PROMPT_VERSION,
                    "reason": reason,
                },
            ),
        ]
        published: list[StateEvent] = list(prior)

        def progress(event: dict[str, object]) -> None:
            published.append(StateEvent.model_validate(event))
            if checkpoint is not None:
                interim = dict(initial)
                interim["events"] = list(published)
                checkpoint(interim, True)  # type: ignore[arg-type]

        if checkpoint is not None:
            interim = dict(initial)
            interim["events"] = list(published)
            checkpoint(interim, True)  # type: ignore[arg-type]
        pipeline = VerifiedCodingPipeline(
            self._client,
            self._model,
            self._sandbox_factory(),
            limits=self._limits_for_budget(),
            progress=progress,
            patterns=self._patterns,
            source=str(initial["session_id"]),
        )
        try:
            outcome = pipeline.run(raw_input)
        except Exception as exc:
            # Progress may already be persisted, so falling back to the kernel would
            # break the append-only trace. Stop safely and say why instead.
            logger.exception("verified coding pipeline failed")
            failed = dict(initial)
            failed["events"] = [
                *published,
                StateEvent(
                    engine_name="verified_coding",
                    event_type="verified_coding_failed",
                    reasoning_mode=ReasoningMode.EXECUTE,
                    summary=(
                        "Verified coding stopped because sandbox or provider infrastructure "
                        f"failed ({type(exc).__name__}). No unverified code is delivered."
                    ),
                    metadata={"failure": type(exc).__name__},
                ),
            ]
            if checkpoint is not None:
                checkpoint(failed, False)  # type: ignore[arg-type]
            return CognitiveRunResult(
                status=CognitiveRunStatus.FAILED,
                state=failed,  # type: ignore[arg-type]
                decisions=(),
                observations=(),
                cycles=0,
            )
        status, state = project(
            outcome,
            raw_input=raw_input,
            session_id=initial["session_id"],
            prior_events=prior,
        )
        if checkpoint is not None:
            checkpoint(state, False)
        return CognitiveRunResult(
            status=status,
            state=state,
            decisions=(),
            observations=(),
            cycles=0,
        )
