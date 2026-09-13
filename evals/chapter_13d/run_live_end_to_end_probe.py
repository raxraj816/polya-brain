"""Raw-input-to-verified-report live probe for Chapter 13-D."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.cognition import accumulated_usage
from app.cognition.bootstrap import build_representation_session_runner
from app.config import Settings

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "zephyra_manual.txt"
LIVE_EVAL_OPT_IN = "POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL"


def main() -> int:
    if os.environ.get(LIVE_EVAL_OPT_IN) != "1":
        raise RuntimeError(
            f"Set {LIVE_EVAL_OPT_IN}=1 only for this non-confidential fictional fixture."
        )
    settings = Settings(ARTIFACT_ALLOWED_ROOTS=str(FIXTURE.parent))
    if not settings.openrouter_model:
        raise RuntimeError("OPENROUTER_MODEL is not configured")
    runner = build_representation_session_runner(settings)
    raw_input = (
        f"Using only the supplied fictional manual at '{FIXTURE}', determine what "
        "request timeout Zephyra revision 7 requires. State the rule and exact value."
    )
    started_at = datetime.now(UTC)
    started = perf_counter()
    execution = runner(raw_input, session_id="live-raw-zephyra")
    latency_ms = (perf_counter() - started) * 1000
    usage = accumulated_usage(execution.state)
    final_answer = execution.state["final_answer"] or ""
    verification = execution.state["verification"]
    actions = [
        selected["action_type"]
        for event in execution.state["events"]
        if event.event_type == "cognitive_action_decision"
        and isinstance((selected := event.metadata.get("selected")), dict)
        and isinstance(selected.get("action_type"), str)
    ]
    evidence_uris = [
        item.source_uri for item in execution.state["evidence"] if item.source_uri is not None
    ]
    passed = bool(
        not execution.awaiting_user_input
        and verification is not None
        and verification.passed
        and "37" in final_answer
        and "Z7.4" in final_answer
        and usage.model_calls <= 3
        and any("zephyra_manual.txt" in uri for uri in evidence_uris)
    )
    summary = {
        "probe": "chapter_13d_live_raw_input_to_verified_report",
        "status": "passed" if passed else "failed",
        "started_at": started_at.isoformat(),
        "model": settings.openrouter_model,
        "fictional_nonconfidential_fixture": True,
        "awaiting_user_input": execution.awaiting_user_input,
        "actions": actions,
        "final_answer": final_answer,
        "verification_passed": bool(verification is not None and verification.passed),
        "evidence_source_uris": evidence_uris,
        "model_calls": usage.model_calls,
        "external_calls": usage.external_calls,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.input_tokens + usage.output_tokens,
        "normalized_cost": round(usage.normalized_cost, 3),
        "latency_ms": round(latency_ms, 3),
        "task_model_snapshot_count": sum(
            event.event_type == "task_model_snapshot" for event in execution.state["events"]
        ),
        "limitations": [
            "One fictional-manual run verifies integration, not general product superiority.",
            "The local evidence evaluator uses deterministic provenance and relevance gates.",
            "Repeated fair live baselines remain required before a scientific win claim.",
        ],
    }
    model_hash = hashlib.sha256(settings.openrouter_model.encode()).hexdigest()[:8]
    run_id = f"{started_at.strftime('%H%M%S')}-{model_hash}"
    output = ROOT / "live_runs" / started_at.date().isoformat() / run_id / "end_to_end.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
