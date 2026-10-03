"""Verified changes: read-only git versions, differential behavior, intent classification."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.execution import DockerPythonSandbox, DockerSandboxLimits, image_available
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.verified_change.pipeline import ChangeLimits, ChangeStatus, ChangeVerifier
from app.verified_change.source import ChangeSourceError, analyse, read_versions

ORIGINAL = '''"""Tag helpers."""


def normalize_tags(tags):
    """Return unique, lowercase, stripped tags in first-seen order; drop empty tags."""
    seen = set()
    out = []
    for tag in tags:
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out
'''
SAME_BEHAVIOR = '''"""Tag helpers."""


def normalize_tags(tags):
    """Return unique, lowercase, stripped tags in first-seen order; drop empty tags."""
    cleaned = (tag.strip().lower() for tag in tags)
    return list(dict.fromkeys(tag for tag in cleaned if tag))
'''
SORTED_REGRESSION = '''"""Tag helpers."""


def normalize_tags(tags):
    """Return unique, lowercase, stripped tags in first-seen order; drop empty tags."""
    return sorted({tag.strip().lower() for tag in tags if tag.strip()})
'''
KEEP_CASE = '''"""Tag helpers."""


def normalize_tags(tags):
    """Return unique, stripped tags in first-seen order; drop empty tags."""
    seen = set()
    out = []
    for tag in tags:
        cleaned = tag.strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            out.append(cleaned)
    return out
'''
GENERATOR = (
    "def generate(rng, size):\n"
    "    pool = ['a', 'A', ' b', 'b ', '', '  ', 'C', 'c', 'dd']\n"
    "    return ([rng.choice(pool) for _ in range(size)],)\n"
)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("git unavailable")
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "tags.py").write_text(ORIGINAL)
    git(root, "init", "-q")
    git(root, "-c", "user.email=t@example.com", "-c", "user.name=t", "add", ".")
    git(root, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "base")
    return root


def response(payload: object) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="fake-model",
        text=json.dumps(payload),
        usage=LLMTokenUsage(input_tokens=10, output_tokens=5, estimated_cost_usd=0.0001),
    )


GENERATED = response({"generator_code": GENERATOR, "input_notes": ["duplicates, case, blanks"]})


def test_versions_are_read_without_touching_the_repository(repo: Path) -> None:
    (repo / "pkg" / "tags.py").write_text(SORTED_REGRESSION)
    versions = read_versions(repo, "pkg/tags.py")
    assert versions.old_source == ORIGINAL and versions.new_source == SORTED_REGRESSION
    change = analyse(versions, "normalize_tags")
    assert "sorted(" in change.function_diff and change.module_diff_lines > 0
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True
    ).stdout
    assert status.strip() == "M pkg/tags.py"


@pytest.mark.parametrize(
    "module",
    ["../outside.py", "/etc/passwd.py", "pkg/tags.txt", "pkg/../../x.py"],
)
def test_paths_must_stay_inside_the_repository(repo: Path, module: str) -> None:
    with pytest.raises(ChangeSourceError):
        read_versions(repo, module)


def test_non_stdlib_modules_and_missing_functions_are_refused(repo: Path) -> None:
    (repo / "pkg" / "tags.py").write_text("import requests\n" + ORIGINAL)
    with pytest.raises(ChangeSourceError, match="requests"):
        analyse(read_versions(repo, "pkg/tags.py"), "normalize_tags")
    (repo / "pkg" / "tags.py").write_text(ORIGINAL)
    with pytest.raises(ChangeSourceError, match="not found"):
        analyse(read_versions(repo, "pkg/tags.py"), "missing")
    with pytest.raises(ChangeSourceError):
        read_versions(repo, "pkg/tags.py", base_ref="--upload-pack=evil")


docker = pytest.mark.skipif(
    shutil.which("docker") is None or not image_available(DockerPythonSandbox().image),
    reason="Docker sandbox image unavailable",
)


def verify(repo: Path, new_source: str, intent: str, script: list[LLMResponse]):  # noqa: ANN201
    (repo / "pkg" / "tags.py").write_text(new_source)
    versions = read_versions(repo, "pkg/tags.py")
    client = FakeLLMClient(script)
    verifier = ChangeVerifier(
        client,
        "fake-model",
        DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
        limits=ChangeLimits(differential_budget_seconds=2.0),
    )
    return verifier.verify(versions, analyse(versions, "normalize_tags"), intent), client


@docker
def test_true_refactor_shows_no_behavior_change(repo: Path) -> None:
    outcome, client = verify(
        repo, SAME_BEHAVIOR, "Refactor for speed; no behavior change.", [GENERATED]
    )
    certificate = outcome.certificate
    assert certificate.status is ChangeStatus.NO_DIFFERENCE
    assert certificate.cases_compared > 100 and not certificate.differences
    assert len(client.requests) == 1


@docker
def test_behavior_preserving_intent_turns_every_difference_into_a_regression(repo: Path) -> None:
    outcome, client = verify(
        repo, SORTED_REGRESSION, "Simplify normalize_tags. No behavior change.", [GENERATED]
    )
    certificate = outcome.certificate
    assert certificate.status is ChangeStatus.REGRESSIONS
    assert certificate.behavior_preserving_intent
    assert certificate.differences and all(
        d.verdict == "regression" for d in certificate.differences
    )
    first = certificate.differences[0]
    assert first.old_output != first.new_output
    assert len(client.requests) == 1  # no classification call for preserving intent
    assert len({d.args for d in certificate.differences}) == len(certificate.differences)


@docker
def test_intended_change_needs_a_verbatim_intent_quote(repo: Path) -> None:
    intent = "Keep the original capitalization of each tag instead of lowercasing it."

    def classification(quote: str) -> LLMResponse:
        return response(
            {
                "items": [
                    {"index": i, "verdict": "intended", "intent_quote": quote, "explanation": "x"}
                    for i in range(6)
                ]
            }
        )

    outcome, client = verify(
        repo, KEEP_CASE, intent, [GENERATED, classification("Keep the original capitalization")]
    )
    assert outcome.certificate.status is ChangeStatus.INTENDED_ONLY
    review_prompt = client.requests[1].messages[0].content
    assert intent in review_prompt and "old -> " in review_prompt
    outcome, _ = verify(
        repo, KEEP_CASE, intent, [GENERATED, classification("tags may be reordered")]
    )
    assert outcome.certificate.status is ChangeStatus.UNCLEAR
    assert all(d.verdict == "unclear" for d in outcome.certificate.differences)


@docker
def test_cli_writes_a_certificate_and_report(repo: Path, tmp_path: Path, monkeypatch) -> None:
    from app.investigator.cli import main

    (repo / "pkg" / "tags.py").write_text(SORTED_REGRESSION)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "fake-model")
    monkeypatch.setenv("FAILURE_PATTERNS_PATH", str(tmp_path / "patterns.jsonl"))
    monkeypatch.setattr(
        "app.verified_change.cli.OpenRouterLLMClient.from_settings",
        lambda settings: FakeLLMClient([GENERATED]),
    )
    code = main(
        [
            "verify-change",
            "--repo",
            str(repo),
            "--module",
            "pkg/tags.py",
            "--function",
            "normalize_tags",
            "--intent",
            "Performance refactor; no behavior change.",
            "--output-root",
            str(tmp_path / "out"),
            "--run-id",
            "r1",
        ]
    )
    assert code == 3
    report = (tmp_path / "out" / "r1" / "report.md").read_text()
    assert report.startswith("# Regression found")
    assert "Old (HEAD)" in report and "```diff" in report
    certificate = json.loads((tmp_path / "out" / "r1" / "certificate.json").read_text())
    assert certificate["status"] == "regressions_found"


GENERATOR_BASE = '''def flatten(items):
    """Yield the leaves of a nested list, depth first."""
    for item in items:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item
'''


@docker
def test_generator_results_are_compared_by_what_they_yield(tmp_path: Path) -> None:
    from app.verified_change.source import ModuleVersions

    def check(new_source: str):  # noqa: ANN202
        versions = ModuleVersions(tmp_path, "flat.py", "base", "new", GENERATOR_BASE, new_source)
        script = [
            response(
                {
                    "generator_code": (
                        "def generate(rng, size):\n"
                        "    def build(depth):\n"
                        "        return [build(depth - 1) if depth and rng.random() < .4 else rng.randrange(5)"
                        " for _ in range(rng.randrange(0, 3))]\n"
                        "    return (build(min(size, 3)),)\n"
                    )
                }
            )
        ]
        verifier = ChangeVerifier(
            FakeLLMClient(script),
            "fake-model",
            DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
            limits=ChangeLimits(differential_budget_seconds=2.0),
        )
        return verifier.verify(versions, analyse(versions, "flatten"), "No behavior change.")

    reformatted = GENERATOR_BASE.replace("depth first.", "depth first (refactored).")
    assert check(reformatted).certificate.status is ChangeStatus.NO_DIFFERENCE
    reversed_order = GENERATOR_BASE.replace("for item in items:", "for item in reversed(items):")
    regression = check(reversed_order).certificate
    assert regression.status is ChangeStatus.REGRESSIONS
    assert regression.differences[0].old_output.startswith("generator yielding [")


SORT_BASE = '''class Box:
    def __init__(self, value):
        self.value = value


def tidy(boxes):
    """Sort boxes in place by value and return how many there are."""
    boxes.sort(key=lambda box: box.value)
    return len(boxes)
'''


@docker
def test_objects_compare_structurally_and_mutation_is_relative(tmp_path: Path) -> None:
    from app.verified_change.source import ModuleVersions

    generator = (
        "class Box:\n"
        "    def __init__(self, value):\n"
        "        self.value = value\n"
        "def generate(rng, size):\n"
        "    return ([Box(rng.randrange(4)) for _ in range(size)],)\n"
    )

    def check(new_source: str):  # noqa: ANN202
        versions = ModuleVersions(tmp_path, "box.py", "base", "new", SORT_BASE, new_source)
        verifier = ChangeVerifier(
            FakeLLMClient([response({"generator_code": generator})]),
            "fake-model",
            DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
            limits=ChangeLimits(differential_budget_seconds=2.0),
        )
        return verifier.verify(versions, analyse(versions, "tidy"), "No behavior change.")

    same = SORT_BASE.replace("return len(boxes)", "count = len(boxes)\n    return count")
    assert check(same).certificate.status is ChangeStatus.NO_DIFFERENCE
    stopped_sorting = SORT_BASE.replace("    boxes.sort(key=lambda box: box.value)\n", "")
    changed = check(stopped_sorting).certificate
    assert changed.status is ChangeStatus.REGRESSIONS
    assert changed.differences[0].kind == "input_mutated"
    assert "Box(value=" in changed.differences[0].new_output
