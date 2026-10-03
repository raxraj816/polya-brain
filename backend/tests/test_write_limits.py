"""Durable storage-write limits across real authenticated API transactions."""

import os
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session
from test_auth import identity_app as original_identity_app
from test_auth import sign_in

from app.api.routes.source_check import SourceCheckAvailability
from app.db.models import Artifact, HumanFeedback, utc_now

pytestmark = pytest.mark.skipif(
    os.environ.get("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)


@pytest.fixture
def identity_app():
    return original_identity_app.__wrapped__()


SOURCE = {
    "raw_input": "Fix the supplied function",
    "source_code": "def f(): return 1\n",
    "check_code": "assert f() == 2\n",
    "execution_approved": True,
    "provider_approved": True,
}


def available(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.source_check.availability",
        lambda settings: SourceCheckAvailability(
            available=True, reason="Local admission fixture; no execution"
        ),
    )


def test_session_creation_limit_preserves_history_and_rejects_another_write(identity_app):
    app, provider, alice, _ = identity_app
    app.state.settings = app.state.settings.model_copy(update={"daily_user_session_limit": 1})
    with sign_in(app, provider, alice) as client:
        first = client.post("/api/v1/sessions", json={"raw_input": "What is 17 * 6?"})
        assert first.status_code == 201
        second = client.post("/api/v1/sessions", json={"raw_input": "Another problem"})
        assert second.status_code == 429
        assert 1 <= int(second.headers["retry-after"]) <= 86400
        history = client.get("/api/v1/sessions").json()["sessions"]
        assert [s["id"] for s in history] == [first.json()["id"]]


def test_feedback_limit_preserves_saved_feedback_and_report(identity_app):
    app, provider, alice, _ = identity_app
    app.state.settings = app.state.settings.model_copy(update={"daily_user_feedback_limit": 1})
    with sign_in(app, provider, alice) as client:
        session_id = client.post("/api/v1/sessions", json={"raw_input": "What is 17 * 6?"}).json()[
            "id"
        ]
        assert client.post(f"/api/v1/sessions/{session_id}/run").status_code == 200
        path = f"/api/v1/sessions/{session_id}/feedback"
        first = client.post(path, json={"feedback_type": "useful", "correction": "Keep this"})
        assert first.status_code == 201
        second = client.post(path, json={"feedback_type": "wrong", "correction": "Retain in form"})
        assert second.status_code == 429
        assert int(second.headers["retry-after"]) > 0
        assert client.get(path).json() == [first.json()]
        assert client.get(f"/api/v1/sessions/{session_id}/report").status_code == 200


@pytest.mark.parametrize("source_first", [True, False])
def test_source_and_ordinary_creation_share_allowance_without_orphan_artifacts(
    identity_app, monkeypatch, source_first
):
    available(monkeypatch)
    app, provider, alice, _ = identity_app
    app.state.settings.daily_user_session_limit = 1
    routes = [("/api/v1/source-check", SOURCE), ("/api/v1/sessions", {"raw_input": "ordinary"})]
    if not source_first:
        routes.reverse()
    with sign_in(app, provider, alice) as client:
        assert client.post(routes[0][0], json=routes[0][1]).status_code == 201
        assert client.post(routes[1][0], json=routes[1][1]).status_code == 429
        ids = [UUID(s["id"]) for s in client.get("/api/v1/sessions").json()["sessions"]]
        assert len(ids) == 1
        with app.state.session_factory() as db:
            assert db.scalar(
                select(func.count()).select_from(Artifact).where(Artifact.session_id.in_(ids))
            ) == int(source_first)


def test_ownership_and_auth_checks_precede_closed_feedback_allowance(identity_app):
    app, provider, alice, bob = identity_app
    with sign_in(app, provider, alice) as client:
        session_id = client.post("/api/v1/sessions", json={"raw_input": "What is 17 * 6?"}).json()[
            "id"
        ]
        assert client.post(f"/api/v1/sessions/{session_id}/run").status_code == 200
        path = f"/api/v1/sessions/{session_id}/feedback"
        app.state.settings.daily_global_feedback_limit = 0
        with sign_in(app, provider, bob) as stranger:
            assert stranger.post(path, json={"feedback_type": "useful"}).status_code == 404
            assert stranger.get(path).status_code == 404
        with TestClient(app) as anonymous:
            assert anonymous.post(path, json={"feedback_type": "useful"}).status_code == 401
            assert anonymous.post("/api/v1/sessions", json={"raw_input": "New"}).status_code == 401
        assert client.post(path, json={"feedback_type": "useful"}).status_code == 429
        assert client.get(path).json() == []


def test_invalid_input_and_pending_session_do_not_consume_feedback_allowance(identity_app):
    app, provider, alice, _ = identity_app
    app.state.settings.daily_user_session_limit = 1
    app.state.settings.daily_user_feedback_limit = 1
    with sign_in(app, provider, alice) as client:
        assert client.post("/api/v1/sessions", json={"raw_input": ""}).status_code == 422
        session_id = client.post("/api/v1/sessions", json={"raw_input": "What is 17 * 6?"}).json()[
            "id"
        ]
        path = f"/api/v1/sessions/{session_id}/feedback"
        assert client.post(path, json={"feedback_type": "useful"}).status_code == 409
        assert client.post(f"/api/v1/sessions/{session_id}/run").status_code == 200
        assert client.post(path, json={"feedback_type": "invented"}).status_code == 422
        assert client.post(path, json={"feedback_type": "useful"}).status_code == 201


def test_lifetime_feedback_limit_reports_no_false_daily_reset(identity_app):
    app, provider, alice, _ = identity_app
    with sign_in(app, provider, alice) as client:
        session_id = client.post("/api/v1/sessions", json={"raw_input": "What is 17 * 6?"}).json()[
            "id"
        ]
        assert client.post(f"/api/v1/sessions/{session_id}/run").status_code == 200
        with app.state.session_factory() as db:
            db.add_all(
                [
                    HumanFeedback(
                        session_id=UUID(session_id),
                        feedback_type="useful",
                        created_at=utc_now() - timedelta(days=1),
                    )
                    for _ in range(100)
                ]
            )
            db.commit()
        path = f"/api/v1/sessions/{session_id}/feedback"
        response = client.post(path, json={"feedback_type": "useful"})
        assert response.status_code == 409
        assert "retry-after" not in response.headers
        assert "100 records" in response.json()["detail"]
        assert len(client.get(path).json()) == 100


def test_failed_source_transaction_rolls_back_both_record_and_allowance(identity_app, monkeypatch):
    available(monkeypatch)
    app, provider, alice, _ = identity_app
    app.state.settings.daily_user_session_limit = 1
    with sign_in(app, provider, alice) as client:

        def fail_commit(db):
            if any(isinstance(record, Artifact) for record in db.new):
                raise RuntimeError("Injected artifact commit failure")

        event.listen(Session, "before_commit", fail_commit)
        try:
            with pytest.raises(RuntimeError, match="Injected artifact"):
                client.post("/api/v1/source-check", json=SOURCE)
        finally:
            event.remove(Session, "before_commit", fail_commit)
        assert client.get("/api/v1/sessions").json()["sessions"] == []
        response = client.post("/api/v1/source-check", json=SOURCE)
        assert response.status_code == 201, response.text
        assert len(client.get("/api/v1/sessions").json()["sessions"]) == 1
