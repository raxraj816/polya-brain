"""Run frozen candidate-repair transfer cases through the production composition.

PYTHONPATH=backend .venv/bin/python -m evals.chapter_13p.repair_transfer.run --output runs/repair-transfer/unique
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.repair_memory import EVENT, RepairLesson, learn_repair
from app.cognition.task_model import accumulated_usage
from app.config import Settings
from app.investigator.artifacts import export_run
from app.investigator.source_patch import source_patch_state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name("cases.json")
    cases = json.loads(fixture.read_text())
    records = []
    summary = {
        "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "limitations": cases["limitations"],
        "runs": records,
    }
    for family in cases["families"]:
        learned = None
        for condition in ["learn", "transfer_cold", "transfer_warm", "incompatible_warm"]:
            if condition.endswith("warm") and learned is None:
                records.append(
                    {
                        "family": family["id"],
                        "condition": condition,
                        "status": "skipped_no_learned_lesson",
                    }
                )
                (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
                continue
            root = args.output / family["id"] / condition
            root.mkdir(parents=True)
            first = condition == "learn"
            source_text = family["source" if first else "transfer_source"]
            check_text = family[
                "negative_check"
                if condition == "incompatible_warm"
                else "check"
                if first
                else "transfer_check"
            ]
            source, check = root / "source.py", root / "check.py"
            source.write_text(source_text)
            check.write_text(check_text)
            config = Settings().model_copy(
                update={
                    "artifact_allowed_roots": str(root.resolve()),
                    "code_execution_enabled": True,
                    "verified_coding_enabled": False,
                    "search_provider": "",
                    "cognitive_max_model_calls": 6,
                }
            )
            lessons = [learned] if condition.endswith("warm") and learned is not None else []
            state = source_patch_state(
                family["negative_problem" if condition == "incompatible_warm" else "problem"],
                source,
                check,
                config,
            )
            started = perf_counter()
            result = build_cognitive_runtime(
                config,
                enable_source_patch=True,
                repair_lesson_loader=lambda lessons=lessons: lessons,
            ).run_state(state)
            elapsed = (perf_counter() - started) * 1000
            (root / "artifacts").mkdir(mode=0o700)
            export_run(result, root / "artifacts", elapsed_ms=elapsed)
            if first:
                lesson = learn_repair(result.state)
                if lesson is not None:
                    serialized = lesson.model_dump_json()
                    (root / "lesson.json").write_text(serialized)
                    learned = RepairLesson.model_validate_json(serialized)
            usage = accumulated_usage(result.state).model_dump(mode="json")
            execution = [
                o.output
                for o in result.state["execution_outputs"]
                if isinstance(o.output, dict) and "patch_verified" in o.output
            ]
            records.append(
                {
                    "family": family["id"],
                    "condition": condition,
                    "status": result.status.value,
                    "usage": usage,
                    "elapsed_ms": elapsed,
                    "memory_proposed": any(e.event_type == EVENT for e in result.state["events"]),
                    "patch_verified": any(o["patch_verified"] for o in execution),
                    "original_failed": any(o["baseline_failed"] for o in execution),
                    "lesson_bytes": len(learned.model_dump_json().encode()) if learned else 0,
                    "host_source_unchanged": source.read_text() == source_text,
                    "usage_may_be_incomplete": any(
                        o.status.value != "succeeded" and o.payload.get("model_calls", 0)
                        for o in result.observations
                    ),
                }
            )
            (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(
                family["id"],
                condition,
                result.status.value,
                usage["model_calls"],
                "model calls",
                flush=True,
            )


if __name__ == "__main__":
    main()
