"""Offline contract tests for the Chapter 13-E live benchmark."""

from evals.chapter_13e.run_live_verifier_benchmark import (
    _run_polya,
    condition_order,
    load_cases,
    score_gate,
)


def test_cases_cover_two_families_and_polya_rejects_every_false_candidate() -> None:
    cases = load_cases()
    results = [_run_polya(case) for case in cases]

    assert len(cases) == 6
    assert {case["family"] for case in cases} == {"multi_rule", "debugging"}
    assert all(item["passed"] for item in results)
    assert all(item["criterion_coverage"] == 1.0 for item in results)
    assert not any(item["false_pass"] for item in results)
    assert sum(item["accepted"] for item in results) == 2
    assert sum(item["model_calls"] for item in results) == 0


def test_condition_order_rotates_and_gate_requires_three_repetitions() -> None:
    assert condition_order(0, 1) != condition_order(1, 1)
    template = {
        condition: {
            "passed": True,
            "false_pass": False,
            "criterion_coverage": 1.0,
            "total_tokens": 0 if condition == "polya" else 100,
        }
        for condition in ("direct_model", "full_context", "ordinary_retrieval", "polya")
    }
    one_repetition = [template for _ in range(6)]
    three_repetitions = [template for _ in range(18)]

    assert not score_gate(one_repetition, 6, 1)["chapter_13e_verifier_gate_passed"]
    assert score_gate(three_repetitions, 6, 3)["chapter_13e_verifier_gate_passed"]
