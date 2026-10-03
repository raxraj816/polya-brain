"""Partial sampling cannot silently become a clean verification certificate."""

import pytest

from app.execution import DockerPythonSandbox, DockerSandboxLimits, image_available
from app.verified_coding.harness import Entrypoint, HarnessConfig, build_program, parse_result


@pytest.fixture
def sandbox():
    runner = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5))
    if not image_available(runner.image):
        pytest.skip("pinned Docker image unavailable")
    return runner


@pytest.mark.parametrize("failure", ["generator", "reference", "scale", "scale_args"])
def test_partial_sampling_does_not_agree(sandbox, failure):
    source = "def f(n): return n"
    generator = "def generate(rng, size): return (size,)"
    reference = source
    if failure == "generator":
        generator = "def generate(rng, size):\n    if size: raise ValueError('missing region')\n    return (0,)"
    elif failure == "reference":
        reference = "def f(n):\n    if n:\n        while True: pass\n    return n"
    elif failure == "scale":
        generator += "\ndef scale_inputs(rng): raise ValueError('missing scale')"
    else:
        generator += "\ndef scale_inputs(rng): return [123]"
    result = parse_result(
        sandbox.execute(
            build_program(
                candidate=source,
                reference=reference,
                tools=generator,
                config=HarnessConfig(
                    entrypoint=Entrypoint(name="f"),
                    max_size=1,
                    max_cases=6,
                    budget_seconds=1,
                    call_seconds=0.01,
                ),
            )
        )
    )
    assert result.cases_compared > 0
    assert not result.agrees


def package(failing=True):
    from test_verified_change import response

    return response(
        {
            "generator_code": (
                "def generate(rng, size):\n"
                + ("    if size: raise ValueError('missing region')\n" if failing else "")
                + "    return (size,)"
            )
        }
    )


@pytest.mark.parametrize("recover", [False, True])
def test_change_pipeline_retries_missing_coverage_and_discloses_final_status(
    sandbox, tmp_path, recover
):
    from app.llm import FakeLLMClient
    from app.verified_change.pipeline import ChangeLimits, ChangeStatus, ChangeVerifier
    from app.verified_change.report import render
    from app.verified_change.source import ModuleVersions, analyse

    versions = ModuleVersions(
        tmp_path, "f.py", "old", "new", "def f(n): return n", "def f(n): return n + 0"
    )
    client = FakeLLMClient([package(), package(not recover)])
    outcome = ChangeVerifier(
        client, "fake-model", sandbox, limits=ChangeLimits(differential_budget_seconds=0.3)
    ).verify(versions, analyse(versions, "f"), "No behavior change.")
    assert outcome.certificate.status is (
        ChangeStatus.NO_DIFFERENCE if recover else ChangeStatus.UNVERIFIED
    )
    assert len(client.requests) == 2
    assert outcome.certificate.cases_compared > 0
    if not recover:
        assert "generator" in render(outcome).lower()
        assert outcome.differential.generator_errors > 0
    (tmp_path / "report.md").write_text(render(outcome))


def test_change_counterexample_survives_incomplete_sampling(sandbox, tmp_path):
    from app.llm import FakeLLMClient
    from app.verified_change.pipeline import ChangeLimits, ChangeStatus, ChangeVerifier
    from app.verified_change.report import render
    from app.verified_change.source import ModuleVersions, analyse

    versions = ModuleVersions(
        tmp_path, "f.py", "old", "new", "def f(n): return n", "def f(n): return n + 1"
    )
    outcome = ChangeVerifier(
        FakeLLMClient([package()]),
        "fake-model",
        sandbox,
        limits=ChangeLimits(differential_budget_seconds=0.3),
    ).verify(versions, analyse(versions, "f"), "No behavior change.")
    assert outcome.certificate.status is ChangeStatus.REGRESSIONS
    assert outcome.certificate.differences
    assert "generator errors" in render(outcome).lower()


