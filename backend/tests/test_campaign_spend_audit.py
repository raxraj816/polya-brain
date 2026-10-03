"""Offline accounting regressions; no credentials, providers, or sandbox required."""

import json

import pytest
from evals.launch_readiness.spend_audit import audit_campaign, money


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def call(root, *, identity="response-1", cost=0.1, returned=True):
    directory = root / "spend"
    save(directory / "1.reserved.json", {"reserve_usd": "0.2", "model": "fixture"})
    if returned:
        save(
            directory / "1.reported.json",
            {"response_id": identity, "model": "fixture", "provider_reported_cost_usd": cost},
        )
        save(
            directory / "1.response.json",
            {"response_id": identity, "model": "fixture", "usage": {"estimated_cost_usd": cost}},
        )
    return directory


def test_overlapping_roots_and_response_copies_count_once(tmp_path):
    call(tmp_path / "a")
    call(tmp_path / "b")
    result = audit_campaign([tmp_path, tmp_path / "a"])
    assert result["provider_or_trace_reported_usd"] == "0.1"
    assert len(result["records"]) == 2
    assert len(result["duplicate_responses"]) == 1
    assert not result["artifact_issues"]


def test_interruption_without_failure_marker_retains_reservation(tmp_path):
    call(tmp_path, returned=False)
    result = audit_campaign([tmp_path])
    assert result["unresolved_local_reservations_usd"] == "0.2"
    assert result["unresolved_calls"] == 1
    assert not result["safe_to_resume_paid_calls"]


def test_disagreement_preserves_reservation(tmp_path):
    directory = call(tmp_path)
    save(
        directory / "1.reported.json",
        {"response_id": "response-1", "model": "fixture", "provider_reported_cost_usd": 0.01},
    )
    result = audit_campaign([tmp_path])
    assert result["artifact_issues"]
    assert result["unresolved_local_reservations_usd"] == "0.2"


def test_conflicting_duplicate_does_not_silently_refund(tmp_path):
    call(tmp_path / "a")
    call(tmp_path / "b", cost=0.15)
    result = audit_campaign([tmp_path])
    assert result["artifact_issues"]
    assert result["recorded_reported_plus_reserved_usd"] == "0.3"


@pytest.mark.parametrize("value", [None, True, -1, "NaN", "Infinity", "bad"])
def test_invalid_amounts_fail_closed(value):
    with pytest.raises(ValueError):
        money(value)


def test_missing_record_and_root_are_not_zero_cost_success(tmp_path):
    directory = call(tmp_path)
    (directory / "1.reserved.json").unlink()
    result = audit_campaign([tmp_path, tmp_path / "missing"])
    assert len(result["artifact_issues"]) == 2
    assert not result["safe_to_resume_paid_calls"]


def test_trace_overlap_rejected_and_aggregate_not_double_counted(tmp_path):
    call(tmp_path)
    trace = tmp_path / "trace.json"
    save(trace, [{"metadata": {"model_calls": [{"cost_usd": 0.1}]}}])
    result = audit_campaign([tmp_path], [trace])
    assert result["artifact_issues"]
    assert result["provider_or_trace_reported_usd"] == "0.1"


def test_unmetered_trace_itemization_and_empty_trace(tmp_path):
    trace = tmp_path / "trace.json"
    empty = tmp_path / "empty.json"
    save(
        trace,
        [
            {"metadata": {"model_calls": 2}},
            {"metadata": {"model_calls": [{"cost_usd": 0.1}, {"cost_usd": 0.2}]}},
        ],
    )
    save(empty, [])
    result = audit_campaign([tmp_path], [trace, trace, empty], cap="0.2")
    assert result["provider_or_trace_reported_usd"] == "0.3"
    assert result["nominal_difference_from_cap_usd"] == "-0.1"
    assert len(result["artifact_issues"]) == 1
    assert not result["safe_to_resume_paid_calls"]
