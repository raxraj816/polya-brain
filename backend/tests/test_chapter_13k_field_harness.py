"""Offline tests for Chapter 13-K scoring and condition isolation."""

from __future__ import annotations

import json
from pathlib import Path

from evals.chapter_13k.build_blind_review_packet import build_packet
from evals.chapter_13k.contracts import FieldInvestigationOutput
from evals.chapter_13k.corpus import (
    case_root,
    load_cases,
    preflight_case,
    visible_evidence_packet,
)
from evals.chapter_13k.run_field_investigator_comparison import (
    _automated_gate,
    _direct_review_output,
    _direct_state,
    _one_equal_actual_model,
    _score_condition,
)


def _correct_output(case_id: str) -> FieldInvestigationOutput:
    outputs = {
        "fastapi_optional_bearer": FieldInvestigationOutput(
            status="diagnosed",
            root_cause="The wrong scheme branch always raises because auto_error is not checked.",
            corrective_action="Return None for a non-Bearer scheme when auto_error is false.",
            verification_steps=["Test absent, Basic, and Bearer headers."],
            implicated_artifacts=["buggy_impl.py"],
            evidence_references=["check.py"],
        ),
        "httpie_unset_header": FieldInvestigationOutput(
            status="diagnosed",
            root_cause="The unset None sentinel reaches value.decode, so decode is called on None.",
            corrective_action="Skip None before decoding while preserving byte-valued headers.",
            verification_steps=["Test a None header alongside a byte-valued header."],
            implicated_artifacts=["buggy_impl.py"],
            evidence_references=["check.py"],
        ),
        "httpie_host_case": FieldInvestigationOutput(
            status="diagnosed",
            root_cause="Converting to a plain dict loses case-insensitive membership.",
            corrective_action="Check Host membership on the original headers.",
            verification_steps=["Test a lowercase Host and assert one preserved value."],
            implicated_artifacts=["buggy_impl.py"],
            evidence_references=["check.py"],
        ),
        "fastapi_skip_defaults": FieldInvestigationOutput(
            status="diagnosed",
            root_cause="Default semantics are lost when the response becomes a plain dict.",
            corrective_action="Call response.dict with skip_defaults before encoding.",
            verification_steps=["Test that skip true omits note and skip false includes it."],
            implicated_artifacts=["buggy_impl.py"],
            evidence_references=["check.py"],
        ),
        "pysnooper_path_output": FieldInvestigationOutput(
            status="diagnosed",
            root_cause="The closure references an unbound output_path.",
            corrective_action="Open output instead of output_path.",
            verification_steps=["Write through a filesystem path and read the same content."],
            implicated_artifacts=["buggy_impl.py"],
            evidence_references=["check.py"],
        ),
        "fastapi_websocket_router": FieldInvestigationOutput(
            status="diagnosed",
            root_cause="include_router only handles APIRoute; there is no WebSocketRoute branch.",
            corrective_action="Add a WebSocketRoute branch with prefix and name.",
            verification_steps=[
                "Include HTTP and websocket routes and assert both prefixed routes."
            ],
            implicated_artifacts=["buggy_impl.py"],
            evidence_references=["check.py"],
        ),
    }
    return outputs[case_id]


def test_hidden_semantic_scorer_accepts_each_declared_correct_diagnosis() -> None:
    usage = {"model_calls": 1, "input_tokens": 100, "output_tokens": 50}
    for case in load_cases():
        score = _score_condition(case, "direct", _correct_output(case.id), usage, 10.0)

        assert score.passed is True
        assert score.mechanism_concepts_passed is True
        assert score.correction_concepts_passed is True
        assert score.check_concepts_passed is True


def test_scorer_rejects_auditable_but_wrong_diagnosis() -> None:
    case = load_cases()[0]
    wrong = FieldInvestigationOutput(
        status="diagnosed",
        root_cause="The network is probably slow.",
        corrective_action="Add a retry and increase the timeout.",
        verification_steps=["Ping the server."],
        implicated_artifacts=["buggy_impl.py"],
        evidence_references=["check.py"],
    )
    score = _score_condition(
        case,
        "direct",
        wrong,
        {"model_calls": 1, "input_tokens": 100, "output_tokens": 50},
        10.0,
    )

    assert score.passed is False
    assert score.evidence_reference_passed is True
    assert score.mechanism_concepts_passed is False
    assert score.correction_concepts_passed is False


