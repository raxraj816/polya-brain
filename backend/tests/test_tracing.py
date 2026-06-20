"""Chapter 9 trace preparation, sanitization, and API tests."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.events import get_trace_repository
from app.config import Settings
from app.db.models import ReasoningEvent
from app.engines import (
    EngineResult,
    EngineRoute,
    EngineRunOutput,
    EngineStatus,
    EngineVersion,
    run_engine,
)
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.main import create_app
from app.models.contracts import ReasoningMode
from app.tracing import REDACTED, prepare_trace_event_writes, sanitize_json_mapping


def event(
    *,
    engine_name: str = "problem_representation",
    event_type: str = "started",
    reasoning_mode: ReasoningMode = ReasoningMode.EXPLORE,
    summary: str = "Trace event.",
    metadata: dict[str, object] | None = None,
) -> StateEvent:
    return StateEvent.model_validate(
        {
            "engine_name": engine_name,
            "event_type": event_type,
            "reasoning_mode": reasoning_mode,
            "summary": summary,
            "metadata": metadata or {},
        }
    )


def persisted_event(
    *,
    session_id: UUID,
    sequence_number: int,
    event_type: str,
    metadata: dict[str, object] | None = None,
) -> ReasoningEvent:
    return ReasoningEvent(
        id=uuid4(),
        session_id=session_id,
        sequence_number=sequence_number,
        engine_name="problem_representation",
        event_type=event_type,
        reasoning_mode="explore",
        summary=f"{event_type} event.",
        event_metadata=metadata or {},
        created_at=datetime(2026, 6, 20, 12, sequence_number, tzinfo=UTC),
    )


def test_trace_sanitization_redacts_secret_keys_and_values() -> None:
    sanitized = sanitize_json_mapping(
        {
            "api_key": "sk-proj-secret1234567890",
            "nested": {
                "Authorization": "Bearer abc.def-123",
                "safe": "keep this",
                "notes": ["token is Bearer xyz987", "ordinary value"],
            },
        }
    )

    assert sanitized["api_key"] == REDACTED
    assert sanitized["nested"] == {
        "Authorization": REDACTED,
        "safe": "keep this",
        "notes": [f"token is {REDACTED}", "ordinary value"],
    }


def test_prepare_trace_event_writes_orders_events_and_route_decisions() -> None:
    writes = prepare_trace_event_writes(
        [
            event(event_type="started"),
            event(
                event_type="completed",
                summary="Completed with Bearer secret-value.",
                metadata={
                    "status": "ok",
                    "recommended_route": "continue",
                    "token": "do-not-store",
                },
            ),
            event(engine_name="constraint_discovery", event_type="started"),
        ],
        start_sequence_number=4,
    )

    assert [write.sequence_number for write in writes] == [4, 5, 6, 7]
    assert [write.event_type for write in writes] == [
        "started",
        "completed",
        "route_decision",
        "started",
    ]
    assert writes[1].summary == f"Completed with {REDACTED}"
    assert writes[1].metadata["token"] == REDACTED
    assert writes[2].engine_name == "graph_router"
    assert writes[2].reasoning_mode is ReasoningMode.COMPARE
    assert writes[2].metadata["source_engine"] == "problem_representation"
    assert writes[2].metadata["next_engine_name"] == "constraint_discovery"


class SecretFailingEngine:
    name = "execution"
    reasoning_mode = ReasoningMode.EXECUTE
    version = EngineVersion(engine="execution@0.1.0", graph="polya_graph@0.1.0")

    def run(self, state: PolyaState) -> EngineRunOutput:
        del state
        return EngineRunOutput(
            state_delta={},
            result=EngineResult(
                status=EngineStatus.FAILED,
                confidence=None,
                recommended_route=EngineRoute.FINALIZE,
                errors=["OpenAI key sk-proj-abcdefghijklmnopqrstuvwxyz leaked upstream"],
                versions=self.version,
                summary="Execution saw Bearer abc.def secret.",
            ),
        )


class SecretRaisingEngine:
    name = "execution"
    reasoning_mode = ReasoningMode.EXECUTE
    version = EngineVersion(engine="execution@0.1.0", graph="polya_graph@0.1.0")

    def run(self, state: PolyaState) -> EngineRunOutput:
        del state
        raise RuntimeError("provider returned sk-proj-abcdefghijklmnopqrstuvwxyz")


def test_run_engine_redacts_terminal_event_summary_and_metadata() -> None:
    output = run_engine(
        SecretFailingEngine(),
        create_initial_state("Investigate secret handling."),
    )

    terminal_event = output.state_delta["events"][-1]
    assert terminal_event.summary == f"Execution saw {REDACTED} secret."
    assert terminal_event.metadata["errors"] == [f"OpenAI key {REDACTED} leaked upstream"]


def test_run_engine_logs_sanitized_failures_without_raw_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="polyabrain.engines")

    output = run_engine(
        SecretRaisingEngine(),
        create_initial_state("Investigate secret exception handling."),
    )

    assert output.result.status is EngineStatus.FAILED
    assert "sk-proj-abcdefghijklmnopqrstuvwxyz" not in caplog.text
    failure_records = [record for record in caplog.records if record.message == "engine.failed"]
    assert len(failure_records) == 1
    assert failure_records[0].exc_info is None
    assert failure_records[0].errors == [f"RuntimeError: provider returned {REDACTED}"]


class FakeTraceReader:
    def __init__(self, events: list[ReasoningEvent] | None) -> None:
        self.events = events

    def list_events(self, session_id: UUID) -> list[ReasoningEvent] | None:
        del session_id
        return self.events


def test_trace_events_endpoint_returns_ordered_sanitized_events() -> None:
    session_id = uuid4()
    app = create_app(Settings(POLYABRAIN_ENV="test"))
    app.dependency_overrides[get_trace_repository] = lambda: FakeTraceReader(
        [
            persisted_event(
                session_id=session_id,
                sequence_number=0,
                event_type="started",
                metadata={"safe": "yes"},
            ),
            persisted_event(
                session_id=session_id,
                sequence_number=1,
                event_type="completed",
                metadata={"authorization": "Bearer secret-token"},
            ),
        ]
    )
    client = TestClient(app)

    response = client.get(f"/api/v1/sessions/{session_id}/events")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == str(session_id)
    assert [event["sequence_number"] for event in payload["events"]] == [0, 1]
    assert payload["events"][0]["metadata"] == {"safe": "yes"}
    assert payload["events"][1]["metadata"] == {"authorization": REDACTED}


def test_trace_events_endpoint_returns_404_for_missing_session() -> None:
    session_id = uuid4()
    app = create_app(Settings(POLYABRAIN_ENV="test"))
    app.dependency_overrides[get_trace_repository] = lambda: FakeTraceReader(None)
    client = TestClient(app)

    response = client.get(f"/api/v1/sessions/{session_id}/events")

    assert response.status_code == 404
