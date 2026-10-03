"""Lean-first differential verification: deterministic guards and sandboxed pipeline runs."""

from __future__ import annotations

import json
import shutil

import pytest

from app.execution import DockerPythonSandbox, DockerSandboxLimits, image_available
from app.execution.sandbox import SandboxExecutionResult
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.verified_coding.contracts import Adjudication, CertificateStatus, Verdict
from app.verified_coding.harness import (
    MAX_SANDBOX_CODE,
    Entrypoint,
    Example,
    HarnessConfig,
    build_program,
    parse_result,
)
from app.verified_coding.pipeline import (
    PipelineLimits,
    VerifiedCodingPipeline,
    quote_supported,
    sourced_examples,
)

PROBLEM = (
    "Implement max_meetings(meetings: list[tuple[int, int]], gap: int) -> int. Each meeting "
    "(s, e) with s <= e occupies the CLOSED time interval [s, e] in a single room. After a "
    "meeting ends at time e the room needs gap units of cleanup, so the next meeting held in "
    "the room must start at a time strictly greater than e + gap. Return the maximum number "
    "of meetings. Examples: max_meetings([(1,2),(2,3)],0)==1; max_meetings([(1,2),(3,4)],1)==1."
)
GOOD = (
    "def max_meetings(meetings, gap):\n"
    "    count, boundary = 0, None\n"
    "    for s, e in sorted(meetings, key=lambda m: m[1]):\n"
    "        if boundary is None or s > boundary:\n"
    "            count += 1\n"
    "            boundary = e + gap\n"
    "    return count\n"
)
HALF_OPEN = GOOD.replace("s > boundary", "s >= boundary")
REFERENCE = (
    "def max_meetings(meetings, gap):\n"
    "    best = 0\n"
    "    for mask in range(1 << len(meetings)):\n"
    "        chosen = sorted(meetings[i] for i in range(len(meetings)) if mask >> i & 1)\n"
    "        if all(chosen[k + 1][0] > chosen[k][1] + gap for k in range(len(chosen) - 1)):\n"
    "            best = max(best, len(chosen))\n"
    "    return best\n"
)
GENERATOR = (
    "def generate(rng, size):\n"
    "    meetings = []\n"
    "    for _ in range(min(size, 7)):\n"
    "        s = rng.randrange(-4, 8)\n"
    "        meetings.append((s, s + rng.randrange(0, 3)))\n"
    "    return (meetings, rng.randrange(0, 3))\n"
)
QUOTE = "the next meeting held in the room must start at a time strictly greater than e + gap"


def response(payload: object) -> LLMResponse:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return LLMResponse(
        provider="fake",
        model="fake-model",
        text=text,
        usage=LLMTokenUsage(input_tokens=100, output_tokens=50, estimated_cost_usd=0.001),
    )


def proposal(code: str = GOOD) -> LLMResponse:
    return response(
        {
            "code": code,
            "tests": ["assert max_meetings([(1, 2), (3, 4)], 0) == 2"],
            "explanation": "Greedy by end time.",
        }
    )


def oracle(reference: str = REFERENCE, examples: list[dict[str, str]] | None = None) -> LLMResponse:
    return response(
        {
            "entrypoint": {"name": "max_meetings", "class_name": None},
            "reference_code": reference,
            "generator_code": GENERATOR,
            "examples": examples
            if examples is not None
            else [
                {"call": "max_meetings([(1,2),(2,3)],0)", "expected": "1"},
                {"call": "max_meetings([(1,2),(3,4)],1)", "expected": "1"},
            ],
            "scale_code": "",
            "same_code": "",
            "assumptions": [],
            "unexpected_extra_key": "ignored",
        }
    )


# ----- deterministic guards (no sandbox) -----------------------------------


def test_sourced_examples_drop_invented_examples() -> None:
    kept, dropped = sourced_examples(
        PROBLEM,
        [
            Example(call="max_meetings([(1, 2), (2, 3)], 0)", expected="1"),
            Example(call="max_meetings([(9,9)],0)", expected="1"),
            Example(call="max_meetings([(1,2),(3,4)],1)", expected="7"),
        ],
    )
    assert [item.call for item in kept] == ["max_meetings([(1, 2), (2, 3)], 0)"]
    assert dropped == 2