def test_scorer_accepts_valid_paraphrase_from_first_field_pilot() -> None:
    case = next(case for case in load_cases() if case.id == "pysnooper_path_output")
    output = FieldInvestigationOutput(
        status="diagnosed",
        root_cause=(
            "The inner write closure calls open(output_path), but it never binds or captures "
            "a variable named output_path; get_write_function only receives output."
        ),
        corrective_action=(
            "In buggy_impl.py, change open(output_path, 'a') to open(output, 'a') so the "
            "closure references the captured output parameter."
        ),
        verification_steps=[
            "Invoke the returned writer for a Path and assert the target file contains the text."
        ],
        implicated_artifacts=["buggy_impl.py", "get_write_function"],
        evidence_references=["check.py"],
    )

    score = _score_condition(
        case,
        "direct",
        output,
        {"model_calls": 1, "input_tokens": 100, "output_tokens": 50},
        10.0,
    )

    assert score.passed is True


def test_scorer_accepts_exact_skip_defaults_mechanism_without_phrase_padding() -> None:
    case = next(case for case in load_cases() if case.id == "fastapi_skip_defaults")
    output = FieldInvestigationOutput(
        status="diagnosed",
        root_cause=(
            "serialize_response ignores skip_defaults and manually creates a response "
            "dictionary, bypassing ResponseModel.dict and its default filtering."
        ),
        corrective_action=(
            "Delegate to response.dict(skip_defaults=skip_defaults) in buggy_impl.py."
        ),
        verification_steps=["Verify both skip_defaults settings in check.py."],
        implicated_artifacts=["buggy_impl.py"],
        evidence_references=["check.py"],
    )

    score = _score_condition(
        case,
        "direct",
        output,
        {"model_calls": 1, "input_tokens": 100, "output_tokens": 50},
        10.0,
    )

    assert score.passed is True


def test_scorer_rejects_correct_answers_transferred_to_unrelated_cases() -> None:
    usage = {"model_calls": 1, "input_tokens": 100, "output_tokens": 50}
    cases = load_cases()
    for index, case in enumerate(cases):
        unrelated = _correct_output(cases[(index + 1) % len(cases)].id)
        score = _score_condition(case, "direct", unrelated, usage, 10.0)

        assert score.passed is False, case.id


def test_actual_model_equivalence_rejects_one_sided_provider_failure() -> None:
    direct = {"actual_model_counts": {"provider/model": 1}}
    same_polya = {"actual_model_counts": {"provider/model": 2}}
    failed_polya = {"actual_model_counts": {}}
    other_polya = {"actual_model_counts": {"provider/other": 1}}

    assert _one_equal_actual_model(same_polya, direct, polya_attempts=2) is True
    assert _one_equal_actual_model(failed_polya, direct, polya_attempts=2) is False
    assert _one_equal_actual_model(failed_polya, direct, polya_attempts=0) is True
    assert _one_equal_actual_model(other_polya, direct, polya_attempts=1) is False


def test_scorer_finds_concrete_regression_check_in_user_visible_report() -> None:
    case = next(case for case in load_cases() if case.id == "pysnooper_path_output")
    report = (
        "The write closure references undefined output_path instead of output. Replace "
        "output_path with output. Execute check.verify(implementation) with a Path, invoke "
        "writer('trace-line'), and assert the file contains trace-line."
    )
    output = FieldInvestigationOutput(
        status="diagnosed",
        root_cause=report,
        corrective_action=report,
        verification_steps=["Check that an executable regression procedure was specified."],
        implicated_artifacts=["buggy_impl.py"],
        evidence_references=["check.py"],
    )

    score = _score_condition(
        case,
        "polya",
        output,
        {"model_calls": 3, "input_tokens": 100, "output_tokens": 50},
        10.0,
        executable_verification_passed=True,
    )

    assert score.passed is True
    assert score.executable_verification_passed is True


