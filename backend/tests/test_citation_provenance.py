"""A model's passing verdict cannot invent a consulted source or section."""

import json
import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_on_demand_cognition import _conclusion_json, _deliberation_json, _ready_state, _response

from app.cognition import CognitiveKernel, CognitiveModelGateway, CognitiveResourceBudget
from app.cognition.capabilities import CapabilityRegistry
from app.cognition.citation_provenance import (
    MAX_ANSWER_CHARS,
    MAX_LINKS,
    MAX_SOURCE_CHARS,
    check_citations,
)
from app.cognition.contracts import CognitiveRunStatus
from app.cognition.model_capabilities import verifier_capability
from app.cognition.model_contracts import DeliberationCapabilityOutput
from app.cognition.on_demand_capabilities import conclusion_checker_capability
from app.config import Settings, get_settings
from app.db.models import EpisodicMemory, ProblemSession, ReasoningEvent
from app.investigator.artifacts import report_from_result
from app.llm import FakeLLMClient
from app.main import create_app
from app.models.contracts import EvidenceItem

SOURCE = "https://manual.example/mira?revision=7"
EXCERPT = "6.4.1. Timeout\nThe timeout is 37 ticks. See Section 9.3.1 for another topic."


def citation_state(excerpt=EXCERPT, uri=SOURCE):
    state = _ready_state()
    state["session_id"] = str(uuid4())
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_web_source",
            source_uri=uri,
            claim="The timeout is 37 ticks.",
            raw_excerpt=excerpt,
        )
    ]
    analysis = DeliberationCapabilityOutput.model_validate_json(_deliberation_json())
    state["hypotheses"] = analysis.hypotheses
    state["plan"] = analysis.tasks
    state["execution_outputs"] = analysis.execution_outputs
    return state


def review(answer, *, fused=True, state=None):
    output = json.loads(_conclusion_json())
    output["final_answer"] = answer
    if not fused:
        del output["reflection"]
    client = FakeLLMClient([_response(json.dumps(output))])
    registry = CapabilityRegistry()
    factory = conclusion_checker_capability if fused else verifier_capability
    registry.register(factory(CognitiveModelGateway(client, "fake")))
    result = CognitiveKernel(registry).run(
        state or citation_state(), max_cycles=1, budget=CognitiveResourceBudget(max_model_calls=4)
    )
    return result, client


@pytest.mark.parametrize("fused", [True, False])
@pytest.mark.parametrize("url", ["https://invented.example/rule", SOURCE + "#section-9.3.1"])
def test_model_pass_with_unadmitted_citation_is_rejected(url, fused):
    answer = f"The timeout is 37 ticks. [Manual]({url})"
    result, client = review(answer, fused=fused)
    assert not result.state["verification"].passed
    assert result.state["final_answer"] is None
    assert result.state["reflection"] is None
    assert len(client.requests) == 1
    event = next(e for e in result.state["events"] if e.event_type == "citation_provenance_checked")
    assert event.metadata["rejected_answer"] == answer
    assert event.metadata["passed"] is False


@pytest.mark.parametrize("fused", [True, False])
def test_supported_section_retains_answer_and_semantic_review(fused):
    answer = f"The timeout is 37 ticks. [Manual]({SOURCE}#section-6.4.1)"
    result, client = review(answer, fused=fused)
    assert result.state["verification"].passed
    assert result.state["final_answer"] == answer
    assert len(client.requests) == 1


@pytest.mark.parametrize("fused", [True, False])
def test_non_http_fixture_evidence_keeps_existing_semantic_review(fused):
    uri = "fixture://manual#section-6.4.1"
    answer = f"The timeout is 37 ticks. [Supplied fixture]({uri})"
    result, client = review(answer, fused=fused, state=citation_state(uri=uri))
    assert result.state["verification"].passed
    assert result.state["final_answer"] == answer
    assert len(client.requests) == 1
    event = next(e for e in result.state["events"] if e.event_type == "citation_provenance_checked")
    assert event.metadata["checked_links"] == 0


