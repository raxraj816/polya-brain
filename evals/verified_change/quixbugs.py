"""QuixBugs catch-rate and false-alarm evaluation for `verify-change`.

For each of the 40 Python programs: the BUG arm treats correct -> buggy as a change
claimed to preserve behavior; the CONTROL arm treats correct -> AST-reformatted
correct as the same claim. A regression on the bug arm is a catch; a regression on
the control arm is a false alarm. The fix's real test cases are never shown to
PolyaBrain; the bundled QuixBugs JSON test cases are only used afterwards to
confirm each bug is observable.

PYTHONPATH=backend:. .venv/bin/python -m evals.verified_change.quixbugs \\
  --quixbugs runs/external/QuixBugs --model google/gemini-3.7-flash \\
  --input-rate 0.00000075 --output-rate 0.00000375 --dollars 0.25 \\
  --programs gcd,sqrt --output runs/verified-change/quixbugs-NEW
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from evals.chapter_13p.coding_execution.budgeted import SpendGuard

from app.config import Settings
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.llm import OpenRouterLLMClient
from app.verified_change.pipeline import PROMPT_VERSION, ChangeLimits, ChangeVerifier
from app.verified_change.source import ModuleVersions, analyse
from app.verified_coding.pipeline import SandboxUnavailable

INTENT = "Refactor for readability. No behavior change."


def module_docs(source: str) -> str:
    """Top-level string blocks (QuixBugs keeps each program's spec there)."""
    tree = ast.parse(source)
    blocks = [
        ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ]
    return "\n\n".join(blocks)


def versions_for(root: Path, name: str) -> dict[str, ModuleVersions]:
    buggy = (root / "python_programs" / f"{name}.py").read_text()
    correct = (root / "correct_python_programs" / f"{name}.py").read_text().rstrip()
    base = correct + "\n\n" + module_docs(buggy) + "\n"
    reformatted = ast.unparse(ast.parse(base)) + "\n"
    return {
        "bug": ModuleVersions(root, f"{name}.py", "correct", "buggy", base, buggy),
        "control": ModuleVersions(root, f"{name}.py", "correct", "reformatted", base, reformatted),
    }


def run_one(verifier: ChangeVerifier, versions: ModuleVersions, name: str) -> dict[str, Any]:
    started = perf_counter()
    try:
        change = analyse(versions, name)
        outcome = verifier.verify(versions, change, INTENT)
    except SandboxUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - preserved as an unverified attempt
        return {"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    certificate = outcome.certificate
    return {
        "status": certificate.status.value,
        "cases_compared": certificate.cases_compared,
        "differences": [item.model_dump(mode="json") for item in certificate.differences],
        "reason": certificate.reason,
        "model_calls": [call.model_dump(mode="json") for call in outcome.model_calls],
        "seconds": round(perf_counter() - started, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", type=Path, required=True)
    parser.add_argument("--programs", help="comma-separated subset (default: all 40)")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dollars", required=True)
    parser.add_argument("--input-rate", required=True)
    parser.add_argument("--output-rate", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.quixbugs.resolve()
    names = sorted(
        path.stem
        for path in (root / "python_programs").glob("*.py")
        if not path.stem.endswith("_test") and path.stem != "node"
    )
    if args.programs:
        wanted = args.programs.split(",")
        names = [name for name in names if name in wanted]
    settings = Settings().model_copy(
        update={"openrouter_model": args.model, "openrouter_fallback_models": ""}
    )
    args.output.mkdir(parents=True, exist_ok=False)
    guard = SpendGuard(
        OpenRouterLLMClient.from_settings(settings),
        model=args.model,
        dollars=args.dollars,
        input_rate=args.input_rate,
        output_rate=args.output_rate,
        directory=args.output / "spend",
    )
    (args.output / "manifest.json").write_text(
        json.dumps(
            {
                "version": "quixbugs_verify_change@1",
                "prompt_version": PROMPT_VERSION,
                "intent": INTENT,
                "programs": names,
                "model": args.model,
                "dollar_cap": args.dollars,
                "quixbugs_files_sha256": {
                    str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for name in names
                    for path in (
                        root / "python_programs" / f"{name}.py",
                        root / "correct_python_programs" / f"{name}.py",
                    )
                },
                "source_sha256": {
                    str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for base in (
                        Path("backend/app/verified_change"),
                        Path("backend/app/verified_coding"),
                    )
                    for path in sorted(base.glob("*.py"))
                },
                "limitations": [
                    "QuixBugs is public and old; models may have seen these programs and fixes.",
                    "Bugs are classic single-line algorithm bugs, not AI-written changes.",
                    "The generator sees the diff, as the product does with a real change.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    for name in names:
        if guard.blocked:
            break
        record: dict[str, Any] = {"program": name}
        for arm, versions in versions_for(root, name).items():
            verifier = ChangeVerifier(
                guard,
                args.model,
                DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
                limits=ChangeLimits(max_retries=0),
            )
            try:
                record[arm] = run_one(verifier, versions, name)
            except SandboxUnavailable as exc:
                record[arm] = {"status": "sandbox_unavailable", "error": str(exc)}
                (args.output / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n")
                print(json.dumps({"halted": name}), flush=True)
                return
        record["charged_usd"] = str(guard.spent)
        (args.output / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "program": name,
                    "bug": record["bug"]["status"],
                    "control": record["control"]["status"],
                    "charged_usd": str(guard.spent),
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
