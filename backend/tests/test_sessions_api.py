"""Chapter 10 session API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.routes.sessions import get_session_service
from app.config import Settings
from app.db.models import ProblemSession, ReasoningEvent
from app.main import create_app
from app.models.contracts import ProductMode
from app.sessions import SessionConflictError, SessionNotFoundError
from app.sessions.service import SessionRunResult


def problem_session(
    *,
    session_id: UUID | None = None,
    raw_input: str = "Investigate latency.",
    mode: str = "investigate",
    domain: str | None = "software_debugging",
    status: str = "created",
    final_answer: str | None = None,
    verification_status: str | None = None,
) -> ProblemSession:
    return ProblemSession(
        id=session_id or uuid4(),
        raw_input=raw_input,
        mode=mode,
        domain=domain,
        status=status,
        created_at=datetime(2026, 6, 20, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 6, 20, 12, 1, tzinfo=UTC) if status == "completed" else None,
        final_answer=final_answer,
        confidence=None,
        verification_status=verification_status,
    )


class FakeSessionService:
    def __init__(self) -> None:
        self.sessions: dict[UUID, ProblemSession] = {}
        self.event_count = 0

    def create_session(
        self,
        *,
        raw_input: str,
        mode: ProductMode,
        domain: str | None,
    ) -> ProblemSession:
        session = problem_session(raw_input=raw_input, mode=mode.value, domain=domain)
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: UUID) -> ProblemSession:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise SessionNotFoundError(f"problem session not found: {session_id}") from exc

    def run_session(self, session_id: UUID) -> SessionRunResult:
        session = self.get_session(session_id)
        if session.status != "created":
            raise SessionConflictError(
                f"problem session {session_id} is {session.status}, not created"
            )
        session.status = "completed"
        session.completed_at = datetime(2026, 6, 20, 12, 2, tzinfo=UTC)
        session.final_answer = "Chapter 10 API shell completed a deterministic stub Polya loop."
        session.verification_status = "stub_passed"
        self.event_count = 24
        return SessionRunResult(session=session, event_count=self.event_count)


def client_with_service(service: FakeSessionService) -> TestClient:
    app = create_app(Settings(POLYABRAIN_ENV="test"))
    app.dependency_overrides[get_session_service] = lambda: service
    return TestClient(app)


def test_create_session_returns_created_session() -> None:
    service = FakeSessionService()
    client = client_with_service(service)

    response = client.post(
        "/api/v1/sessions",
        json={
            "raw_input": "  Investigate why p95 latency jumped after deploy.  ",
            "mode": "investigate",
            "domain": "software_debugging",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["raw_input"] == "Investigate why p95 latency jumped after deploy."
    assert payload["mode"] == "investigate"
    assert payload["domain"] == "software_debugging"
    assert payload["status"] == "created"
    assert payload["completed_at"] is None


def test_create_session_rejects_blank_raw_input() -> None:
    client = client_with_service(FakeSessionService())

    response = client.post("/api/v1/sessions", json={"raw_input": "   "})

    assert response.status_code == 422


def test_create_session_rejects_invalid_mode() -> None:
    client = client_with_service(FakeSessionService())

    response = client.post(
        "/api/v1/sessions",
        json={"raw_input": "Investigate latency.", "mode": "chat"},
    )

    assert response.status_code == 422


def test_get_session_returns_existing_session() -> None:
    service = FakeSessionService()
    session = problem_session(raw_input="Read me.")
    service.sessions[session.id] = session
    client = client_with_service(service)

    response = client.get(f"/api/v1/sessions/{session.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(session.id)
    assert response.json()["raw_input"] == "Read me."


def test_get_session_returns_404_for_missing_session() -> None:
    client = client_with_service(FakeSessionService())

    response = client.get(f"/api/v1/sessions/{uuid4()}")

    assert response.status_code == 404


def test_run_session_completes_created_session() -> None:
    service = FakeSessionService()
    session = problem_session()
    service.sessions[session.id] = session
    client = client_with_service(service)

    response = client.post(f"/api/v1/sessions/{session.id}/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["event_count"] == 24
    assert payload["verification_status"] == "stub_passed"
    assert payload["final_answer"].startswith("Chapter 10 API shell completed")


def test_run_session_returns_404_for_missing_session() -> None:
    client = client_with_service(FakeSessionService())

    response = client.post(f"/api/v1/sessions/{uuid4()}/run")

    assert response.status_code == 404


def test_run_session_returns_409_for_already_completed_session() -> None:
    service = FakeSessionService()
    session = problem_session(status="completed", final_answer="Already done.")
    service.sessions[session.id] = session
    client = client_with_service(service)

    response = client.post(f"/api/v1/sessions/{session.id}/run")

    assert response.status_code == 409


class FakeTraceReader:
    def __init__(self, events: list[ReasoningEvent]) -> None:
        self.events = events

    def list_events(self, session_id: UUID) -> list[ReasoningEvent]:
        del session_id
        return self.events


def test_trace_endpoint_can_read_ordered_events_after_run() -> None:
    from app.api.routes.events import get_trace_repository

    service = FakeSessionService()
    session = problem_session()
    service.sessions[session.id] = session
    events = [
        ReasoningEvent(
            id=uuid4(),
            session_id=session.id,
            sequence_number=0,
            engine_name="problem_representation",
            event_type="started",
            reasoning_mode="explore",
            summary="Started problem representation.",
            event_metadata={},
            created_at=datetime(2026, 6, 20, 12, 0, tzinfo=UTC),
        ),
        ReasoningEvent(
            id=uuid4(),
            session_id=session.id,
            sequence_number=1,
            engine_name="problem_representation",
            event_type="completed",
            reasoning_mode="explore",
            summary="Completed problem representation.",
            event_metadata={"status": "ok"},
            created_at=datetime(2026, 6, 20, 12, 1, tzinfo=UTC),
        ),
    ]
    app = create_app(Settings(POLYABRAIN_ENV="test"))
    app.dependency_overrides[get_session_service] = lambda: service
    app.dependency_overrides[get_trace_repository] = lambda: FakeTraceReader(events)
    client = TestClient(app)

    run_response = client.post(f"/api/v1/sessions/{session.id}/run")
    trace_response = client.get(f"/api/v1/sessions/{session.id}/events")

    assert run_response.status_code == 200
    assert trace_response.status_code == 200
    payload = trace_response.json()
    assert [event["sequence_number"] for event in payload["events"]] == [0, 1]
