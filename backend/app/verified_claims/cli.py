"""`polyabrain ask-data`: answer a question about local tables and prove every number."""

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
from app.verified_claims.pipeline import AnswerStatus, ClaimVerifier
from app.verified_claims.report import HEADLINES, LABELS, render
from app.verified_claims.tables import TableError, load_tables
from app.verified_coding.pipeline import SandboxUnavailable

EXIT_CODES = {
    AnswerStatus.VERIFIED: 0,
    AnswerStatus.CORRECTED: 0,
    AnswerStatus.NEEDS_REVIEW: 3,
    AnswerStatus.UNVERIFIED: 4,
}


def add_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "ask-data",
        help="Answer a question about local CSV/JSON tables and independently prove every number.",
    )
    parser.add_argument("question", nargs="+", help="The question about the tables.")
    parser.add_argument(
        "--table",
        type=Path,
        action="append",
        required=True,
        help="A .csv or .json table; repeat for more.",
    )
    parser.add_argument("--output-root", type=Path, default=Path("runs/verified-claims"))
    parser.add_argument("--run-id", help="A new output folder name.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable summary.")


def run(args: argparse.Namespace) -> int:
    """Exit 0: verified or corrected; 3: needs review; 4: unverified; 1: setup error."""
    question = " ".join(args.question).strip()
    if not question or len(question) > 4_000:
        print("polyabrain: The question must contain 1–4000 characters.", file=sys.stderr)
        return 1
    if args.run_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.run_id):
        print("polyabrain: --run-id must be a plain folder name.", file=sys.stderr)
        return 1
    try:
        tables = load_tables(args.table)
        settings = Settings()
    except TableError as exc:
        print(f"polyabrain: {exc}", file=sys.stderr)
        return 1
    except OSError, ValidationError:
        print(
            "polyabrain: Could not read the tables or the environment configuration.",
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
    verifier = ClaimVerifier(
        OpenRouterLLMClient.from_settings(settings),
        model,
        DockerPythonSandbox(
            image=settings.code_execution_image,
            limits=DockerSandboxLimits(
                memory_megabytes=max(128, settings.code_execution_memory_mb)
            ),
        ),
        patterns=default_store(settings.failure_patterns_path, settings.failure_patterns_enabled),
        source=directory.name,
    )
    started = perf_counter()
    try:
        outcome = verifier.verify(question, tables)
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
    (directory / "answer_code.py").write_text(outcome.answer_code, encoding="utf-8")
    (directory / "verifier_code.py").write_text(outcome.oracle_code, encoding="utf-8")
    (directory / "report.md").write_text(render(outcome), encoding="utf-8")
    if args.json:
        print(
            json.dumps(
                {
                    "status": certificate.status.value,
                    "claims": [c.model_dump(mode="json") for c in certificate.claims],
                    "report": str(directory / "report.md"),
                }
            )
        )
    else:
        print(f"{HEADLINES[certificate.status]}.")
        for claim in certificate.claims:
            print(f"- {LABELS[claim.status]}: {claim.statement} = {claim.final_value!r}")
        print(f"Report: {directory / 'report.md'}")
    return EXIT_CODES[certificate.status]
