"""Evaluation fairness and missing outcomes must remain inspectable."""

import json
from pathlib import Path

import pytest
from evals.launch_readiness.investigation import (
    Case,
    load_cases,
    review_packet,
    run_arm,
    solver_packet,
)
from pydantic import ValidationError

from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage


def case():
    return Case(
        id="sample",
        prompt="Explain the limit.",
        sources=[{"uri": "https://manual.example/spec", "excerpt": "Limit is 64."}],
        rubric="PRIVATE_RUBRIC_SENTINEL",
    )


def test_rubric_is_not_in_solver_packet_or_requests(tmp_path):
    client = FakeLLMClient(
        [
            LLMResponse(
                provider="fake", model="fake", text=text, usage=LLMTokenUsage(estimated_cost_usd=0)
            )
            for text in ["Draft", "Final"]
        ]
    )
    result = run_arm(case(), "lean", client, "fake", tmp_path / "attempt")
    assert result["answer"] == "Final"
    assert result["semantic_correctness"] is None
    assert len(client.requests) == 2
    assert all("PRIVATE_RUBRIC_SENTINEL" not in r.model_dump_json() for r in client.requests)
    assert all(r.options.max_retries == 0 for r in client.requests)
    assert all("Limit is 64." in r.model_dump_json() for r in client.requests)
    saved = json.loads((tmp_path / "attempt/input.json").read_text())
    assert saved["packet"] == solver_packet(case())


@pytest.mark.parametrize("arm", ["lean", "polya"])
def test_provider_failure_is_retained_without_a_semantic_pass(arm, tmp_path):
    result = run_arm(case(), arm, FakeLLMClient([]), "fake", tmp_path / "attempt")
    assert result["semantic_correctness"] is None
    assert not result["usage"]["usage_complete"]
    assert list((tmp_path / "attempt").glob("model-*.failure.json"))
    assert (tmp_path / "attempt/outcome.json").is_file()


def test_blind_packet_includes_missing_attempts_and_empty_ratings(tmp_path):
    review_packet([case()], [], tmp_path)
    packet = json.loads((tmp_path / "review-packet.json").read_text())
    assert len(packet) == 2
    assert all(i["answer"] is None and "arm" not in i for i in packet)
    assert all(all(v is None for v in i["ratings"].values()) for i in packet)
    key = json.loads((tmp_path / "private-condition-key.json").read_text())
    assert {v["arm"] for v in key.values()} == {"lean", "polya"}


def test_duplicate_or_unsafe_case_ids_are_rejected(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"provenance": "test", "cases": [case().model_dump()] * 2}))
    with pytest.raises(ValueError):
        load_cases(path)
    with pytest.raises(ValidationError):
        Case.model_validate({**case().model_dump(), "id": "../overwrite"})


def test_developer_corpus_declares_provenance_and_required_adversaries():
    provenance, cases = load_cases(Path("evals/launch_readiness/investigation-cases.json"))
    assert "not independent" in provenance
    assert {c.id for c in cases} == {
        "redelivery",
        "version-scope",
        "conflicting-timeout",
        "source-injection",
    }
