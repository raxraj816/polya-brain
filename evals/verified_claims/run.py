"""Frozen verified-claims evaluation: lean (stated numbers) vs verified (final numbers).

PYTHONPATH=backend:. .venv/bin/python -m evals.verified_claims.run --model google/gemini-3.7-flash \\
  --input-rate 0.00000075 --output-rate 0.00000375 --dollars 0.18 --output runs/verified-claims/NEW
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from evals.chapter_13p.coding_execution.budgeted import SpendGuard

from app.config import Settings
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.llm import OpenRouterLLMClient
from app.verified_claims.pipeline import PROMPT_VERSION, ClaimLimits, ClaimStatus, ClaimVerifier
from app.verified_claims.runner import same, stated_tolerance
from app.verified_claims.tables import load_tables
from app.verified_coding.pipeline import SandboxUnavailable

ROOT = Path(__file__).parent
TRUSTED = {ClaimStatus.PROVEN.value, ClaimStatus.CORRECTED.value, ClaimStatus.REVIEWED.value}


def matches(expected: Any, value: Any) -> bool:
    return same(expected, value, absolute=max(stated_tolerance(expected), 0.005))


def score(task: dict[str, Any], certificate: dict[str, Any]) -> dict[str, Any]:
    claims = certificate.get("claims", [])
    required = task["truth_required"]
    lean = {
        k: any(matches(task["truth"][k], c.get("stated_value")) for c in claims) for k in required
    }
    verified = {
        k: any(
            matches(task["truth"][k], c.get("final_value")) and c.get("status") in TRUSTED
            for c in claims
        )
        for k in required
    }
    certified = certificate.get("status") in {"verified", "corrected_and_verified"}
    return {
        "lean_correct": all(lean.values()),
        "verified_correct": all(verified.values()),
        "certified": certified,
        "false_certification": certified and not all(verified.values()),
        "lean_facts": lean,
        "verified_facts": verified,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dollars", required=True)
    parser.add_argument("--input-rate", required=True)
    parser.add_argument("--output-rate", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, default=ROOT / "tasks.json")
    parser.add_argument("--only", help="comma-separated task ids")
    args = parser.parse_args()
    tasks = json.loads(args.tasks.read_text())
    if args.only:
        tasks = [t for t in tasks if t["id"] in args.only.split(",")]
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
                "version": "verified_claims_eval@1",
                "prompt_version": PROMPT_VERSION,
                "tasks_file": str(args.tasks),
                "tasks_sha256": hashlib.sha256(args.tasks.read_bytes()).hexdigest(),
                "model": args.model,
                "dollar_cap": args.dollars,
                "source_sha256": {
                    str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(Path("backend/app/verified_claims").glob("*.py"))
                },
            },
            indent=2,
        )
        + "\n"
    )
    for task in tasks:
        if guard.blocked:
            print(json.dumps({"task": task["id"], "skipped": "spend guard blocked"}), flush=True)
            continue
        verifier = ClaimVerifier(
            guard,
            args.model,
            DockerPythonSandbox(
                limits=DockerSandboxLimits(timeout_seconds=40, memory_megabytes=128)
            ),
            limits=ClaimLimits(max_retries=0, per_request_output_tokens=5_000),
        )
        tables = load_tables([args.tasks.parent / item for item in task["tables"]])
        try:
            outcome = verifier.verify(task["question"], tables)
        except SandboxUnavailable as exc:
            print(json.dumps({"task": task["id"], "halted": str(exc)}), flush=True)
            break
        certificate = outcome.certificate.model_dump(mode="json")
        record = {
            "task": task["id"],
            "truth": task["truth"],
            "score": score(task, certificate),
            "certificate": certificate,
            "answer_code": outcome.answer_code,
            "verifier_code": outcome.oracle_code,
            "model_calls": [c.model_dump(mode="json") for c in outcome.model_calls],
            "seconds": round(outcome.elapsed_ms / 1000, 1),
        }
        (args.output / f"{task['id']}.json").write_text(
            json.dumps(record, indent=2, default=str) + "\n"
        )
        print(
            json.dumps(
                {
                    "task": task["id"],
                    "status": certificate["status"],
                    **{
                        k: record["score"][k]
                        for k in ("lean_correct", "verified_correct", "false_certification")
                    },
                    "charged_usd": str(guard.spent),
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
