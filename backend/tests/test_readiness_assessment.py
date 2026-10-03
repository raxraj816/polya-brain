"""Saved evaluation corruption and missing attempts must not become wins."""

import json
from dataclasses import asdict

import pytest
from evals.chapter_13p.coding_execution.evidence import checks_digest, digest
from evals.chapter_13p.coding_execution.matched import DEFAULT_LIMITS
from evals.chapter_13p.coding_execution.verify import CHECKS
from evals.launch_readiness.assess import assess, build_packet


def write(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def run(tmp_path):
    root = tmp_path / "run"
    root.mkdir()
    manifest = dict(
        cases={"median": "Implement median"},
        repeats=1,
        model="fixture",
        limits=asdict(DEFAULT_LIMITS),
        checks={"median": checks_digest(CHECKS["median"])},
    )
    write(root / "manifest.json", manifest)
    for arm in ("lean", "polya"):
        directory = root / f"median-0-{arm}"
        directory.mkdir()
        write(
            directory / "input.json",
            dict(prompt="Implement median", model="fixture", limits=manifest["limits"]),
        )
        # Both deliberately deliver nothing. This is a valid recorded failure.
        outcome = dict(
            case="median",
            arm=arm,
            prompt_sha256=digest("Implement median"),
            delivered_answer=None,
            usage=dict(
                model_calls=1,
                sandbox_calls=0,
                input_tokens=10,
                output_tokens=10,
                usage_complete=True,
                elapsed_ms=100,
            ),
        )
        write(directory / "outcome.json", outcome)
        write(
            directory / "score.json",
            dict(
                **outcome,
                repeat=0,
                independent=dict(passed=False, checks_sha256=manifest["checks"]["median"]),
            ),
        )
        write(
            directory / "model-1.request.json",
            dict(model="fixture", options=dict(max_retries=0, max_output_tokens=100)),
        )
        write(
            directory / "model-1.response.json",
            dict(
                model="fixture",
                usage=dict(input_tokens=10, output_tokens=10, estimated_cost_usd=0.001),
            ),
        )
    return root


def test_failures_are_valid_evidence_and_remain_in_denominator(run):
    report = assess(run)
    assert report["all_artifacts_valid"]
    assert report["totals"]["polya"]["attempts"] == 1
    assert report["totals"]["polya"]["independent_passes"] == 0
    assert not report["superiority_established"]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "model",
        "cost",
        "tokens",
        "invented_pass",
        "score_answer",
        "extra_response",
        "limits",
        "infinite_cost",
    ],
)
def test_tampered_or_missing_evidence_fails_closed(run, mutation):
    directory = run / "median-0-polya"
    if mutation == "missing":
        (directory / "score.json").unlink()
    else:
        name = {
            "model": "model-1.response.json",
            "cost": "model-1.response.json",
            "infinite_cost": "model-1.response.json",
            "tokens": "model-1.response.json",
            "invented_pass": "score.json",
            "score_answer": "score.json",
            "extra_response": "model-2.response.json",
            "limits": "input.json",
        }[mutation]
        value = json.loads(
            (
                directory / ("model-1.response.json" if mutation == "extra_response" else name)
            ).read_text()
        )
        if mutation == "model":
            value["model"] = "different"
        if mutation == "cost":
            value["usage"]["estimated_cost_usd"] = None
        if mutation == "infinite_cost":
            value["usage"]["estimated_cost_usd"] = float("inf")
        if mutation == "tokens":
            value["usage"]["input_tokens"] += 1
        if mutation == "invented_pass":
            value["independent"]["passed"] = True
        if mutation == "score_answer":
            value["delivered_answer"] = "invented answer"
        if mutation == "limits":
            value["limits"]["model_calls"] += 1
        write(directory / name, value)
    report = assess(run)
    assert not report["all_artifacts_valid"]
    assert report["totals"]["polya"]["attempts"] == 1
    assert report["totals"]["polya"]["cost_usd"] is None
    assert report["polya_to_lean"]["tokens"] is None


def test_review_packet_keeps_failure_and_separates_condition_key(run, tmp_path):
    output = tmp_path / "packet"
    build_packet(run, output)
    packet = json.loads((output / "review-packet.json").read_text())
    key = json.loads((output / "private-condition-key.json").read_text())
    assert packet["review_status"] == "unreviewed"
    assert "[No answer delivered]" in (output / "review-packet.md").read_text()
    responses = packet["pairs"][0]["responses"]
    assert len(responses) == 2
    assert all(r["answer"] == "[No answer delivered]" for r in responses)
    assert {r["response_id"] for r in responses} == {r["response_id"] for r in key}
    assert all("arm" not in r and "cost_usd" not in r for r in responses)
    with pytest.raises(FileExistsError):
        build_packet(run, output)
