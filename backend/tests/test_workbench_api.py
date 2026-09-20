"""Exercise the workbench against real persistence and the shared runtime."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_sessions_service import awaiting_runner

from app.config import Settings, get_settings
from app.db.models import ProblemSession, ReasoningEvent
from app.main import create_app
from app.models.contracts import ProductMode
from app.sessions.service import PolyaSessionService

pytestmark = pytest.mark.skipif(
    os.environ.get("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)


@pytest.fixture
def client():
    app = create_app(
        Settings(
            _env_file=None,
            DATABASE_URL=get_settings().database_url,
            OPENROUTER_API_KEY="",
            OPENROUTER_MODEL="",
            SEARCH_API_KEY="",
            SEARCH_PROVIDER="",
        )
    )
    with TestClient(app) as test_client:
        yield test_client


def test_history_search_is_literal_paginated_and_filtered(client: TestClient) -> None:
    marker = f"workbench-{uuid4()}%_"
    ids = [
        client.post("/api/v1/sessions", json={"raw_input": f"{marker} item {index}"}).json()["id"]
        for index in range(3)
    ]
    first = client.get("/api/v1/sessions", params={"q": marker, "limit": 2}).json()
    assert first["has_more"] is True
    second = client.get(
        "/api/v1/sessions", params={"q": marker, "limit": 2, "offset": first["next_offset"]}
    ).json()
    assert second["has_more"] is False
    assert {s["id"] for s in first["sessions"] + second["sessions"]} == set(ids)
    assert (
        client.get("/api/v1/sessions", params={"q": marker, "status": "completed"}).json()[
            "sessions"
        ]
        == []
    )
    assert client.get("/api/v1/sessions?limit=101").status_code == 422


def test_real_run_exposes_artifacts_and_unique_incremental_trace(client: TestClient) -> None:
    session_id = client.post("/api/v1/sessions", json={"raw_input": "What is 17 * 6?"}).json()["id"]
    observed_before_final_save = []
    factory = client.app.state.session_factory
    # Each progress commit can be read by another database session before final artifacts.
    from app.tracing.persistence import SQLAlchemyTraceRepository

    original = SQLAlchemyTraceRepository.persist_events

    def observe(self, *, session_id, events):
        with factory() as db:
            existing = list(
                db.scalars(select(ReasoningEvent).where(ReasoningEvent.session_id == session_id))
            )
            status = db.get(ProblemSession, session_id).status
            if existing and status == "running":
                observed_before_final_save.append(len(existing))
        return original(self, session_id=session_id, events=events)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(SQLAlchemyTraceRepository, "persist_events", observe)
        response = client.post(f"/api/v1/sessions/{session_id}/run")
    assert response.status_code == 200, response.text
    assert response.json()["verification_status"] == "passed"
    assert observed_before_final_save
    events = client.get(f"/api/v1/sessions/{session_id}/events?limit=500").json()["events"]
    assert response.json()["event_count"] == len(events)
    sequences = [e["sequence_number"] for e in events]
    assert sequences == list(range(sequences[0], sequences[0] + len(events)))
    # Cumulative checkpoint slices must not duplicate completed capability events.
    signatures = [(e["event_type"], e["summary"], str(e["metadata"])) for e in events]
    assert len(signatures) == len(set(signatures))
    artifacts = client.get(f"/api/v1/sessions/{session_id}/artifacts")
    assert artifacts.status_code == 200, artifacts.text
    assert artifacts.json()["structured_problem"]
    assert artifacts.json()["evidence"]
    report = client.get(f"/api/v1/sessions/{session_id}/report").json()
    assert "102" in report["final_conclusion"]
    assert report["checks_performed"]
    assert client.post(f"/api/v1/sessions/{session_id}/run").status_code == 409


def test_pending_questions_survive_a_new_request(client: TestClient) -> None:
    with client.app.state.session_factory() as db:
        service = PolyaSessionService(db, runner=awaiting_runner)
        session = service.create_session(
            raw_input="Investigate this issue.", mode=ProductMode.INVESTIGATE, domain=None
        )
        session_id = session.id
        service.run_session(session_id)
    response = client.get(f"/api/v1/sessions/{session_id}/report")
    assert response.status_code == 200
    assert "Which measurable success criterion should be used?" in response.json()["open_questions"]


def test_missing_artifacts_returns_404(client: TestClient) -> None:
    assert client.get(f"/api/v1/sessions/{uuid4()}/artifacts").status_code == 404


def test_feedback_is_persisted_for_manual_review_without_changing_conclusion(
    client: TestClient,
) -> None:
    session_id = client.post("/api/v1/sessions", json={"raw_input": "What is 9 + 4?"}).json()["id"]
    assert (
        client.post(
            f"/api/v1/sessions/{session_id}/feedback", json={"feedback_type": "wrong"}
        ).status_code
        == 409
    )
    assert client.post(f"/api/v1/sessions/{session_id}/run").status_code == 200
    before = client.get(f"/api/v1/sessions/{session_id}/report").json()
    saved = client.post(
        f"/api/v1/sessions/{session_id}/feedback",
        json={"feedback_type": "incomplete", "correction": "Show an additional independent check."},
    )
    assert saved.status_code == 201
    feedback = client.get(f"/api/v1/sessions/{session_id}/feedback").json()
    assert feedback[0]["correction"] == "Show an additional independent check."
    review = client.get("/api/v1/sessions?feedback_type=incomplete").json()
    assert session_id in {s["id"] for s in review["sessions"]}
    assert client.get(f"/api/v1/sessions/{session_id}/report").json() == before
    assert (
        client.post(
            f"/api/v1/sessions/{session_id}/feedback", json={"feedback_type": "verified"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/sessions/{session_id}/feedback",
            json={"feedback_type": "wrong", "correction": "x" * 10001},
        ).status_code
        == 422
    )


@pytest.mark.parametrize("mode", ["compare", "review"])
def test_api_composer_preserves_persisted_mode_and_domain(client: TestClient, mode: str) -> None:
    session = client.post(
        "/api/v1/sessions",
        json={"raw_input": "What is 5 + 3?", "mode": mode, "domain": "quantity_check"},
    ).json()
    result = client.post(f"/api/v1/sessions/{session['id']}/run")
    assert result.status_code == 200, result.text
    events = client.get(f"/api/v1/sessions/{session['id']}/events?limit=500").json()["events"]
    approach = next(e for e in events if e["event_type"] == "approach_selected")
    assert approach["metadata"]["selected_mode"] == mode
    artifacts = client.get(f"/api/v1/sessions/{session['id']}/artifacts").json()
    assert artifacts["structured_problem"]["domain"] == "quantity_check"


def test_null_in_generated_claim_survives_real_trace_persistence(client: TestClient):
    from uuid import UUID

    from app.graph.state import StateEvent
    from app.models.contracts import ReasoningMode
    from app.tracing.persistence import SQLAlchemyTraceRepository

    sid = client.post("/api/v1/sessions", json={"raw_input": "Inspect measurement text."}).json()[
        "id"
    ]
    with client.app.state.session_factory() as db:
        repository = SQLAlchemyTraceRepository(db)
        repository.persist_events(
            session_id=UUID(sid),
            events=[
                StateEvent(
                    engine_name="evidence_evaluator",
                    event_type="evidence_evaluation_completed",
                    reasoning_mode=ReasoningMode.COMPARE,
                    summary="Observed \x00 in generated text.",
                    metadata={"assessments": [{"extracted_claim": "Value \x0033.24 min ± 1.4 s."}]},
                )
            ],
        )
        db.commit()
    response = client.get(f"/api/v1/sessions/{sid}/events")
    assert response.status_code == 200
    event = response.json()["events"][-1]
    assert event["summary"] == r"Observed \u0000 in generated text."
    assert (
        event["metadata"]["assessments"][0]["extracted_claim"] == r"Value \u000033.24 min ± 1.4 s."
    )


def test_generated_null_claim_can_be_admitted_and_persisted_without_changing_source(
    client: TestClient,
):
    from uuid import UUID

    from app.acquisition.contracts import EvidenceCandidateAssessment
    from app.cognition.persistence import SQLAlchemyCognitiveStateRepository
    from app.graph.state import create_initial_state
    from app.models.contracts import EvidenceItem

    sid = client.post("/api/v1/sessions", json={"raw_input": "Inspect source measurement."}).json()[
        "id"
    ]
    assessment = EvidenceCandidateAssessment(
        candidate_id="test",
        extracted_claim="Value \x0033.24 min.",
        relationship="supports",
        relevance_score=1,
        reliability_score=0.9,
        temporal_validity="timeless",
        contradiction_risk=0,
        rationale="Source compared.",
    )
    state = create_initial_state("Inspect source measurement.", session_id=sid)
    source = "Source reports a 33.24 minute change."
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_web_source",
            source_uri="https://example.org/source",
            claim=assessment.extracted_claim,
            raw_excerpt=source,
        )
    ]
    with client.app.state.session_factory() as db:
        repository = SQLAlchemyCognitiveStateRepository(db)
        repository.persist_state(session_id=UUID(sid), state=state)
        db.commit()
        evidence = repository.load_evidence(UUID(sid))[0]
    assert evidence.claim == r"Value \u000033.24 min."
    assert evidence.raw_excerpt == source
