"""Replay frozen incompatible cases with previously serialized repair lessons."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.repair_memory import RepairLesson, learn_repair
from app.cognition.repair_recovery import EVENT
from app.cognition.task_model import accumulated_usage
from app.config import Settings
from app.investigator.artifacts import export_run
from app.investigator.source_patch import source_patch_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lessons-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name("cases.json")
    records = []
    summary = {
        "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "scope": "Known-case recovery development replay; not a held-out comparison.",
        "runs": records,
    }
    for family in json.loads(fixture.read_text())["families"]:
        lesson = RepairLesson.model_validate_json(
            (args.lessons_root / family["id"] / "learn/lesson.json").read_text()
        )
        assert lesson.valid()
        root = args.output / family["id"]
        root.mkdir()
        source, check = root / "source.py", root / "check.py"
        source.write_text(family["transfer_source"])
        check.write_text(family["negative_check"])
        settings = Settings().model_copy(
            update={
                "artifact_allowed_roots": str(root.resolve()),
                "code_execution_enabled": True,
                "verified_coding_enabled": False,
                "search_provider": "",
                "cognitive_max_model_calls": 6,
            }
        )
        state = source_patch_state(family["negative_problem"], source, check, settings)
        started = perf_counter()
        result = build_cognitive_runtime(
            settings, enable_source_patch=True, repair_lesson_loader=lambda lesson=lesson: [lesson]
        ).run_state(state)
        elapsed = perf_counter() - started
        (root / "artifacts").mkdir(mode=0o700)
        export_run(result, root / "artifacts", elapsed_ms=elapsed * 1000)
        learned = learn_repair(result.state)
        records.append(
            {
                "family": family["id"],
                "status": result.status.value,
                "elapsed_seconds": elapsed,
                "usage": accumulated_usage(result.state).model_dump(mode="json"),
                "recovery_proposed": any(e.event_type == EVENT for e in result.state["events"]),
                "historical_failed_verdict_retained": any(
                    e.event_type == "verification_invalidated" for e in result.state["events"]
                ),
                "patch_verdicts": [
                    o.output.get("patch_verified")
                    for o in result.state["execution_outputs"]
                    if isinstance(o.output, dict)
                ],
                "new_lesson": {"old_text": learned.old_text, "new_text": learned.new_text}
                if learned
                else None,
                "host_source_unchanged": source.read_text() == family["transfer_source"],
                "usage_may_be_incomplete": any(
                    o.status.value != "succeeded"
                    and o.payload
                    and isinstance(o.payload, dict)
                    and o.payload.get("model_calls", 0)
                    for o in result.observations
                ),
            }
        )
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(family["id"], result.status.value, records[-1]["patch_verdicts"], flush=True)


if __name__ == "__main__":
    main()
