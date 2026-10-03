"""Paired evaluation: lean, lean+self-review, lean+differential verification, kernel.

The lean, self-review and verified arms share the exact same stage-one answer, so
their difference isolates what each second stage adds or breaks. The kernel arm is
an independent production-runtime attempt. Every arm is scored by withheld checks
the solvers never see. One serial spend guard covers the whole batch.

PYTHONPATH=backend:. .venv/bin/python -m evals.verified_coding.run \\
  --cases evals/verified_coding/heldout-cases.json --model google/gemini-3.7-flash \\
  --input-rate 0.00000075 --output-rate 0.00000375 --dollars 2.5 --repeats 2 \\
  --output runs/verified-coding/NEW
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any

from evals.chapter_13p.coding_execution.budgeted import SpendGuard
from evals.chapter_13p.coding_execution.evidence import (
    checks_digest,
    digest,
    execution_passed,
    extract_code,
    load_cases,
)
from evals.chapter_13p.coding_execution.matched import Limits, run_arm
from pydantic import ValidationError

from app.config import Settings
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.llm import LLMMessage, LLMRequest, LLMRequestOptions, LLMRole, OpenRouterLLMClient
from app.verified_coding.pipeline import (
    PipelineLimits,
    SandboxUnavailable,
    SolveOutcome,
    VerifiedCodingPipeline,
    infrastructure_failure,
    parse_proposal,
    summarize,
)
from app.verified_coding.prompts import PROMPT_VERSION

from .checks import CHECKS as CHECKS_V1
from .checks_v2 import CHECKS_V2
from .scoring import score_code

CHECKS = {**CHECKS_V1, **CHECKS_V2}

SELF_REVIEW_PROMPT = (
    "You previously wrote the solution below. Act as a skeptical reviewer. Re-read the "
    "PROBLEM clause by clause and check the code against every stated rule, edge case, "
    "tie-break, input format and efficiency requirement. Where the code violates any "
    "requirement, fix it; if it is fully correct, return it unchanged. Return a JSON object "
    "with code (complete implementation), tests (1..20 Python assertion strings, each max "
    "2000 chars, covering the clauses you checked) and explanation. Your code/tests will run.\n\n"
    "PROBLEM:\n{problem}\n\nYOUR PREVIOUS CODE:\n{code}\n"
)


def save(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, default=str) + "\n")


def score(case: str, code: str | None) -> dict[str, Any]:
    result = score_code(code, CHECKS[case])
    if code:
        result.update(code_sha256=digest(code), checks_sha256=checks_digest(CHECKS[case]))
    infrastructure = (
        result.get("exit_code") not in (None, 0)
        and not result.get("tests")
        and not result.get("timed_out")
        and "docker" in str(result.get("stderr_tail", "")).lower()
    )
    if infrastructure:
        raise SandboxUnavailable("scoring sandbox unavailable")
    return result


class Recorder:
    """Record every request/response of one arm next to the shared spend guard."""

    def __init__(self, client: SpendGuard, directory: Path) -> None:
        self.client, self.directory = client, directory
        self.provider, self.capabilities = client.provider, client.capabilities
        self.calls = 0

    def complete(self, request: LLMRequest):  # noqa: ANN201 - LLMClient protocol
        self.calls += 1
        stem = self.directory / f"model-{self.calls}"
        save(stem.with_suffix(".request.json"), request.model_dump(mode="json"))
        try:
            response = self.client.complete(request)
        except Exception as exc:
            save(stem.with_suffix(".failure.json"), {"failure": type(exc).__name__})
            raise
        save(stem.with_suffix(".response.json"), response.model_dump(mode="json"))
        return response


def self_review(
    client: Recorder, model: str, problem: str, solved: SolveOutcome, limits: PipelineLimits
) -> dict[str, Any]:
    """Simplest strong alternative: ask the same model to critique and fix its code."""
    started = perf_counter()
    sandbox = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5))
    if solved.proposal is None:
        return {"code": None, "calls": 0, "elapsed_ms": 0.0, "usage": []}
    fallback = solved.proposal.code if solved.passed else None
    messages = [
        LLMMessage(
            role=LLMRole.USER,
            content=SELF_REVIEW_PROMPT.format(problem=problem, code=solved.proposal.code),
        )
    ]
    usage: list[dict[str, Any]] = []
    delivered = fallback
    for _ in range(2):
        try:
            response = client.complete(
                LLMRequest(
                    model=model,
                    messages=messages,
                    options=LLMRequestOptions(
                        max_output_tokens=limits.per_request_output_tokens,
                        json_mode=True,
                        timeout_seconds=limits.request_timeout_seconds,
                        total_timeout_seconds=limits.request_timeout_seconds,
                        max_retries=0,
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001 - recorded as an arm failure
            usage.append({"failure": type(exc).__name__})
            break
        usage.append(response.usage.model_dump(mode="json"))
        messages.append(LLMMessage(role=LLMRole.ASSISTANT, content=response.text))
        try:
            proposal = parse_proposal(response.text)
            result = sandbox.execute(proposal.code, proposal.tests)
            if infrastructure_failure(result):
                raise SandboxUnavailable("self-review sandbox unavailable")
        except (ValidationError, ValueError) as exc:
            messages.append(
                LLMMessage(
                    role=LLMRole.USER,
                    content=f"Invalid response ({type(exc).__name__}). Return only the requested JSON object.",
                )
            )
            continue
        if execution_passed(result, len(proposal.tests)):
            delivered = proposal.code
            break
        messages.append(
            LLMMessage(
                role=LLMRole.USER,
                content="Observed sandbox result; repair and rerun: " + result.model_dump_json(),
            )
        )
    return {
        "code": delivered,
        "calls": len(usage),
        "elapsed_ms": round((perf_counter() - started) * 1000, 1),
        "usage": usage,
        "kept_original": delivered == fallback,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dollars", required=True)
    parser.add_argument("--input-rate", required=True)
    parser.add_argument("--output-rate", required=True)
    parser.add_argument("--repeats", type=int, choices=range(1, 4), default=1)
    parser.add_argument("--kernel", action="store_true", help="also run the kernel arm")
    parser.add_argument(
        "--kernel-repeats",
        type=int,
        default=None,
        help="run the kernel arm only in the first N repeats (default: all)",
    )
    args = parser.parse_args()
    cases = load_cases(args.cases)
    if set(cases) - set(CHECKS):
        parser.error("every case needs withheld checks")
    settings = Settings().model_copy(
        update={
            "openrouter_model": args.model,
            "openrouter_fallback_models": "",
            "code_execution_enabled": True,
            "verified_coding_enabled": False,
            "search_provider": "",
            "artifact_allowed_roots": "",
            "cognitive_max_model_calls": Limits().model_calls,
            "cognitive_max_external_calls": 0,
            "cognitive_max_input_tokens": 10000000,
            "cognitive_max_output_tokens": Limits().output_tokens,
            "cognitive_max_duration_ms": Limits().seconds * 1000,
            "cognitive_max_normalized_cost": 1000,
        }
    )
    if not settings.openrouter_api_key.get_secret_value().strip():
        parser.error("configured OpenRouter credential required")
    args.output.mkdir(parents=True, exist_ok=False)
    guard = SpendGuard(
        OpenRouterLLMClient.from_settings(settings),
        model=args.model,
        dollars=args.dollars,
        input_rate=args.input_rate,
        output_rate=args.output_rate,
        directory=args.output / "spend",
    )
    limits = PipelineLimits(max_retries=0)
    save(
        args.output / "manifest.json",
        {
            "version": "verified_coding_paired@1",
            "prompt_version": PROMPT_VERSION,
            "cases_file": str(args.cases),
            "cases_sha256": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
            "source_sha256": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for base in (Path("backend/app"), Path("evals/verified_coding"))
                for path in sorted(base.rglob("*.py"))
            },
            "cases": cases,
            "checks": {case: checks_digest(CHECKS[case]) for case in cases},
            "repeats": args.repeats,
            "model": args.model,
            "pipeline_limits": asdict(limits),
            "kernel_limits": asdict(Limits()) if args.kernel else None,
            "kernel_repeats": args.kernel_repeats if args.kernel else 0,
            "dollar_cap": args.dollars,
            "pricing_per_token": {"input": args.input_rate, "output": args.output_rate},
            "design": [
                "lean, self_review and verified share one stage-one answer per attempt",
                "self_review and verified each start from that answer; neither sees the other",
                "kernel is an independent production-runtime attempt",
                "withheld checks are never shown to any arm",
            ],
        },
    )
    records: list[dict[str, Any]] = []
    halted: str | None = None
    for repeat in range(args.repeats):
        for case, problem in cases.items():
            if guard.blocked or halted:
                break
            try:
                records.append(attempt(args, settings, guard, limits, case, problem, repeat))
            except SandboxUnavailable as exc:
                halted = f"sandbox unavailable during {case}-{repeat}: {exc}"
                print(json.dumps({"halted": halted}), flush=True)
    save(
        args.output / "summary.json",
        {
            "records": records,
            "expected_attempts": len(cases) * args.repeats,
            "complete": len(records) == len(cases) * args.repeats,
            "batch_blocked": guard.blocked,
            "halted": halted,
            "reported_or_reserved_usd": str(guard.spent),
        },
    )


def attempt(
    args: argparse.Namespace,
    settings: Settings,
    guard: SpendGuard,
    limits: PipelineLimits,
    case: str,
    problem: str,
    repeat: int,
) -> dict[str, Any]:
    """One paired attempt; raises SandboxUnavailable to halt the batch."""
    base = args.output / f"{case}-{repeat}"
    base.mkdir()
    record: dict[str, Any] = {"case": case, "repeat": repeat}
    # Stage one, shared.
    (base / "lean").mkdir()
    lean_client = Recorder(guard, base / "lean")
    stage = VerifiedCodingPipeline(
        lean_client,
        args.model,
        DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
        limits=limits,
    )
    started = perf_counter()
    solved = stage.solve(problem)
    lean_code = solved.proposal.code if solved.proposal and solved.passed else None
    record["lean"] = {
        "calls": len(stage.model_calls),
        "usage": [call.model_dump(mode="json") for call in stage.model_calls],
        "elapsed_ms": round((perf_counter() - started) * 1000, 1),
        "own_tests_passed": solved.passed,
        "failure": solved.failure,
        "score": score(case, lean_code),
    }
    # Self-review, from the same answer.
    (base / "self_review").mkdir()
    review = self_review(Recorder(guard, base / "self_review"), args.model, problem, solved, limits)
    record["self_review"] = {
        **{k: v for k, v in review.items() if k != "code"},
        "score": score(case, review["code"]),
    }
    # Differential verification, from the same answer.
    (base / "verified").mkdir()
    verifier = VerifiedCodingPipeline(
        Recorder(guard, base / "verified"),
        args.model,
        DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
        limits=limits,
    )
    outcome = verifier.verify(problem, solved)
    save(
        base / "verified" / "outcome.json",
        {
            "certificate": outcome.certificate.model_dump(mode="json"),
            "oracle": outcome.oracle.model_dump(mode="json") if outcome.oracle else None,
            "code": outcome.code,
            "events": outcome.events,
        },
    )
    record["verified"] = {
        **summarize(outcome).model_dump(mode="json"),
        "usage": [call.model_dump(mode="json") for call in outcome.model_calls],
        "elapsed_ms": round(outcome.elapsed_ms, 1),
        "score": score(case, outcome.code),
    }
    kernel_repeats = args.repeats if args.kernel_repeats is None else args.kernel_repeats
    if args.kernel and repeat < kernel_repeats and not guard.blocked:
        kernel = run_arm(settings, case, problem, "polya", base / "kernel", Limits(), client=guard)
        record["kernel"] = {
            "runtime_status": kernel.get("runtime_status"),
            "failure": kernel.get("failure"),
            "usage": kernel["usage"],
            "score": score(case, extract_code(kernel.get("delivered_answer") or "")),
        }
    record["batch_charged_usd"] = str(guard.spent)
    save(base / "record.json", record)
    print(
        json.dumps(
            {
                "case": case,
                "repeat": repeat,
                "lean": record["lean"]["score"]["passed"],
                "self_review": record["self_review"]["score"]["passed"],
                "verified": record["verified"]["score"]["passed"],
                "verified_status": record["verified"]["status"],
                "kernel": record.get("kernel", {}).get("score", {}).get("passed"),
                "charged_usd": str(guard.spent),
                "blocked": guard.blocked,
            }
        ),
        flush=True,
    )
    return record


if __name__ == "__main__":
    main()