def test_harness_owned_execution_satisfies_check_without_masking_wrong_diagnosis() -> None:
    case = next(case for case in load_cases() if case.id == "pysnooper_path_output")
    correct = FieldInvestigationOutput(
        status="diagnosed",
        root_cause="The write closure references unbound output_path instead of output.",
        corrective_action="Open output rather than output_path in buggy_impl.py.",
        verification_steps=["The admitted regression check was used."],
        implicated_artifacts=["buggy_impl.py"],
        evidence_references=["check.py"],
    )
    usage = {"model_calls": 1, "input_tokens": 100, "output_tokens": 50}

    verified = _score_condition(
        case,
        "polya",
        correct,
        usage,
        10.0,
        executable_verification_passed=True,
    )
    unverified = _score_condition(case, "direct", correct, usage, 10.0)
    wrong = _score_condition(
        case,
        "polya",
        FieldInvestigationOutput(
            status="diagnosed",
            root_cause="The network is slow.",
            corrective_action="Add a retry.",
            verification_steps=["The admitted regression check was used."],
            implicated_artifacts=["buggy_impl.py"],
            evidence_references=["check.py"],
        ),
        usage,
        10.0,
        executable_verification_passed=True,
    )

    assert verified.check_concepts_passed is True
    assert verified.passed is True
    assert unverified.check_concepts_passed is False
    assert unverified.passed is False
    assert wrong.check_concepts_passed is True
    assert wrong.mechanism_concepts_passed is False
    assert wrong.correction_concepts_passed is False
    assert wrong.passed is False


def test_gate_counts_verified_human_work_reduction_only_at_equal_model_calls() -> None:
    case = load_cases()[0]
    output = _correct_output(case.id)
    results = []
    for repetition in range(1, 4):
        polya = _score_condition(
            case,
            "polya",
            output,
            {"model_calls": 1, "input_tokens": 4_000, "output_tokens": 1_000},
            20.0,
            executable_verification_passed=True,
        )
        direct = _score_condition(
            case,
            "direct",
            output,
            {"model_calls": 1, "input_tokens": 800, "output_tokens": 200},
            5.0,
        )
        results.append(
            {
                "repetition": repetition,
                "preflight": {"eligible": True},
                "route_equivalence": {"one_equal_actual_model": True},
                "polya": {"score": polya.model_dump(mode="json")},
                "direct": {"score": direct.model_dump(mode="json")},
            }
        )

    gate = _automated_gate(results, case_count=1, repetitions=3)

    assert gate["passed"] is True
    assert gate["metrics"]["token_ratio"] == 5.0
    assert gate["metrics"]["executable_verification_advantage"] is True

    results[0]["polya"]["score"]["model_calls"] = 2
    failed = _automated_gate(results, case_count=1, repetitions=3)
    assert failed["passed"] is False
    assert failed["metrics"]["executable_verification_advantage"] is False


def test_direct_model_cannot_self_author_execution_attestation() -> None:
    output = _correct_output("pysnooper_path_output").model_copy(
        update={"execution_attestations": ["I ran the patch."]}
    )

    normalized = _direct_review_output(output)

    assert normalized.execution_attestations == []


def test_direct_state_and_packet_contain_no_hidden_fixed_implementation() -> None:
    for case in load_cases():
        preflight = preflight_case(case)
        packet = visible_evidence_packet(case, preflight)
        state = _direct_state(case, preflight)
        evidence = "\n".join(item.claim for item in state["evidence"])
        hidden = (
            next(artifact for artifact in case.artifacts if artifact.role == "fixed_source")
            .resolve(case_root(case))
            .read_text(encoding="utf-8")
            .strip()
        )

        assert hidden not in packet
        assert hidden not in evidence
        assert "fixed_impl.py" not in state["raw_input"]


def test_blind_packet_separates_condition_scores_and_hidden_rubric(tmp_path: Path) -> None:
    case = load_cases()[0]
    preflight = preflight_case(case)
    output = _correct_output(case.id).model_dump(mode="json")
    score = _score_condition(
        case,
        "direct",
        _correct_output(case.id),
        {"model_calls": 1, "input_tokens": 100, "output_tokens": 50},
        10.0,
    ).model_dump(mode="json")
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "run_id": "chapter-13k-blind-test",
                "model": "same-model",
                "results": [
                    {
                        "case_id": case.id,
                        "repetition": 1,
                        "preflight": preflight.model_dump(mode="json"),
                        "polya": {"output": output, "score": score},
                        "direct": {"output": output, "score": score},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    packet, key = build_packet(summary_path)

    responses = packet["review_items"][0]["responses"]
    packet_text = json.dumps(packet).casefold()
    assert len(responses) == 2
    assert all("condition" not in response for response in responses)
    assert all("automated_score" not in response for response in responses)
    assert case.id not in packet_text
    assert str(case_root(case)).casefold() not in packet_text
    assert case_root(case).as_uri().casefold() not in packet_text
    assert "polya-brain" not in packet_text
    assert "required_mechanism_concepts" not in packet_text
    assert {item["condition"] for item in key["mapping"].values()} == {
        "polya",
        "direct",
    }