def test_quote_must_be_problem_text() -> None:
    assert quote_supported(PROBLEM, QUOTE)
    assert quote_supported(PROBLEM, "  Strictly greater than e + gap. ")
    assert not quote_supported(PROBLEM, "meetings may touch at their endpoints")
    assert not quote_supported(PROBLEM, "gap")


def test_consistency_rejects_self_contradicting_rulings() -> None:
    check = VerifiedCodingPipeline._consistency_failure
    wrong_side = Adjudication(verdict=Verdict.CANDIDATE_WRONG, expected="2")
    assert check(wrong_side, candidate_output="2", reference_output="1", stated_expected=None)
    not_literal = Adjudication(verdict=Verdict.CANDIDATE_WRONG, expected="10**9")
    assert check(not_literal, candidate_output="2", reference_output="1", stated_expected=None)
    contradicts_example = Adjudication(verdict=Verdict.CANDIDATE_WRONG, expected="2")
    assert check(
        contradicts_example, candidate_output="3", reference_output="2", stated_expected="1"
    )
    consistent = Adjudication(verdict=Verdict.CANDIDATE_WRONG, expected="1")
    assert (
        check(consistent, candidate_output="2", reference_output="1", stated_expected=None) is None
    )
    reference_wrong = Adjudication(verdict=Verdict.REFERENCE_WRONG, expected="2")
    assert (
        check(reference_wrong, candidate_output="2", reference_output="1", stated_expected=None)
        is None
    )


