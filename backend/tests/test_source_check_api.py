"""Browser snapshot admission, immutable execution, and candidate review."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes.source_check import availability
from app.auth import require_principal
from app.config import Settings, get_settings
from app.db.models import Artifact, PlanTask
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.main import create_app
from app.sessions.source_check import SourceCheckRequest, input_metadata, validated_input

SOURCE = "\n\ndef total(count, unit_price):\n    return count + unit_price\n\n"
CHECK = "def verify(implementation):\n    assert implementation.total(3, 7) == 21\n    assert implementation.total(0, 7) == 0\n"


def payload(**changes):
    return {
        "raw_input": "Investigate incorrect totals and propose a small verified edit.",
        "source_code": SOURCE,
        "check_code": CHECK,
        "execution_approved": True,
        "provider_approved": True,
        **changes,
    }


def test_admission_preserves_exact_bytes_and_rejects_changed_hashes():
    request = SourceCheckRequest(**payload())
    assert request.source_code == SOURCE
    assert request.check_code == CHECK
    metadata = input_metadata(request)
    assert validated_input(metadata) == request
    metadata["source_code"] += "# changed\n"
    with pytest.raises(ValueError, match="changed after admission"):
        validated_input(metadata)


@pytest.mark.parametrize(
    "changes",
    [
        {"execution_approved": False},
        {"execution_approved": 1},
        {"provider_approved": "true"},
        {"provider_approved": False},
        {"source_code": " "},
        {"check_code": "x" * 18001},
        {"source_code": 'key="sk-proj-abcdefghijklmnopqrstuv"\n'},
        {"source_code": "\x00"},
    ],
)
def test_admission_rejects_missing_consent_and_unusable_snapshots(changes):
    with pytest.raises(ValueError):
        SourceCheckRequest(**payload(**changes))


class DynamicProposal(FakeLLMClient):
    def __init__(self, replacement="count * unit_price"):
        super().__init__([])
        self.replacement = replacement
        self.source_path = None

    def complete(self, request):
        self.requests.append(request)
        content = "\n".join(message.content for message in request.messages)
        source = re.search(r'file://[^"\s]+/source\.py', content).group(0)
        check = re.search(r'file://[^"\s]+/check\.py', content).group(0)
        self.source_path = Path(source.removeprefix("file://"))
        return LLMResponse(
            provider="fake",
            model="test-model",
            text=json.dumps(
                {
                    "diagnosis": "total adds count and unit_price instead of multiplying them.",
                    "implicated_source_uri": source,
                    "old_text": "count + unit_price",
                    "new_text": self.replacement,
                    "correction_rationale": "Multiply units by price.",
                    "regression_check_uri": check,
                    "regression_check_summary": "Check three and zero units.",
                    "remaining_uncertainty": ["Only the supplied examples are covered."],
                }
            ),
            finish_reason="stop",
            usage=LLMTokenUsage(input_tokens=100, output_tokens=120),
        )


@pytest.fixture
def client():
    if os.environ.get("POLYABRAIN_RUN_DB_TESTS") != "1":
        pytest.skip("requires migrated Postgres")
    settings = Settings(
        _env_file=None,
        DATABASE_URL=get_settings().database_url,
        OPENROUTER_API_KEY="fake-test-provider",
        OPENROUTER_MODEL="test-model",
        SEARCH_API_KEY="",
        SEARCH_PROVIDER="",
        CODE_EXECUTION_ENABLED=True,
    )
    if not availability(settings).available:
        pytest.skip("requires configured pinned Docker sandbox")
    with TestClient(create_app(settings)) as client:
        owner = f"source-check-test-{uuid4()}"
        client.app.dependency_overrides[require_principal] = lambda: owner
        yield client


@pytest.mark.parametrize("case", ["fixed", "wrong_edit", "vacuous"])
def test_source_check_runs_and_exports_measured_candidate(client, monkeypatch, case):
    fake = DynamicProposal("count - unit_price" if case == "wrong_edit" else "count * unit_price")
    monkeypatch.setattr("app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: fake)
    inputs = payload(
        check_code="def verify(implementation):\n    assert True\n" if case == "vacuous" else CHECK
    )
    created = client.post("/api/v1/source-check", json=inputs)
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    result = client.post(f"/api/v1/sessions/{session_id}/run")
    assert result.status_code == 200, result.text
    review = client.get(f"/api/v1/sessions/{session_id}/candidate")
    assert review.status_code == 200, review.text
    candidate = review.json()["candidate"]
    assert candidate is not None
    assert candidate["host_files_modified"] is False
    assert "-    return count + unit_price" in candidate["patch"]
    assert "+    return " + fake.replacement in candidate["patch"]
    report = client.get(f"/api/v1/sessions/{session_id}/report").json()
    if case == "fixed":
        assert report["verification_status"] == "passed"
        assert report["confidence_level"] == "medium"
        assert (
            "failed on the original source and passed on the candidate"
            in report["final_conclusion"]
        )
        assert report["open_questions"]
    else:
        assert report["verification_status"] != "passed"
        assert "failed on the original source and passed on the candidate" not in (
            report["final_conclusion"] or ""
        )
    assert fake.source_path is not None and not fake.source_path.exists()
    with client.app.state.session_factory() as db:
        artifact = db.scalar(
            select(Artifact).where(
                Artifact.session_id == UUID(session_id),
                Artifact.artifact_type == "source_check_input",
            )
        )
        assert artifact.artifact_metadata["source_code"] == SOURCE
    evidence = client.get(f"/api/v1/sessions/{session_id}/artifacts").json()["evidence"]
    assert any(item["raw_excerpt"] == SOURCE for item in evidence)
    if case == "fixed":
        with client.app.state.session_factory() as db:
            plan = db.scalar(
                select(PlanTask).where(
                    PlanTask.session_id == UUID(session_id),
                    PlanTask.tool_name == "source_patch_sandbox",
                )
            )
            plan.params = {**plan.params, "new_text": "count - unit_price"}
            db.commit()
        assert client.get(f"/api/v1/sessions/{session_id}/candidate").status_code == 409


def test_source_check_rejects_mutated_stored_input_before_model_dispatch(client, monkeypatch):
    fake = DynamicProposal()
    monkeypatch.setattr("app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: fake)
    session_id = client.post("/api/v1/source-check", json=payload()).json()["id"]
    with client.app.state.session_factory() as db:
        artifact = db.scalar(
            select(Artifact).where(
                Artifact.session_id == UUID(session_id),
                Artifact.artifact_type == "source_check_input",
            )
        )
        artifact.artifact_metadata = {
            **artifact.artifact_metadata,
            "source_code": SOURCE + "# changed\n",
        }
        db.commit()
    response = client.post(f"/api/v1/sessions/{session_id}/run")
    assert response.status_code == 500
    assert not fake.requests
    assert client.get(f"/api/v1/sessions/{session_id}/candidate").status_code == 409


def test_disabled_source_check_rejects_creation():
    with TestClient(create_app(Settings(_env_file=None, CODE_EXECUTION_ENABLED=False))) as client:
        assert client.get("/api/v1/source-check").json()["available"] is False
        assert client.post("/api/v1/source-check", json=payload()).status_code == 409


def test_persisted_repair_is_reused_only_within_owner_and_retested(client, monkeypatch):
    from app.cognition.repair_memory import EVENT
    from app.memory import SQLAlchemyMemoryRepository

    fake = DynamicProposal()
    monkeypatch.setattr("app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: fake)
    first = client.post("/api/v1/source-check", json=payload()).json()["id"]
    assert client.post(f"/api/v1/sessions/{first}/run").status_code == 200
    assert client.get(f"/api/v1/sessions/{first}/report").json()["verification_status"] == "passed"
    assert len(fake.requests) == 1
    owner = client.app.dependency_overrides[require_principal]()
    with client.app.state.session_factory() as db:
        db.info["owner_id"] = owner
        lessons = SQLAlchemyMemoryRepository(db).load_repair_lessons()
        assert len(lessons) == 1 and lessons[0].source_session_id == first
        db.info["owner_id"] = "different-test-owner"
        assert SQLAlchemyMemoryRepository(db).load_repair_lessons() == []
    second = client.post(
        "/api/v1/source-check",
        json=payload(
            source_code=SOURCE.replace("total", "invoice"),
            check_code="def verify(implementation):\n    assert implementation.invoice(11, 4) == 44\n",
        ),
    ).json()["id"]
    assert client.post(f"/api/v1/sessions/{second}/run").status_code == 200
    assert client.get(f"/api/v1/sessions/{second}/report").json()["verification_status"] == "passed"
    assert len(fake.requests) == 1
    events = client.get(f"/api/v1/sessions/{second}/events").json()["events"]
    assert any(
        e["event_type"] == EVENT and e["metadata"]["source_session_id"] == first for e in events
    )
    candidate = client.get(f"/api/v1/sessions/{second}/candidate").json()["candidate"]
    assert candidate["verification_status"] == "passed"
    assert "count * unit_price" in candidate["patch"]


def test_rejected_persisted_repair_recovers_and_exports_only_current_candidate(client, monkeypatch):
    from app.cognition.repair_recovery import EVENT
    from app.memory import SQLAlchemyMemoryRepository

    fake = DynamicProposal()
    monkeypatch.setattr("app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: fake)
    first = client.post("/api/v1/source-check", json=payload()).json()["id"]
    assert client.post(f"/api/v1/sessions/{first}/run").status_code == 200
    assert client.get(f"/api/v1/sessions/{first}/report").json()["verification_status"] == "passed"
    fake.replacement = "count - unit_price"
    second = client.post(
        "/api/v1/source-check",
        json=payload(
            raw_input="The revised billing rule is count minus unit_price; repair against the current check.",
            check_code="def verify(implementation):\n    assert implementation.total(11, 4) == 7\n",
        ),
    ).json()["id"]
    assert client.post(f"/api/v1/sessions/{second}/run").status_code == 200
    report = client.get(f"/api/v1/sessions/{second}/report").json()
    assert report["verification_status"] == "passed"
    assert len(fake.requests) == 2
    candidate = client.get(f"/api/v1/sessions/{second}/candidate").json()["candidate"]
    assert candidate["verification_status"] == "passed"
    assert "+    return count - unit_price" in candidate["patch"]
    assert "count * unit_price" not in candidate["patch"]
    events = client.get(f"/api/v1/sessions/{second}/events", params={"limit": 200}).json()["events"]
    assert any(e["event_type"] == EVENT for e in events)
    assert any(e["event_type"] == "verification_invalidated" for e in events)
    with client.app.state.session_factory() as db:
        db.info["owner_id"] = client.app.dependency_overrides[require_principal]()
        lessons = SQLAlchemyMemoryRepository(db).load_repair_lessons()
        assert any(
            lesson.source_session_id == second and lesson.new_text == "count - unit_price"
            for lesson in lessons
        )
