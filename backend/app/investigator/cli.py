"""Run actual, bounded PolyaBrain investigations from a local terminal."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from os import pathsep
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from pydantic import SecretStr, ValidationError

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.contracts import CognitiveRunStatus
from app.cognition.runtime import DEFAULT_MAX_CYCLES
from app.config import Settings
from app.graph.state import create_initial_state
from app.investigator.artifacts import export_run, write_json
from app.investigator.recovery import RecoveryError, RecoveryStore, runtime_fingerprint
from app.investigator.source_patch import source_patch_state


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polyabrain",
        description="Investigate problems through the production Cognitive Runtime.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    investigate = commands.add_parser(
        "investigate",
        help="Run a real bounded investigation and export its evidence, checks, and report.",
    )
    investigate.add_argument(
        "problem", nargs="+", help="The problem and explicit quoted artifact paths."
    )
    investigate.add_argument(
        "--source", type=Path, help="Explicit Python source for experimental patch investigation."
    )
    investigate.add_argument(
        "--check", type=Path, help="Python artifact defining verify(implementation)."
    )
    investigate.add_argument(
        "--experimental-source-patch",
        action="store_true",
        help="Opt into supplied-check patch investigation; no host edits or hostile-code attestation.",
    )
    resume = commands.add_parser(
        "resume", help="Continue a local checkpoint without replaying completed work."
    )
    resume.add_argument("run_directory", type=Path)
    resume.add_argument("--answer", help="Full revised problem answering a missing-input pause.")
    for command in (investigate, resume):
        _run_options(command)
    commands.add_parser(
        "proof", help="Run the legacy curated-template demonstration (repository checkout only)."
    )
    return parser


def _run_options(investigate: argparse.ArgumentParser) -> None:
    investigate.add_argument(
        "--offline",
        action="store_true",
        help="Disable model and search calls; use only deterministic capabilities.",
    )
    investigate.add_argument(
        "--artifact-root",
        type=Path,
        action="append",
        help="Allow explicit local files under this directory; repeat for multiple roots.",
    )
    investigate.add_argument(
        "--allow-code-execution",
        action="store_true",
        help="Enable the configured ephemeral networkless Docker sandbox.",
    )
    investigate.add_argument(
        "--max-model-calls",
        type=int,
        help="Hard model-attempt ceiling, including retries and repairs (0–100).",
    )
    investigate.add_argument(
        "--max-seconds", type=float, help="Hard run deadline in seconds (0–3600)."
    )
    investigate.add_argument(
        "--max-cycles",
        type=int,
        default=DEFAULT_MAX_CYCLES,
        help=f"Maximum controller cycles (1–100, default {DEFAULT_MAX_CYCLES}).",
    )
    investigate.add_argument("--output-root", type=Path, default=Path("runs/investigator"))
    investigate.add_argument(
        "--run-id", help="A new output folder name; existing runs are never replaced."
    )
    investigate.add_argument(
        "--json", action="store_true", help="Print a machine-readable summary."
    )


def main(argv: list[str] | None = None) -> int:
    """Return 0 for verified completion, 2 for input, 3 for no verified outcome."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "proof":
        parser.error("Run ./polyabrain proof from the repository for the legacy demonstration.")
    problem = (
        " ".join(args.problem).strip()
        if args.command == "investigate"
        else (args.answer or "").strip()
    )
    if (args.command == "investigate" or args.answer is not None) and (
        not problem or len(problem) > 100_000
    ):
        parser.error("The problem must contain 1–100000 characters.")
    if not 1 <= args.max_cycles <= 100:
        parser.error("--max-cycles must be between 1 and 100.")
    if (
        args.command == "investigate"
        and any((args.source, args.check, args.experimental_source_patch))
        and not all(
            (args.source, args.check, args.experimental_source_patch, args.allow_code_execution)
        )
    ):
        parser.error(
            "Source-patch investigation requires --source, --check, --experimental-source-patch, and --allow-code-execution."
        )
    if args.run_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.run_id):
        parser.error(
            "--run-id must be a new plain folder name (letters, digits, underscores, hyphens; at most 80 characters)."
        )

    store: RecoveryStore | None = None
    try:
        settings = Settings()
        if args.artifact_root is not None:
            roots = [path.resolve(strict=True) for path in args.artifact_root]
            if any(not path.is_dir() for path in roots):
                raise ValueError("Artifact roots must be existing directories.")
            settings.artifact_allowed_roots = pathsep.join(str(path) for path in roots)
        settings.code_execution_enabled = args.allow_code_execution
        if args.max_model_calls is not None:
            if not 0 <= args.max_model_calls <= 100:
                raise ValueError("--max-model-calls must be between 0 and 100.")
            settings.cognitive_max_model_calls = args.max_model_calls
        if args.max_seconds is not None:
            if not 0 <= args.max_seconds <= 3600:
                raise ValueError("--max-seconds must be between 0 and 3600.")
            settings.cognitive_max_duration_ms = args.max_seconds * 1000
        if args.offline:
            settings.openrouter_api_key = SecretStr("")
            settings.openrouter_model = ""
            settings.openrouter_fallback_models = ""
            settings.search_api_key = SecretStr("")
            settings.search_provider = ""
            settings.cognitive_max_model_calls = 0
            settings.cognitive_max_external_calls = 0
        store = RecoveryStore()
        parent_token = None
        if args.command == "resume":
            descriptor_path = args.run_directory / "recovery.json"
            if descriptor_path.stat().st_size > 4096:
                raise RecoveryError("Invalid recovery descriptor.")
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            if not isinstance(descriptor, dict) or not isinstance(
                descriptor.get("recovery_id"), str
            ):
                raise RecoveryError("Invalid recovery descriptor.")
            parent_token = descriptor["recovery_id"]
            state = store.load(
                parent_token,
                runtime_fingerprint(settings, args.run_directory),
                problem if args.answer is not None else None,
            )
        elif args.experimental_source_patch:
            state = source_patch_state(problem, args.source, args.check, settings)
            state["max_iterations"] = args.max_cycles
        else:
            state = create_initial_state(
                problem, session_id=str(uuid4()), max_iterations=args.max_cycles
            )
        session_id = state["session_id"]
        runtime = build_cognitive_runtime(
            settings,
            enable_source_patch=bool(
                state["structured_problem"] is not None
                and state["structured_problem"].problem_type == "source_patch_investigation"
            ),
        )
        root = args.output_root.resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = root / (
            args.run_id or (str(uuid4()) if parent_token is not None else session_id)
        )
        directory.mkdir(mode=0o700)
        token = store.create(runtime_fingerprint(settings, directory))
        write_json(
            directory / "recovery.json",
            {
                "version": "local_recovery@0.1.0",
                "recovery_id": token,
                "parent_recovery_id": parent_token,
            },
        )
        # Transfer recovery rights and save state in one durable transaction.
        store.initialize(token, state, parent_token)
    except RecoveryError as exc:
        if store is not None:
            store.close()
        print(f"polyabrain: {exc}", file=sys.stderr)
        return 1
    except ValidationError:
        if store is not None:
            store.close()
        print(
            "polyabrain: Invalid environment configuration. Check .env against .env.example.",
            file=sys.stderr,
        )
        return 1
    except FileExistsError:
        if store is not None:
            store.close()
        print(
            "polyabrain: That run directory already exists. Choose a new --run-id.", file=sys.stderr
        )
        return 1
    except OSError, ValueError, sqlite3.Error:
        if store is not None:
            store.close()
        print(
            "polyabrain: Invalid options, unavailable artifact roots, or unwritable output directory. Check --help and your configuration.",
            file=sys.stderr,
        )
        return 1

    started = perf_counter()
    try:
        result = runtime.run_state(
            state,
            max_cycles=args.max_cycles,
            checkpoint=lambda current, in_flight: store.save(token, current, in_flight),
        )
        store.finish(token, result)
        report = export_run(result, directory, elapsed_ms=(perf_counter() - started) * 1000)
    except (Exception, KeyboardInterrupt) as exc:
        # Preserve failure evidence without serializing exception arguments or credentials.
        write_json(
            directory / "error.json",
            {
                "status": "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                "error_type": type(exc).__name__,
                "session_id": session_id,
                "message": "No verified outcome was exported. Review the local configuration and retry with a new run directory.",
            },
        )
        print(
            f"polyabrain: Run stopped safely. Failure artifact: {directory / 'error.json'}",
            file=sys.stderr,
        )
        return 130 if isinstance(exc, KeyboardInterrupt) else 1
    finally:
        store.close()

    if args.json:
        print(
            json.dumps(
                {
                    "session_id": session_id,
                    "status": result.status.value,
                    "verification_status": report.verification_status,
                    "report": str(directory / "report.md"),
                    "open_questions": report.open_questions,
                }
            )
        )
    else:
        print(f"{report.verification_status}: {report.final_conclusion}")
        for question in report.open_questions:
            print(f"Open question: {question}")
        print(f"Report: {directory / 'report.md'}")
    if (
        result.status in {CognitiveRunStatus.NEEDS_INPUT, CognitiveRunStatus.MAX_CYCLES}
        and not args.json
    ):
        print(f"Continue with: ./polyabrain resume {directory} (use the same runtime options)")
    if result.status is CognitiveRunStatus.NEEDS_INPUT:
        return 2
    return 0 if report.verification_status == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
