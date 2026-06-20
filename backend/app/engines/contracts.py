"""Chapter 7 engine interface contracts and telemetry wrapper."""

from __future__ import annotations

import logging
from enum import StrEnum
from time import perf_counter
from typing import Annotated, Any, Protocol

from pydantic import Field, JsonValue, ValidationError, model_validator

from app.graph.state import PolyaState, StateEvent, append_state_events
from app.models.contracts import ContractModel, NonEmptyStr, ReasoningMode, Score
from app.tracing.sanitization import sanitize_json_mapping, sanitize_text

logger = logging.getLogger("polyabrain.engines")

NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]


class EngineStatus(StrEnum):
    """Stage-gate status values shared by all PolyaBrain engines."""

    OK = "ok"
    NEEDS_INPUT = "needs_input"
    NEEDS_EVIDENCE = "needs_evidence"
    LOW_CONFIDENCE = "low_confidence"
    BLOCKED = "blocked"
    FAILED = "failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EngineRoute(StrEnum):
    """Route recommendations emitted by engines for Chapter 8 graph wiring."""

    CONTINUE = "continue"
    CLARIFY = "clarify"
    RESEARCH = "research"
    REFRAME = "reframe"
    REPLAN = "replan"
    RETRY_EXECUTION = "retry_execution"
    FINALIZE = "finalize"
    FINALIZE_INSUFFICIENT_EVIDENCE = "finalize_insufficient_evidence"


class TokenUsage(ContractModel):
    """Token usage reported by LLM-backed engines when available."""

    input_tokens: NonNegativeInt = 0
    output_tokens: NonNegativeInt = 0

    @property
    def total_tokens(self) -> int:
        """Return total tokens without storing redundant state."""
        return self.input_tokens + self.output_tokens


class EngineVersion(ContractModel):
    """Version metadata needed to reproduce an engine decision."""

    engine: NonEmptyStr
    prompt: NonEmptyStr | None = None
    model: NonEmptyStr | None = None
    tool: NonEmptyStr | None = None
    verifier: NonEmptyStr | None = None
    graph: NonEmptyStr | None = None


class EngineResult(ContractModel):
    """A typed engine outcome with enough metadata for routing and audit."""

    status: EngineStatus
    confidence: Score | None = None
    missing_inputs: list[NonEmptyStr] = Field(default_factory=list)
    recommended_route: EngineRoute
    duration_ms: NonNegativeFloat = 0.0
    errors: list[NonEmptyStr] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    versions: EngineVersion
    summary: NonEmptyStr

    @model_validator(mode="after")
    def outcome_must_be_stage_gated(self) -> EngineResult:
        """Reject outcomes that would let weak output continue silently."""
        if self.status is EngineStatus.OK:
            if self.confidence is None:
                raise ValueError("ok engine result requires confidence")
            if self.recommended_route is not EngineRoute.CONTINUE:
                raise ValueError("ok engine result must recommend continue")

        if self.status is EngineStatus.NEEDS_INPUT:
            if not self.missing_inputs:
                raise ValueError("needs_input engine result requires missing_inputs")
            if self.recommended_route is not EngineRoute.CLARIFY:
                raise ValueError("needs_input engine result must recommend clarify")

        if (
            self.status is EngineStatus.NEEDS_EVIDENCE
            and self.recommended_route is not EngineRoute.RESEARCH
        ):
            raise ValueError("needs_evidence engine result must recommend research")

        if (
            self.status in {EngineStatus.LOW_CONFIDENCE, EngineStatus.BLOCKED}
            and self.recommended_route is EngineRoute.CONTINUE
        ):
            raise ValueError(f"{self.status.value} engine result cannot recommend continue")

        if self.status is EngineStatus.FAILED:
            if not self.errors:
                raise ValueError("failed engine result requires at least one error")
            if self.recommended_route is EngineRoute.CONTINUE:
                raise ValueError("failed engine result cannot recommend continue")

        if (
            self.status is EngineStatus.INSUFFICIENT_EVIDENCE
            and self.recommended_route is not EngineRoute.FINALIZE_INSUFFICIENT_EVIDENCE
        ):
            raise ValueError(
                "insufficient_evidence engine result must recommend finalize_insufficient_evidence"
            )

        return self


class EngineRunOutput(ContractModel):
    """State delta plus the auditable result of one engine invocation."""

    state_delta: dict[str, Any] = Field(default_factory=dict)
    result: EngineResult

    @model_validator(mode="after")
    def state_delta_keys_must_match_polya_state(self) -> EngineRunOutput:
        """Reject misspelled or non-state delta keys before graph routing."""
        allowed_keys = set(PolyaState.__annotations__)
        invalid_keys = sorted(set(self.state_delta) - allowed_keys)
        if invalid_keys:
            raise ValueError(f"state_delta contains unknown PolyaState keys: {invalid_keys}")
        return self


class PolyaEngine(Protocol):
    """Synchronous interface every Chapter 7+ engine must implement."""

    name: str
    reasoning_mode: ReasoningMode
    version: EngineVersion

    def run(self, state: PolyaState) -> EngineRunOutput:
        """Run the engine against the current graph state."""
        ...


def engine_event_metadata(result: EngineResult) -> dict[str, JsonValue]:
    """Build JSON-compatible trace metadata for one engine result."""
    return sanitize_json_mapping(
        {
            "status": result.status.value,
            "recommended_route": result.recommended_route.value,
            "confidence": result.confidence,
            "missing_inputs": list(result.missing_inputs),
            "duration_ms": result.duration_ms,
            "errors": list(result.errors),
            "token_usage": {
                "input_tokens": result.token_usage.input_tokens,
                "output_tokens": result.token_usage.output_tokens,
                "total_tokens": result.token_usage.total_tokens,
            },
            "versions": result.versions.model_dump(mode="json"),
        }
    )


