"""Contract tests for the Chapter 13-D unfamiliar-task structural proof."""

from evals.chapter_13d.run_live_four_condition_benchmark import (
    _expected_supported,
    _load_corpus,
    _retrieve,
    _run_polya,
)
from evals.chapter_13d.run_live_four_condition_benchmark import (
    _load_cases as load_live_cases,
)
from evals.chapter_13d.run_micro_world_proof import load_cases, run_proof


def test_micro_world_proof_covers_six_cases_three_families_and_transfer() -> None:
    summary = run_proof(load_cases())

    assert len(summary["results"]) == 6
    assert summary["gate"]["structural_proof_passed"] is True
    assert summary["gate"]["three_families"] is True
    assert summary["gate"]["all_polya_runs_verified"] is True
    assert summary["gate"]["all_polya_runs_within_two_model_calls"] is True
    assert summary["gate"]["all_transfer_cases_reduce_acquisition_work"] is True
    assert summary["gate"]["scientific_win_claimed"] is False


def test_every_case_reports_all_four_conditions_and_auditable_resources() -> None:
    summary = run_proof(load_cases())

    for result in summary["results"]:
        assert set(result["baselines"]) == {
            "direct",
            "full_context",
            "ordinary_retrieval",
        }
        assert result["polya"]["passed"] is True
        assert result["polya"]["source_uris"]
        assert result["polya"]["model_calls"] == 2
        assert result["polya"]["normalized_cost"] <= 2.0


def test_live_corpus_contract_retrieves_and_solves_all_cases_without_model_calls() -> None:
    corpus = _load_corpus()

    for case in load_live_cases():
        document_id, _text = _retrieve(case, corpus)
        result = _run_polya(case, corpus)

        assert document_id == case["id"]
        assert result["passed"] is True
        assert result["verification_passed"] is True
        assert result["model_calls"] == 0
        assert result["total_tokens"] == 0
        assert result["acquisitions"] == 1


def test_live_rubric_normalizes_punctuation_without_erasing_rule_identity() -> None:
    report = "18 minutes after an amber-tier abort."

    assert _expected_supported(report, "18-minute")
    assert _expected_supported(report, "amber-tier abort")
    assert not _expected_supported("37 ticks", "Z7.4")
