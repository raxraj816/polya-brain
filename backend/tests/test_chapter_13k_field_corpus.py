"""Contract tests for the Chapter 13-K field-derived executable corpus."""

from __future__ import annotations

from collections import Counter

from evals.chapter_13k.corpus import (
    case_root,
    load_cases,
    polya_problem_input,
    preflight_case,
    visible_evidence_packet,
)


def test_field_corpus_has_six_real_provenance_bearing_paired_cases() -> None:
    cases = load_cases()

    assert len(cases) == 6
    assert len({case.project for case in cases}) == 3
    assert Counter(case.pair_position for case in cases) == {"first": 3, "transfer": 3}
    assert all(case.public_historical_case for case in cases)
    assert all(case.reduced_reproduction for case in cases)
    assert all(case.buggy_commit != case.fixed_commit for case in cases)
    assert all(str(case.bugsinpy_metadata).startswith("https://github.com/") for case in cases)


def test_every_field_case_has_executable_fail_to_pass_preflight() -> None:
    for case in load_cases():
        preflight = preflight_case(case)

        assert preflight.eligible is True
        assert preflight.buggy.exit_code != 0
        assert preflight.fixed.exit_code == 0
        assert f"{case.id}:fixed:PASS" in preflight.fixed.stdout


def test_equal_information_packet_excludes_hidden_fixed_source() -> None:
    for case in load_cases():
        preflight = preflight_case(case)
        packet = visible_evidence_packet(case, preflight)
        raw_input = polya_problem_input(case, preflight)
        root = case_root(case)

        assert case.problem_statement in packet
        assert "BUGGY REPRODUCTION OBSERVATION" in packet
        assert "fixed_impl.py" not in raw_input
        for artifact in case.artifacts:
            content = artifact.resolve(root).read_text(encoding="utf-8").strip()
            if artifact.visible_to_conditions:
                assert content in packet
                assert str(artifact.resolve(root)) in raw_input
            else:
                assert content not in packet
                assert str(artifact.resolve(root)) not in raw_input


def test_field_cases_declare_hidden_semantic_outcome_rules() -> None:
    for case in load_cases():
        assert case.required_mechanism_concepts
        assert case.required_correction_concepts
        assert case.required_check_concepts
        assert all(rule.any_of for rule in case.required_mechanism_concepts)
        assert all(rule.any_of for rule in case.required_correction_concepts)
        assert all(rule.any_of for rule in case.required_check_concepts)
