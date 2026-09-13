"""Offline gates for the Chapter 13-F adaptive scheduler benchmark."""

from evals.chapter_13f.run_adaptive_scheduler_benchmark import (
    condition_order,
    load_cases,
    run_benchmark,
)


def test_scheduler_cases_cover_all_capability_regimes() -> None:
    cases = load_cases()

    assert len(cases) == 12
    assert {case.condition for case in cases} == {
        "healthy",
        "degraded",
        "recovered",
        "version_changed",
    }
    assert len({case.problem_type for case in cases}) == len(cases)
    assert condition_order(0, 1) != condition_order(1, 1)


def test_adaptive_scheduler_passes_repeated_held_out_gate() -> None:
    summary, results = run_benchmark(repetitions=5)
    static = summary["controllers"]["static"]
    adaptive = summary["controllers"]["adaptive"]

    assert len(results) == 120
    assert summary["gate"]["adaptive_scheduler_gate_passed"] is True
    assert summary["gate"]["general_intelligence_win_claimed"] is False
    assert adaptive["verified_outcome_rate"] == 1.0
    assert static["verified_outcome_rate"] == 0.75
    assert adaptive["wrong_routes"] == 0
    assert static["wrong_routes"] == 15
    assert adaptive["external_calls"] < static["external_calls"]
    assert adaptive["tokens"] < static["tokens"]
    assert adaptive["total_latency_ms"] < static["total_latency_ms"]
    assert adaptive["total_regret_ms"] < static["total_regret_ms"]
