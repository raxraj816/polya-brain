"""`polyabrain verify-change`: certify what a code change did to one function."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from app.config import Settings
from app.execution import DockerPythonSandbox, DockerSandboxLimits, image_available
from app.investigator.artifacts import write_json
from app.llm import OpenRouterLLMClient
from app.memory.failure_patterns import default_store
from app.verified_change.pipeline import ChangeStatus, ChangeVerifier
from app.verified_change.report import HEADLINES, render
from app.verified_change.source import ChangeSourceError, analyse, read_versions
from app.verified_coding.pipeline import SandboxUnavailable

EXIT_CODES = {
    ChangeStatus.NO_DIFFERENCE: 0,
    ChangeStatus.INTENDED_ONLY: 0,
    ChangeStatus.REGRESSIONS: 3,
    ChangeStatus.UNCLEAR: 3,
    ChangeStatus.UNVERIFIED: 4,
}


def add_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "verify-change",
        help="Run old and new versions of a changed function side by side and certify the behavior change.",
    )
    parser.add_argument("--repo", type=Path, default=Path("."), help="Local git repository.")
    parser.add_argument(
        "--module", required=True, help="Repository-relative path of the .py module."
    )
    parser.add_argument(
        "--function", required=True, help="Function name, or Class.method for a no-argument class."
    )
    parser.add_argument("--base", default="HEAD", help="Base git revision (default HEAD).")
    parser.add_argument("--head", help="Changed git revision (default: the working tree).")
    intent = parser.add_mutually_exclusive_group()
    intent.add_argument("--intent", default="", help="What the change is supposed to do.")
    intent.add_argument("--intent-file", type=Path, help="Read the intent (e.g. a PR description).")
    parser.add_argument("--output-root", type=Path, default=Path("runs/verified-change"))
    parser.add_argument("--run-id", help="A new output folder name.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable summary.")


def run(args: argparse.Namespace) -> int:
    """Exit 0: no regression; 3: regression or review needed; 4: unverified; 1: setup error."""
    if args.run_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.run_id):
        print("polyabrain: --run-id must be a plain folder name.", file=sys.stderr)
        return 1
    try:
        intent = (
            args.intent_file.read_text(encoding="utf-8") if args.intent_file else args.intent
        ).strip()[:8_000]
        settings = Settings()
        versions = read_versions(args.repo, args.module, base_ref=args.base, head_ref=args.head)
        change = analyse(versions, args.function)
    except ChangeSourceError as exc:
        print(f"polyabrain: {exc}", file=sys.stderr)
        return 1
    except OSError, UnicodeDecodeError, ValidationError:
        print(
            "polyabrain: Could not read the intent file or the environment configuration.",
            file=sys.stderr,
        )
        return 1
    key = settings.openrouter_api_key.get_secret_value().strip()
    model = settings.openrouter_model.strip()
    if not key or not model:
        print(
            "polyabrain: Configure OPENROUTER_API_KEY and OPENROUTER_MODEL first.", file=sys.stderr
        )
        return 1
    if not image_available(settings.code_execution_image):
        print(
            "polyabrain: Start Docker and pull the configured sandbox image first.", file=sys.stderr
        )
        return 1
    directory = args.output_root.resolve() / (args.run_id or str(uuid4()))
    try:
        directory.mkdir(parents=True, mode=0o700)
    except FileExistsError:
        print(
            "polyabrain: That run directory already exists. Choose a new --run-id.", file=sys.stderr
        )
        return 1
    verifier = ChangeVerifier(
        OpenRouterLLMClient.from_settings(settings),
        model,
        DockerPythonSandbox(
            image=settings.code_execution_image,
            limits=DockerSandboxLimits(memory_megabytes=settings.code_execution_memory_mb),
        ),
        patterns=default_store(settings.failure_patterns_path, settings.failure_patterns_enabled),
        source=directory.name,
    )
    started = perf_counter()
    try:
        outcome = verifier.verify(versions, change, intent)
    except SandboxUnavailable as exc:
        write_json(
            directory / "error.json", {"status": "failed", "error_type": "SandboxUnavailable"}
        )
        print(f"polyabrain: The sandbox became unavailable: {exc}", file=sys.stderr)
        return 1
    outcome.elapsed_ms = (perf_counter() - started) * 1000
    certificate = outcome.certificate
    write_json(directory / "certificate.json", certificate.model_dump(mode="json"))
    write_json(directory / "trace.json", outcome.events)  # type: ignore[arg-type]
    (directory / "report.md").write_text(render(outcome), encoding="utf-8")
    if args.json:
        print(
            json.dumps(
                {
                    "status": certificate.status.value,
                    "cases_compared": certificate.cases_compared,
                    "differences": [
                        item.model_dump(mode="json") for item in certificate.differences
                    ],
                    "report": str(directory / "report.md"),
                }
            )
        )
    else:
        print(f"{HEADLINES[certificate.status]} ({certificate.cases_compared:,} inputs compared).")
        for item in certificate.differences:
            print(
                f"- {item.verdict}: input {item.args} | old {item.old_output} | new {item.new_output}"
            )
        print(f"Report: {directory / 'report.md'}")
    return EXIT_CODES[certificate.status]