@pytest.mark.parametrize(
    "answer",
    [
        f"Read [the manual]({SOURCE}) for the 37-tick timeout.",
        f"Read [the manual][m].\n\n[m]: {SOURCE}#section-6.4.1",
        f"Read <{SOURCE}#6.4.1>.",
        f"The rule is documented at {SOURCE}#section-6%2E4%2E1.",
        f"| Topic | Source |\n| --- | --- |\n| Timeout | [manual]({SOURCE}) |",
        f"> The excerpt supports the timeout. [Manual]({SOURCE})",
        "Example: `https://unread.example/path`.",
        "```python\nurl = 'https://unread.example/path'\n```",
        "~~~text\nhttps://unread.example/path\n~~~",
        "    https://unread.example/path\n",
        "Unverified link (not evidence): [Future research](https://unread.example).",
        "Unverified link (not evidence): https://unread.example",
        "A sentence without a citation remains subject to semantic review.",
    ],
)
def test_supported_formats_and_explicit_examples_are_not_false_rejected(answer):
    assert not check_citations(citation_state(), answer).failures


@pytest.mark.parametrize(
    "answer",
    [
        "Source: https://unread.example/path.",
        "[Manual][m]\n\n[m]: https://unread.example/path",
        "<https://unread.example/path>",
        "| Topic | Source |\n| --- | --- |\n| Timeout | [manual](https://unread.example) |",
        "> [Manual](https://unread.example)",
        f"[Manual]({SOURCE}#section-9.3.1)",
        f"[Manual]({SOURCE}#section-6.4.10)",
        f"[Manual]({SOURCE}#unknown-anchor)",
        "[Manual](https://manual.example/mira?revision=8)",
        "[Manual](https://manual.example/mira)",
        "[Manual](http://manual.example/mira?revision=7)",
        "[Manual](https://manual.example/mira/?revision=7)",
        "[Manual](https://manual.example@unread.example/mira?revision=7)",
        "[Manual](//manual.example/mira?revision=7)",
        "[Manual](https://manual.example:invalid/mira?revision=7)",
        "[Manual](https://manual.example/mira%QQ?revision=7)",
        "Unverified link (not evidence): [Manual](https://unread.example) proves the timeout.",
        "Unverified link (not evidence): [A](https://a.example) [B](https://b.example)",
        "Unverified link (not evidence): [A](https://a.example)\nThe timeout is 37 ticks.",
    ],
)
def test_unsupported_citations_cannot_hide_in_formatting_or_url_aliases(answer):
    assert check_citations(citation_state(), answer).failures


def test_future_link_does_not_exempt_a_later_factual_paragraph():
    answer = (
        "Unverified link (not evidence): [Future](https://future.example).\n\n"
        "The timeout is 37 ticks. [Rule](https://invented.example/rule)"
    )
    result = check_citations(citation_state(), answer)
    assert result.unverified_links == 1
    assert len(result.failures) == 1
    assert "invented.example" in result.failures[0]


def test_source_claims_and_other_documents_cannot_supply_a_missing_heading():
    state = citation_state()
    state["evidence"][0].claim = "9.3.1. Timeout\nThe timeout is 37 ticks."
    state["evidence"].append(
        EvidenceItem(
            source_type="web",
            source_uri="https://other.example",
            claim="Another rule.",
            raw_excerpt="9.3.1. Timeout\nThe timeout is 37 ticks.",
        )
    )
    assert check_citations(state, f"[Manual]({SOURCE}#section-9.3.1)").failures


def test_missing_excerpt_and_user_supplied_url_are_not_admitted_evidence():
    state = citation_state(excerpt=None)
    state["raw_input"] += f" See {SOURCE}."
    assert check_citations(state, f"[Manual]({SOURCE})").failures
    state["evidence"] = []
    assert check_citations(state, f"[Manual]({SOURCE})").failures