def test_program_size_is_bounded_and_missing_marker_is_setup_error() -> None:
    config = HarnessConfig(entrypoint=Entrypoint(name="f"))
    noise = "".join(f"x{i} = {i * 7919 % 104729}\n" for i in range(9000))
    with pytest.raises(ValueError, match="sandbox admits"):
        build_program(candidate=noise, reference=noise, tools=noise, config=config)
    assert len(
        build_program(candidate=GOOD, reference=REFERENCE, tools=GENERATOR, config=config)
    ) < (MAX_SANDBOX_CODE // 2)
    missing = parse_result(
        SandboxExecutionResult(exit_code=1, stdout="", stderr="Boom\n", runtime_ms=1, tests_run=0)
    )
    assert missing.setup_error is not None and not missing.agrees


# ----- sandboxed pipeline runs ---------------------------------------------


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return image_available(DockerPythonSandbox().image)


docker = pytest.mark.skipif(not _docker_available(), reason="Docker sandbox image unavailable")


def run(script: list[LLMResponse]) -> tuple[object, FakeLLMClient]:
    client = FakeLLMClient(script)
    pipeline = VerifiedCodingPipeline(
        client,
        "fake-model",
        DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
        limits=PipelineLimits(differential_budget_seconds=3.0),
    )
    return pipeline.run(PROBLEM), client


@docker
def test_correct_candidate_is_verified_with_two_model_calls() -> None:
    outcome, client = run([proposal(), oracle()])
    certificate = outcome.certificate  # type: ignore[attr-defined]
    assert certificate.status is CertificateStatus.VERIFIED
    assert certificate.cases_compared > 100
    assert certificate.examples_sourced == 2
    assert len(client.requests) == 2
    oracle_request = client.requests[1].messages[0].content
    assert "s >= boundary" not in oracle_request and "def max_meetings" not in oracle_request
    assert outcome.code == GOOD  # type: ignore[attr-defined]


@docker
def test_misread_candidate_is_caught_adjudicated_and_repaired() -> None:
    ruling = {
        "verdict": "candidate_wrong",
        "expected": "1",
        "governing_requirement": QUOTE,
        "explanation": "Touching meetings share an instant.",
        "repaired_candidate_code": GOOD,
        "repaired_reference_code": "",
        "relaxation": "",
        "question": "",
    }
    outcome, client = run([proposal(HALF_OPEN), oracle(), response(ruling)])
    certificate = outcome.certificate  # type: ignore[attr-defined]
    assert certificate.status is CertificateStatus.REPAIRED
    assert outcome.code == GOOD  # type: ignore[attr-defined]
    finding = certificate.findings[0]
    assert finding.source == "stated_example" and finding.resolved
    assert finding.governing_requirement == QUOTE
    assert len(client.requests) == 3
    adjudication_request = client.requests[2].messages[0].content
    assert "the problem states the expected output is 1" in adjudication_request


@docker
def test_wrong_reference_is_repaired_without_touching_the_candidate() -> None:
    sloppy = REFERENCE.replace("> chosen[k][1] + gap", ">= chosen[k][1] + gap")
    ruling = {
        "verdict": "reference_wrong",
        "expected": "1",
        "governing_requirement": QUOTE,
        "explanation": "The reference allowed touching meetings.",
        "repaired_candidate_code": "",
        "repaired_reference_code": REFERENCE,
    }
    outcome, _ = run([proposal(), oracle(sloppy), response(ruling)])
    certificate = outcome.certificate  # type: ignore[attr-defined]
    assert certificate.status is CertificateStatus.VERIFIED
    assert outcome.code == GOOD  # type: ignore[attr-defined]


@docker
def test_unsupported_ruling_is_not_applied() -> None:
    ruling = {
        "verdict": "candidate_wrong",
        "expected": "1",
        "governing_requirement": "meetings must never touch under any circumstance",
        "repaired_candidate_code": GOOD,
    }
    outcome, _ = run([proposal(HALF_OPEN), oracle(examples=[]), response(ruling)])
    certificate = outcome.certificate  # type: ignore[attr-defined]
    assert certificate.status is CertificateStatus.DISPUTED
    assert outcome.code == HALF_OPEN  # type: ignore[attr-defined]
    assert not certificate.findings[0].resolved


@docker
def test_ambiguous_specification_becomes_an_open_question() -> None:
    ruling = {"verdict": "ambiguous", "question": "Do meetings that touch at an endpoint conflict?"}
    outcome, _ = run([proposal(HALF_OPEN), oracle(examples=[]), response(ruling)])
    certificate = outcome.certificate  # type: ignore[attr-defined]
    assert certificate.status is CertificateStatus.AMBIGUOUS
    assert certificate.open_question == "Do meetings that touch at an endpoint conflict?"


@docker
def test_unusable_oracle_is_reported_unverified() -> None:
    broken = response({"entrypoint": {"name": "max_meetings"}, "reference_code": "x"})
    outcome, client = run([proposal(), broken, response("not json")])
    certificate = outcome.certificate  # type: ignore[attr-defined]
    assert certificate.status is CertificateStatus.UNVERIFIED
    assert outcome.code == GOOD  # type: ignore[attr-defined]
    assert len(client.requests) == 3


@docker
def test_oracle_generator_failure_gets_one_feedback_retry() -> None:
    bad_generator = json.loads(oracle().text)
    bad_generator["generator_code"] = "def generate(rng, size):\n    return [1, 2]\n"
    outcome, client = run([proposal(), response(bad_generator), oracle()])
    assert outcome.certificate.status is CertificateStatus.VERIFIED  # type: ignore[attr-defined]
    assert "YOUR PREVIOUS ORACLE COULD NOT BE USED" in client.requests[2].messages[0].content


@docker
def test_inconsistent_ruling_leaves_candidate_disputed() -> None:
    ruling = {
        "verdict": "candidate_wrong",
        "expected": "2",
        "governing_requirement": QUOTE,
        "repaired_candidate_code": GOOD,
    }
    outcome, _ = run([proposal(HALF_OPEN), oracle(), response(ruling)])
    assert outcome.certificate.status is CertificateStatus.DISPUTED  # type: ignore[attr-defined]
    assert outcome.code == HALF_OPEN  # type: ignore[attr-defined]


# ----- routing, runtime fast path and report projection --------------------


@pytest.mark.parametrize(
    "text",
    [
        PROBLEM,
        "Implement Python class Solution with method findMedianSortedArrays(self, nums1: list[int], nums2: list[int]) -> float.",
        "Write covered_count(intervals: list[tuple[int, int]]) -> int that counts covered points.",
    ],
)
def test_self_contained_implementations_route_to_verified_coding(text: str) -> None:
    from app.verified_coding.runtime import route_reason

    assert route_reason(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "Our API p95 latency jumped after deploy. Should we add Redis or inspect queries first?",
        "Implement retry logic in our repository's client.py so uploads stop failing.",
        "Why does merge_ranges(xs) -> list return duplicates in production?",
        "Explain how quicksort works.",
        "Implement a cache.",
    ],
)
def test_investigations_and_vague_requests_stay_on_the_kernel(text: str) -> None:
    from app.verified_coding.runtime import route_reason

    assert route_reason(text) is None


