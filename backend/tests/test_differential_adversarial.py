"""Adversarial developer controls for false agreement, not solver-quality evidence."""

import json

import pytest

from app.execution import DockerPythonSandbox, DockerSandboxLimits, image_available
from app.execution.sandbox import SandboxExecutionResult
from app.verified_coding.harness import (
    RESULT_MARKER,
    Entrypoint,
    Example,
    HarnessConfig,
    Regression,
    build_program,
    parse_result,
)


@pytest.fixture
def sandbox():
    runner = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5))
    if not image_available(runner.image):
        pytest.skip("pinned Docker image unavailable")
    return runner


def compare(sandbox, candidate, reference, **options):
    config = HarnessConfig(
        entrypoint=Entrypoint(name="f"), max_cases=8, budget_seconds=1, **options
    )
    execution = sandbox.execute(
        build_program(
            candidate=candidate,
            reference=reference,
            tools="def generate(rng, size): return ()",
            config=config,
        )
    )
    return parse_result(execution)


@pytest.mark.parametrize(
    "candidate,reference,relaxations",
    [
        ("{True: 'value'}", "{1: 'value'}", []),
        ("{1.0: 'value'}", "{1: 'value'}", []),
        ("{'nested': {False: 'value'}}", "{'nested': {0: 'value'}}", []),
        ("{True}", "{1}", []),
        ("{1.0}", "{1}", []),
        ("frozenset([1])", "{1}", []),
        ("[True, 2]", "[1, 2]", ["unordered"]),
        ("[[True], [2]]", "[[1], [2]]", ["unordered"]),
        ("[1.0, 2]", "[1, 2]", ["unordered"]),
        ("{True}", "{1}", ["numeric_type"]),
    ],
)
def test_container_type_changes_cannot_be_certified(sandbox, candidate, reference, relaxations):
    result = compare(
        sandbox,
        f"def f(): return {candidate}",
        f"def f(): return {reference}",
        relaxations=relaxations,
    )
    assert result.setup_error is None
    assert not result.agrees
    assert result.disagreements > 0
    assert result.counterexamples


@pytest.mark.parametrize(
    "candidate,reference,relaxations",
    [
        ("{'b': 2, 'a': 1}", "{'a': 1, 'b': 2}", []),
        ("{1, 2}", "{2, 1}", []),
        ("[2, 1]", "[1, 2]", ["unordered"]),
        ("[2.0, 1.0]", "[1, 2]", ["unordered", "numeric_type"]),
        ("{1.0: 'v'}", "{1: 'v'}", ["numeric_type"]),
    ],
)
def test_equivalent_containers_keep_supported_relaxations(
    sandbox, candidate, reference, relaxations
):
    result = compare(
        sandbox,
        f"def f(): return {candidate}",
        f"def f(): return {reference}",
        relaxations=relaxations,
    )
    assert result.agrees, result.model_dump()


def test_agreeing_but_wrong_boolean_cannot_satisfy_stated_integer_example(sandbox):
    result = compare(
        sandbox,
        "def f(): return True",
        "def f(): return True",
        examples=[Example(call="f()", expected="1")],
    )
    assert not result.agrees
    assert result.candidate_example_failures and result.reference_example_failures


@pytest.mark.parametrize("tail", ["10001", "-1"])
def test_equal_truncated_iterator_prefix_is_unverified(sandbox, tail):
    prefix = "def f():\n    yield from range(10000)\n    yield "
    result = compare(sandbox, prefix + tail, prefix + "10002")
    assert not result.agrees
    assert result.setup_error and "iterator" in result.setup_error


def test_complete_iterator_at_limit_remains_comparable(sandbox):
    result = compare(
        sandbox, "def f(): yield from range(10000)", "def f(): yield from range(10000)"
    )
    assert result.agrees


@pytest.mark.parametrize("ending", ["return 0", "raise ValueError('invalid')"])
@pytest.mark.parametrize("mode", ["absolute", "relative"])
def test_type_only_argument_mutation_is_detected(sandbox, ending, mode):
    execution = sandbox.execute(
        build_program(
            candidate=f"def f(values):\n    values[0] = True\n    {ending}",
            reference=f"def f(values): {ending}",
            tools="def generate(rng, size): return ([1],)",
            config=HarnessConfig(entrypoint=Entrypoint(name="f"), max_cases=8, mutation_mode=mode),
        )
    )
    result = parse_result(execution)
    assert not result.agrees
    assert result.mutation_detected


