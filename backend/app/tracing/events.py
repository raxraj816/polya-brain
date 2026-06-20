"""Pure trace event preparation for persistence and API exposure."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import JsonValue

from app.graph.state import StateEvent
from app.models.contracts import ReasoningMode
from app.tracing.sanitization import sanitize_json_mapping_with_count, sanitize_text_with_count

TERMINAL_ENGINE_EVENT_TYPES = {"completed", "failed"}
ROUTE_DECISION_EVENT_TYPE = "route_decision"
GRAPH_ROUTER_ENGINE_NAME = "graph_router"


@dataclass(frozen=True)
class TraceEventWrite:
    """Trace event data ready to be written to durable storage."""

    sequence_number: int
    engine_name: str
    event_type: str
    reasoning_mode: ReasoningMode
    summary: str
    metadata: dict[str, JsonValue]
    redaction_count: int


def _sanitize_event(
    event: StateEvent,
    *,
    sequence_number: int,
) -> TraceEventWrite:
    sanitized_summary = sanitize_text_with_count(event.summary)
    sanitized_metadata, metadata_redactions = sanitize_json_mapping_with_count(event.metadata)
    return TraceEventWrite(
        sequence_number=sequence_number,
        engine_name=event.engine_name,
        event_type=event.event_type,
        reasoning_mode=event.reasoning_mode,
        summary=sanitized_summary.value,
        metadata=sanitized_metadata,
        redaction_count=sanitized_summary.redaction_count + metadata_redactions,
    )


def _route_decision_for_event(
    event: StateEvent,
    *,
    next_event: StateEvent | None,
    sequence_number: int,
) -> TraceEventWrite | None:
    if event.engine_name == GRAPH_ROUTER_ENGINE_NAME:
        return None
    if event.event_type not in TERMINAL_ENGINE_EVENT_TYPES:
        return None

    status = event.metadata.get("status")
    recommended_route = event.metadata.get("recommended_route")
    if not isinstance(status, str) or not isinstance(recommended_route, str):
        return None

    next_metadata: dict[str, JsonValue] = {}
    if next_event is not None:
        next_metadata = {
            "next_engine_name": next_event.engine_name,
            "next_event_type": next_event.event_type,
        }

    metadata: dict[str, JsonValue] = {
        "source_engine": event.engine_name,
        "source_event_type": event.event_type,
        "status": status,
        "recommended_route": recommended_route,
        **next_metadata,
    }
    sanitized_summary = sanitize_text_with_count(
        f"Routed {event.engine_name} after {status} with {recommended_route} recommendation."
    )
    sanitized_metadata, metadata_redactions = sanitize_json_mapping_with_count(metadata)
    return TraceEventWrite(
        sequence_number=sequence_number,
        engine_name=GRAPH_ROUTER_ENGINE_NAME,
        event_type=ROUTE_DECISION_EVENT_TYPE,
        reasoning_mode=ReasoningMode.COMPARE,
        summary=sanitized_summary.value,
        metadata=sanitized_metadata,
        redaction_count=sanitized_summary.redaction_count + metadata_redactions,
    )


def prepare_trace_event_writes(
    events: list[StateEvent],
    *,
    start_sequence_number: int = 0,
) -> list[TraceEventWrite]:
    """Prepare sanitized trace writes with deterministic route-decision events."""
    if start_sequence_number < 0:
        raise ValueError("start_sequence_number must be non-negative")

    writes: list[TraceEventWrite] = []
    next_sequence_number = start_sequence_number
    for index, event in enumerate(events):
        writes.append(_sanitize_event(event, sequence_number=next_sequence_number))
        next_sequence_number += 1

        route_decision = _route_decision_for_event(
            event,
            next_event=events[index + 1] if index + 1 < len(events) else None,
            sequence_number=next_sequence_number,
        )
        if route_decision is not None:
            writes.append(route_decision)
            next_sequence_number += 1

    return writes