def fast_path(script: list[LLMResponse], max_model_calls: int = 12) -> object:
    from app.cognition.task_model import CognitiveResourceBudget
    from app.verified_coding.runtime import VerifiedCodingFastPath

    return VerifiedCodingFastPath(
        FakeLLMClient(script),
        "fake-model",
        image=DockerPythonSandbox().image,
        memory_megabytes=64,
        budget=CognitiveResourceBudget(max_model_calls=max_model_calls),
        limits=PipelineLimits(differential_budget_seconds=3.0),
    )


def test_fast_path_declines_seed_evidence_small_budgets_and_investigations() -> None:
    from app.models.contracts import EvidenceItem

    seed = [EvidenceItem(source_type="user", source_uri="file://x", claim="context")]
    path = fast_path([])
    assert path(PROBLEM, session_id=None, seed_evidence=seed, checkpoint=None) is None  # type: ignore[operator]
    assert (
        fast_path([], max_model_calls=3)(
            PROBLEM, session_id=None, seed_evidence=None, checkpoint=None
        )  # type: ignore[operator]
        is None
    )
    assert path("Explain quicksort.", session_id=None, seed_evidence=None, checkpoint=None) is None  # type: ignore[operator]


@docker
def test_fast_path_delivers_a_verified_contract_valid_state() -> None:
    from evals.chapter_13p.coding_execution.evidence import extract_code

    from app.cognition.contracts import CognitiveRunStatus
    from app.cognition.task_model import accumulated_usage
    from app.investigator.artifacts import report_from_result

    checkpoints: list[tuple[int, bool]] = []
    path = fast_path(
        [
            proposal(HALF_OPEN),
            oracle(),
            response(
                {
                    "verdict": "candidate_wrong",
                    "expected": "1",
                    "governing_requirement": QUOTE,
                    "explanation": "Touching meetings share time 2.",
                    "repaired_candidate_code": GOOD,
                }
            ),
        ]
    )
    result = path(  # type: ignore[operator]
        PROBLEM,
        session_id="11111111-1111-4111-8111-111111111111",
        seed_evidence=None,
        checkpoint=lambda state, in_flight: checkpoints.append((len(state["events"]), in_flight)),
    )
    assert result is not None
    assert result.status is CognitiveRunStatus.COMPLETED
    state = result.state
    assert state["verification"] is not None and state["verification"].passed
    assert extract_code(state["final_answer"]) == GOOD.strip()
    assert "Repaired and verified" in state["final_answer"]
    assert accumulated_usage(state).model_calls == 3
    assert any(item.source_type == "differential_execution" for item in state["evidence"])
    assert any(item.contradicts_hypothesis_ids for item in state["evidence"])
    assert state["reflection"] is not None and state["reflection"].reusable_lessons
    assert checkpoints[-1][1] is False
    assert [count for count, _ in checkpoints] == sorted(count for count, _ in checkpoints)
    assert checkpoints[-1][0] == len(state["events"])
    report = report_from_result(result)
    assert report.verification_status == "passed"
    assert report.evidence_against and report.checks_performed