def test_plain_object_boolean_field_is_not_an_integer_field(sandbox):
    prefix = "class Box: pass\ndef f():\n    box = Box()\n    box.value = "
    suffix = "\n    return box"
    result = compare(sandbox, prefix + "True" + suffix, prefix + "1" + suffix)
    assert not result.agrees
    assert result.disagreements


def test_incomplete_comparison_reaches_unverified_change_certificate(sandbox, tmp_path):
    from test_verified_change import response

    from app.llm import FakeLLMClient
    from app.verified_change.pipeline import ChangeLimits, ChangeStatus, ChangeVerifier
    from app.verified_change.report import render
    from app.verified_change.source import ModuleVersions, analyse

    source = "def f(): yield from range(10001)"
    versions = ModuleVersions(
        tmp_path, "stream.py", "old", "new", source, source.replace("10001", "10002")
    )
    package = response({"generator_code": "def generate(rng, size): return ()"})
    client = FakeLLMClient([package, package])
    outcome = ChangeVerifier(
        client, "fake-model", sandbox, limits=ChangeLimits(differential_budget_seconds=1)
    ).verify(versions, analyse(versions, "f"), "No behavior change.")
    assert outcome.certificate.status is ChangeStatus.UNVERIFIED
    assert "iterator" in outcome.certificate.reason
    assert len(client.requests) == 2
    report = render(outcome)
    assert report.startswith("# Not verified")
    assert "iterator" in report
    (tmp_path / "report.md").write_text(report)
    (tmp_path / "certificate.json").write_text(outcome.certificate.model_dump_json(indent=2))


def test_incomplete_comparison_reaches_unverified_coding_report(sandbox, tmp_path):
    from test_verified_coding import response

    from app.llm import FakeLLMClient
    from app.verified_coding.contracts import CertificateStatus
    from app.verified_coding.pipeline import PipelineLimits, VerifiedCodingPipeline
    from app.verified_coding.projection import project

    source = "def f(): yield from range(10001)"
    proposal = response({"code": source, "tests": ["assert next(f()) == 0"], "explanation": "x"})
    oracle = response(
        {
            "entrypoint": {"name": "f"},
            "reference_code": source,
            "generator_code": "def generate(rng, size): return ()",
            "examples": [],
            "assumptions": [],
        }
    )
    client = FakeLLMClient([proposal, oracle, oracle])
    outcome = VerifiedCodingPipeline(
        client, "fake-model", sandbox, limits=PipelineLimits(differential_budget_seconds=1)
    ).run("Implement f() yielding every integer from 0 to 10000 inclusive.")
    assert outcome.certificate.status is CertificateStatus.UNVERIFIED
    assert outcome.code.strip() == source
    assert len(client.requests) == 3
    _, state = project(outcome, raw_input="Implement f() yielding 0 through 10000.")
    assert state["verification"] is not None and not state["verification"].passed
    assert state["reflection"] is not None
    assert not state["reflection"].reusable_lessons
    assert state["reflection"].outcome_summary.startswith("Not verified:")
    assert state["final_answer"].startswith("**Not verified:")
    assert "iterator" in state["final_answer"]
    (tmp_path / "report.md").write_text(state["final_answer"])
    (tmp_path / "certificate.json").write_text(outcome.certificate.model_dump_json(indent=2))


@pytest.mark.parametrize(
    "options",
    [
        {"examples": [Example(call="f()", expected="missing_name")]},
        {"regressions": [Regression(args="missing_name", expected="1")]},
        {"regressions": [Regression(args="()", expected="missing_name")]},
    ],
)
def test_unexecutable_required_checks_are_not_silently_dropped(sandbox, options):
    result = compare(sandbox, "def f(): return 1", "def f(): return 1", **options)
    assert not result.agrees
    assert result.setup_error


@pytest.mark.parametrize(
    "flags", [{"exit_code": 1}, {"timed_out": True}, {"output_truncated": True}]
)
def test_failed_sandbox_execution_cannot_promote_a_passing_marker(flags):
    fields = dict(
        exit_code=0,
        stdout=RESULT_MARKER + json.dumps({"cases_compared": 8}),
        stderr="",
        runtime_ms=1,
        tests_run=0,
    )
    fields.update(flags)
    result = parse_result(SandboxExecutionResult(**fields))
    assert result.setup_error
    assert not result.agrees