def test_source_equivalence_is_limited_and_fragments_remain_bound():
    state = citation_state(uri="https://MANUAL.example:443/mira?revision=7")
    assert not check_citations(state, f"[Manual]({SOURCE})").failures
    assert not check_citations(
        citation_state(uri=SOURCE + "#timeout"), f"[Manual]({SOURCE}#timeout)"
    ).failures
    # Even an admitted numbered URI requires its heading, not just a named fragment.
    assert check_citations(
        citation_state(uri=SOURCE + "#section-9.3.1"), f"[Manual]({SOURCE}#section-9.3.1)"
    ).failures


def test_repeated_passages_can_supply_a_heading_without_cross_source_credit():
    state = citation_state()
    state["evidence"].append(
        EvidenceItem(
            source_type="web",
            source_uri=SOURCE,
            claim="The new passage.",
            raw_excerpt="## 9.3.1. Another rule\nThe timeout is 37 ticks.",
        )
    )
    assert not check_citations(state, f"[Manual]({SOURCE}#section-9.3.1)").failures


def test_input_limits_fail_closed_and_trace_remains_bounded():
    answer = "x" * (MAX_ANSWER_CHARS + 1)
    result = check_citations(citation_state(), answer)
    assert result.failures
    event = result.event(answer, "conclusion_checker")
    assert len(event.metadata["rejected_answer"]) == 16_000
    assert event.metadata["rejected_answer_truncated"]
    assert check_citations(citation_state(), (f"[Manual]({SOURCE}) " * (MAX_LINKS + 1))).failures
    assert check_citations(
        citation_state(), "[Manual](https://unread.example/" + "x" * 2050 + ")"
    ).failures
    state = citation_state(excerpt="x" * (MAX_SOURCE_CHARS + 1))
    assert check_citations(state, f"[Manual]({SOURCE})").failures


def test_failed_citation_is_visible_in_cli_report_without_a_verified_answer():
    result, _ = review("A checked timeout. [Manual](https://invented.example)")
    assert result.status != CognitiveRunStatus.COMPLETED
    report = report_from_result(result)
    assert report.failed_checks
    assert "no admitted source" in " ".join(report.failed_checks)
    assert report.verification_status != "passed"
    assert report.final_conclusion == "No verified conclusion is available."
    assert report.reflection is None


@pytest.mark.skipif(
    os.environ.get("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)
def test_failed_citation_survives_api_reload_and_cannot_become_learned_success(monkeypatch):
    def runner(raw_input, *, session_id):
        state = citation_state()
        state["session_id"] = session_id
        state["raw_input"] = raw_input
        result, _ = review("A checked timeout. [Manual](https://invented.example)", state=state)
        return result.state

    monkeypatch.setattr(
        "app.api.routes.sessions.build_representation_session_runner",
        lambda *args, **kwargs: runner,
    )
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
    with TestClient(app) as client:
        session_id = client.post(
            "/api/v1/sessions", json={"raw_input": "Check the supplied manual."}
        ).json()["id"]
        response = client.post(f"/api/v1/sessions/{session_id}/run")
        assert response.status_code == 200, response.text
        assert response.json()["verification_status"] == "failed"
        first = client.get(f"/api/v1/sessions/{session_id}/report").json()
    with TestClient(app) as client:
        second = client.get(f"/api/v1/sessions/{session_id}/report").json()
        assert first == second
        assert second["verification_status"] == "failed"
        assert "no admitted source" in " ".join(second["failed_checks"])
        assert second["reflection"] is None
    with app.state.session_factory() as db:
        assert db.get(ProblemSession, UUID(session_id)).final_answer is None
        assert not list(
            db.scalars(
                select(EpisodicMemory).where(EpisodicMemory.source_session_id == UUID(session_id))
            )
        )
        event = db.scalar(
            select(ReasoningEvent).where(
                ReasoningEvent.session_id == UUID(session_id),
                ReasoningEvent.event_type == "citation_provenance_checked",
            )
        )
        assert event.event_metadata["passed"] is False