def test_coding_pipeline_cannot_certify_partial_sampling(sandbox):
    from test_verified_coding import response

    from app.llm import FakeLLMClient
    from app.verified_coding.contracts import CertificateStatus
    from app.verified_coding.pipeline import PipelineLimits, VerifiedCodingPipeline
    from app.verified_coding.projection import project

    oracle = response(
        {
            "entrypoint": {"name": "f"},
            "reference_code": "def f(n): return n",
            "generator_code": "def generate(rng, size):\n    if size: raise ValueError('missing region')\n    return (0,)",
        }
    )
    client = FakeLLMClient(
        [
            response(
                {
                    "code": "def f(n): return n",
                    "tests": ["assert f(0) == 0"],
                    "explanation": "identity",
                }
            ),
            oracle,
            oracle,
        ]
    )
    outcome = VerifiedCodingPipeline(
        client, "fake-model", sandbox, limits=PipelineLimits(differential_budget_seconds=0.3)
    ).run("Implement f(n: int) -> int returning its argument.")
    assert outcome.certificate.status is CertificateStatus.UNVERIFIED
    assert outcome.certificate.cases_compared > 0
    assert outcome.certificate.final_differential.generator_errors > 0
    _, state = project(outcome, raw_input="Implement identity.")
    assert not state["verification"].passed
    assert "generator" in state["final_answer"].lower()


def test_repaired_candidate_still_requires_complete_sampling(sandbox, monkeypatch):
    from test_verified_coding import GOOD, HALF_OPEN, PROBLEM, QUOTE, oracle, proposal, response

    from app.llm import FakeLLMClient
    from app.verified_coding.contracts import CertificateStatus
    from app.verified_coding.harness import DifferentialResult, Disagreement
    from app.verified_coding.pipeline import VerifiedCodingPipeline

    client = FakeLLMClient(
        [
            proposal(HALF_OPEN),
            oracle(),
            response(
                {
                    "verdict": "candidate_wrong",
                    "expected": "1",
                    "governing_requirement": QUOTE,
                    "repaired_candidate_code": GOOD,
                }
            ),
        ]
    )
    pipeline = VerifiedCodingPipeline(client, "fake-model", sandbox)
    results = iter(
        [
            DifferentialResult(
                cases_compared=1,
                disagreements=1,
                counterexamples=[
                    Disagreement(
                        kind="output_mismatch",
                        size=1,
                        args="([(1, 2), (2, 3)], 0)",
                        candidate="2",
                        reference="1",
                    )
                ],
            ),
            DifferentialResult(cases_compared=8, generator_errors=2),
        ]
    )
    monkeypatch.setattr(pipeline, "_differential", lambda **kwargs: next(results))
    outcome = pipeline.run(PROBLEM)
    assert outcome.certificate.status is CertificateStatus.UNVERIFIED
    assert outcome.certificate.findings[0].resolved
    assert outcome.certificate.final_differential.generator_errors == 2


def test_only_intended_differences_cannot_hide_incomplete_coverage(sandbox, tmp_path):
    from test_verified_change import response

    from app.llm import FakeLLMClient
    from app.verified_change.pipeline import ChangeLimits, ChangeStatus, ChangeVerifier
    from app.verified_change.source import ModuleVersions, analyse

    intent = "Increase the returned value by one for every input."
    versions = ModuleVersions(
        tmp_path, "f.py", "old", "new", "def f(n): return n", "def f(n): return n + 1"
    )
    client = FakeLLMClient(
        [
            package(),
            response(
                {
                    "items": [
                        {
                            "index": 0,
                            "verdict": "intended",
                            "intent_quote": intent,
                            "explanation": "one larger",
                        }
                    ]
                }
            ),
        ]
    )
    outcome = ChangeVerifier(
        client, "fake-model", sandbox, limits=ChangeLimits(differential_budget_seconds=0.3)
    ).verify(versions, analyse(versions, "f"), intent)
    assert outcome.certificate.status is ChangeStatus.UNVERIFIED
    assert outcome.certificate.differences[0].verdict == "intended"
    assert "generator errors" in outcome.certificate.reason