def _safe_engine_name(engine: PolyaEngine) -> str:
    """Return a non-empty engine name for failure-safe audit events."""
    try:
        name = engine.name.strip()
    except AttributeError:
        return "unknown_engine"
    return name or "unknown_engine"


def _safe_reasoning_mode(engine: PolyaEngine) -> ReasoningMode:
    """Return a valid reasoning mode even for malformed engine objects."""
    raw_reasoning_mode = getattr(engine, "reasoning_mode", None)
    if isinstance(raw_reasoning_mode, ReasoningMode):
        return raw_reasoning_mode
    if not isinstance(raw_reasoning_mode, str):
        return ReasoningMode.EXPLORE
    try:
        return ReasoningMode(raw_reasoning_mode)
    except ValueError:
        return ReasoningMode.EXPLORE


def _safe_engine_version(engine: PolyaEngine, engine_name: str) -> EngineVersion:
    """Return valid version metadata without trusting the engine object."""
    raw_version = getattr(engine, "version", None)
    if isinstance(raw_version, EngineVersion):
        return raw_version
    try:
        return EngineVersion.model_validate(raw_version)
    except ValidationError:
        return EngineVersion(engine=f"{engine_name}@unknown")


def _started_event(
    *,
    engine_name: str,
    reasoning_mode: ReasoningMode,
    version: EngineVersion,
    state: PolyaState,
) -> StateEvent:
    """Create the wrapper-owned start event for a run."""
    return StateEvent(
        engine_name=engine_name,
        event_type="started",
        reasoning_mode=reasoning_mode,
        summary=f"Started {engine_name}.",
        metadata={
            "status": "started",
            "session_id": state["session_id"],
            "versions": version.model_dump(mode="json"),
        },
    )


def _terminal_event(
    *,
    engine_name: str,
    reasoning_mode: ReasoningMode,
    result: EngineResult,
) -> StateEvent:
    """Create the wrapper-owned completion or failure event for a run."""
    return StateEvent(
        engine_name=engine_name,
        event_type="completed" if result.status is not EngineStatus.FAILED else "failed",
        reasoning_mode=reasoning_mode,
        summary=sanitize_text(result.summary),
        metadata=engine_event_metadata(result),
    )


def _result_with_duration(result: EngineResult, duration_ms: float) -> EngineResult:
    """Return a validated copy of a result with wrapper-owned duration."""
    return result.model_copy(update={"duration_ms": duration_ms})


def _state_delta_with_wrapper_events(
    state_delta: dict[str, Any],
    *,
    start_event: StateEvent,
    terminal_event: StateEvent,
) -> dict[str, Any]:
    """Return a state delta with wrapper events around engine-provided events."""
    updated_delta = dict(state_delta)
    existing_events = updated_delta.get("events")
    events_with_start = append_state_events(None, start_event)
    events_with_engine_events = append_state_events(events_with_start, existing_events)
    updated_delta["events"] = append_state_events(events_with_engine_events, terminal_event)
    return updated_delta


def run_engine(engine: PolyaEngine, state: PolyaState) -> EngineRunOutput:
    """Run an engine with telemetry, structured trace events, and failure capture."""
    started_at = perf_counter()
    engine_name = _safe_engine_name(engine)
    reasoning_mode = _safe_reasoning_mode(engine)
    version = _safe_engine_version(engine, engine_name)
    start_event = _started_event(
        engine_name=engine_name,
        reasoning_mode=reasoning_mode,
        version=version,
        state=state,
    )
    logger.info(
        "engine.started",
        extra={
            "engine_name": engine_name,
            "session_id": state["session_id"],
            "reasoning_mode": reasoning_mode.value,
            "versions": version.model_dump(mode="json"),
        },
    )

    try:
        output = engine.run(state)
        duration_ms = (perf_counter() - started_at) * 1000
        result = _result_with_duration(output.result, duration_ms)
        state_delta = _state_delta_with_wrapper_events(
            output.state_delta,
            start_event=start_event,
            terminal_event=_terminal_event(
                engine_name=engine_name,
                reasoning_mode=reasoning_mode,
                result=result,
            ),
        )
        logger.info(
            "engine.completed",
            extra={
                "engine_name": engine_name,
                "session_id": state["session_id"],
                **engine_event_metadata(result),
            },
        )
    except Exception as exc:  # pragma: no cover - tested through public wrapper behavior
        duration_ms = (perf_counter() - started_at) * 1000
        result = EngineResult(
            status=EngineStatus.FAILED,
            confidence=None,
            recommended_route=EngineRoute.FINALIZE,
            duration_ms=duration_ms,
            errors=[f"{type(exc).__name__}: {exc}"],
            versions=version,
            summary=f"{engine_name} failed before producing a valid result.",
        )
        state_delta = {}
        logger.error(
            "engine.failed",
            extra={
                "engine_name": engine_name,
                "session_id": state["session_id"],
                **engine_event_metadata(result),
            },
        )
        state_delta = _state_delta_with_wrapper_events(
            {},
            start_event=start_event,
            terminal_event=_terminal_event(
                engine_name=engine_name,
                reasoning_mode=reasoning_mode,
                result=result,
            ),
        )

    return EngineRunOutput(state_delta=state_delta, result=result)