@docker
def test_disputed_outcome_is_not_reported_as_verified() -> None:
    from app.cognition.contracts import CognitiveRunStatus
    from app.investigator.artifacts import report_from_result

    path = fast_path([proposal(HALF_OPEN), oracle(examples=[]), response("{}"), response("{}")])
    result = path(PROBLEM, session_id=None, seed_evidence=None, checkpoint=None)  # type: ignore[operator]
    assert result is not None and result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert result.state["verification"] is not None and not result.state["verification"].passed
    assert "Not verified" in result.state["final_answer"]
    report = report_from_result(result)
    assert report.verification_status != "passed"
    assert report.final_conclusion == "No verified conclusion is available."


class _DeadDaemon:
    limits = DockerSandboxLimits(timeout_seconds=5)

    def execute(self, code: str, tests: object = ()) -> SandboxExecutionResult:
        return SandboxExecutionResult(
            exit_code=1,
            stdout="",
            stderr="failed to connect to the docker API at unix:///x/docker.sock\n",
            runtime_ms=3,
            tests_run=1,
        )


def test_sandbox_outage_stops_instead_of_blaming_the_code() -> None:
    from app.cognition.contracts import CognitiveRunStatus
    from app.cognition.task_model import CognitiveResourceBudget
    from app.verified_coding.pipeline import SandboxUnavailable
    from app.verified_coding.runtime import VerifiedCodingFastPath

    client = FakeLLMClient([proposal(), proposal()])
    pipeline = VerifiedCodingPipeline(client, "fake-model", _DeadDaemon())
    with pytest.raises(SandboxUnavailable):
        pipeline.solve(PROBLEM)
    assert len(client.requests) == 1  # the outage was never fed back to the model

    path = VerifiedCodingFastPath(
        FakeLLMClient([proposal()]),
        "fake-model",
        image="unused",
        memory_megabytes=64,
        budget=CognitiveResourceBudget(),
        sandbox_factory=_DeadDaemon,  # type: ignore[arg-type]
    )
    result = path(PROBLEM, session_id=None, seed_evidence=None, checkpoint=None)
    assert result is not None and result.status is CognitiveRunStatus.FAILED
    assert result.state["final_answer"] is None
    assert result.state["events"][-1].event_type == "verified_coding_failed"


@docker
def test_reference_self_correction_is_not_presented_as_a_draft_defect() -> None:
    from app.verified_coding.projection import project

    sloppy = REFERENCE.replace("> chosen[k][1] + gap", ">= chosen[k][1] + gap")
    ruling = {
        "verdict": "reference_wrong",
        "expected": "1",
        "governing_requirement": QUOTE,
        "repaired_reference_code": REFERENCE,
    }
    outcome, _ = run([proposal(), oracle(sloppy), response(ruling)])
    _, state = project(outcome, raw_input=PROBLEM)  # type: ignore[arg-type]
    answer = state["final_answer"] or ""
    assert "Verifier self-corrections (the draft was right)" in answer
    assert "found in the draft" not in answer
    assert not any(item.contradicts_hypothesis_ids for item in state["evidence"])
    assert state["reflection"] is not None and not state["reflection"].reusable_lessons


def test_newline_joined_assertions_are_split_and_schema_errors_are_specific() -> None:
    from pydantic import ValidationError

    from app.verified_coding.pipeline import parse_proposal, schema_feedback

    text = json.dumps(
        {
            "code": GOOD,
            "tests": "assert max_meetings([], 0) == 0\nassert max_meetings(\n    [(1, 2)], 0) == 1\n",
            "explanation": "x",
        }
    )
    proposal = parse_proposal(text)
    assert proposal.tests == [
        "assert max_meetings([], 0) == 0",
        "assert max_meetings(\n    [(1, 2)], 0) == 1",
    ]
    with pytest.raises(ValidationError) as caught:
        parse_proposal(json.dumps({"code": GOOD, "tests": [], "explanation": "x"}))
    feedback = schema_feedback(caught.value)
    assert "tests" in feedback and '"tests": [string, ...]' in feedback
