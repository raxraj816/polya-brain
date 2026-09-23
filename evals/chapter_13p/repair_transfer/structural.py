"""Compare frozen renamed-expression cases using the production composition."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.repair_memory import RepairLesson, learn_repair
from app.cognition.task_model import accumulated_usage
from app.config import Settings
from app.investigator.artifacts import export_run
from app.investigator.source_patch import source_patch_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lessons-root", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name("structural-cases.json")
    summary = {"fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(), "runs": []}
    for family in json.loads(fixture.read_text())["families"]:
        lesson = None
        conditions = ["learn", "cold", "warm"]
        if args.lessons_root:
            lesson = RepairLesson.model_validate_json(
                (args.lessons_root / family["id"] / "learn/lesson.json").read_text()
            )
            conditions = ["warm", "negative"]
        for condition in conditions:
            if condition in {"warm", "negative"} and lesson is None:
                summary["runs"].append(
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
            initial, negative = condition == "learn", condition == "negative"
            source, check = root / "source.py", root / "check.py"
            source_text = family["source" if initial else "transfer_source"]
            source.write_text(source_text)
            check.write_text(
                family["negative_check" if negative else "check" if initial else "transfer_check"]
            )
            config = Settings().model_copy(
                update={
                    "artifact_allowed_roots": str(root.resolve()),
                    "code_execution_enabled": True,
                    "search_provider": "",
                    "cognitive_max_model_calls": 6,
                }
            )
            state = source_patch_state(
                family[
                    "negative_problem" if negative else "problem" if initial else "transfer_problem"
                ],
                source,
                check,
                config,
            )
            lessons = [lesson] if lesson and condition in {"warm", "negative"} else []
            started = perf_counter()
            result = build_cognitive_runtime(
                config,
                enable_source_patch=True,
                repair_lesson_loader=lambda lessons=lessons: lessons,
            ).run_state(state)
            elapsed = perf_counter() - started
            (root / "artifacts").mkdir(mode=0o700)
            export_run(result, root / "artifacts", elapsed_ms=elapsed * 1000)
            if initial:
                lesson = learn_repair(result.state)
                if lesson:
                    (root / "lesson.json").write_text(lesson.model_dump_json())
            recalls = [
                e.metadata
                for e in result.state["events"]
                if e.event_type == "source_patch_memory_proposed"
            ]
            summary["runs"].append(
                {
                    "family": family["id"],
                    "condition": condition,
                    "status": result.status.value,
                    "usage": accumulated_usage(result.state).model_dump(mode="json"),
                    "elapsed_seconds": elapsed,
                    "lesson_available": bool(lesson),
                    "memory_proposed": bool(recalls),
                    "transfer_kind": recalls[0].get("transfer_kind", "exact") if recalls else None,
                    "patch_verdicts": [
                        o.output.get("patch_verified")
                        for o in result.state["execution_outputs"]
                        if isinstance(o.output, dict)
                    ],
                    "host_source_unchanged": source.read_text() == source_text,
                    "lesson_bytes": len(lesson.model_dump_json().encode()) if lesson else 0,
                    "usage_may_be_incomplete": any(
                        o.status.value != "succeeded"
                        and isinstance(o.payload, dict)
                        and o.payload.get("model_calls", 0)
                        for o in result.observations
                    ),
                }
            )
            (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(
                family["id"],
                condition,
                result.status.value,
                accumulated_usage(result.state).model_calls,
                flush=True,
            )


if __name__ == "__main__":
    main()
