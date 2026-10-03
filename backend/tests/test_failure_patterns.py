"""Failure-pattern memory: record, merge, retrieve and feed back as hints."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.execution import DockerPythonSandbox, DockerSandboxLimits, image_available
from app.memory.failure_patterns import MAX_PATTERNS, FailurePatternStore


def test_patterns_merge_rank_and_stay_bounded(tmp_path: Path) -> None:
    store = FailurePatternStore(tmp_path / "patterns.jsonl")
    first = store.record(
        "change", "Rounding of exact halves switched to banker's rounding", trigger="(1, 2, 2, 2)"
    )
    again = store.record(
        "change", "rounding of exact  halves switched to banker's rounding", source="run-2"
    )
    assert again.id == first.id and again.seen == 2 and again.sources == ["run-2"]
    store.record("claims", "Average computed per row instead of weighted by quantity")
    hits = store.relevant("change", "prorate rounding of halves in billing")
    assert [p.id for p in hits] == [first.id]
    assert store.relevant("claims", "prorate rounding of halves in billing") == []
    assert "NOT requirements" in store.prompt_hints("change", "halves rounding banker")
    assert store.prompt_hints("change", "unrelated words entirely") == ""
    with (tmp_path / "patterns.jsonl").open("a") as stream:
        stream.write("{damaged json\n")
    assert len(store.load()) == 2
    for index in range(MAX_PATTERNS + 5):
        store.record("coding", f"synthetic defect number {index} unique signature")
    assert len(store.load()) == MAX_PATTERNS


docker = pytest.mark.skipif(
    shutil.which("docker") is None or not image_available(DockerPythonSandbox().image),
    reason="Docker sandbox image unavailable",
)


@docker
def test_a_confirmed_regression_becomes_a_hint_for_the_next_change(tmp_path: Path) -> None:
    from test_verified_change import GENERATED, ORIGINAL, SORTED_REGRESSION

    from app.llm import FakeLLMClient
    from app.verified_change.pipeline import ChangeLimits, ChangeVerifier
    from app.verified_change.source import ModuleVersions, analyse

    store = FailurePatternStore(tmp_path / "patterns.jsonl")
    versions = ModuleVersions(tmp_path, "tags.py", "base", "new", ORIGINAL, SORTED_REGRESSION)

    def run(client: FakeLLMClient) -> None:
        ChangeVerifier(
            client,
            "fake-model",
            DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
            limits=ChangeLimits(differential_budget_seconds=1.0),
            patterns=store,
            source="run",
        ).verify(
            versions,
            analyse(versions, "normalize_tags"),
            "Simplify normalize_tags. No behavior change.",
        )

    first = FakeLLMClient([GENERATED])
    run(first)
    assert "DEFECTS POLYABRAIN CONFIRMED BEFORE" not in first.requests[0].messages[0].content
    learned = store.load()
    assert learned and learned[0].domain == "change" and "normalize_tags" in learned[0].signature
    second = FakeLLMClient([GENERATED])
    run(second)
    prompt = second.requests[0].messages[0].content
    assert "DEFECTS POLYABRAIN CONFIRMED BEFORE" in prompt and "normalize_tags" in prompt
    assert json.loads((tmp_path / "patterns.jsonl").read_text().splitlines()[0])["seen"] == 2


@docker
def test_a_corrected_claim_is_learned_and_offered_to_the_next_verifier(tmp_path: Path) -> None:
    from test_verified_claims import CLAIMS, ORDERS, QUESTION, answer, oracle

    from app.llm import FakeLLMClient
    from app.verified_claims.pipeline import ClaimLimits, ClaimVerifier
    from app.verified_claims.tables import load_tables

    store = FailurePatternStore(tmp_path / "patterns.jsonl")
    table = tmp_path / "orders.csv"
    table.write_text(ORDERS)

    def run(client: FakeLLMClient) -> None:
        ClaimVerifier(
            client,
            "fake-model",
            DockerPythonSandbox(
                limits=DockerSandboxLimits(timeout_seconds=30, memory_megabytes=128)
            ),
            limits=ClaimLimits(call_seconds=3.0),
            patterns=store,
        ).verify(QUESTION, load_tables([table]))

    wrong_text = [dict(CLAIMS[0], value=600.0), CLAIMS[1]]
    run(FakeLLMClient([answer(claims=wrong_text), oracle()]))
    assert store.load()[0].domain == "claims"
    second = FakeLLMClient([answer(), oracle()])
    run(second)
    assert "DEFECTS POLYABRAIN CONFIRMED BEFORE" in second.requests[1].messages[0].content
