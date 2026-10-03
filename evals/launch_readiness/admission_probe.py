"""Saved-candidate ablation; never supplies a product answer or changes admission."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.chapter_13p.coding_execution.evidence import checks_digest, digest, execution_passed
from evals.chapter_13p.coding_execution.matched import save
from evals.chapter_13p.coding_execution.verify import CHECKS

from app.cognition.generated_checks import validate_generated_checks
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.models.contracts import PlanTask


def probe(root: Path, output: Path):
    manifest = json.loads((root / "manifest.json").read_text())
    records = []
    for case in ("median", "integer_coverage", "lexicographic_toposort"):
        assert manifest["checks"][case] == checks_digest(CHECKS[case])
        for repeat in range(manifest["repeats"]):
            directory = root / f"{case}-{repeat}-polya"
            original = directory / "model-2.response.json"
            payload = json.loads(json.loads(original.read_text())["text"])
            tasks = [PlanTask.model_validate(task) for task in payload["tasks"]]
            try:
                validate_generated_checks(tasks, {"raw_input": manifest["cases"][case]})
                rejection = None
            except ValueError as exc:
                rejection = str(exc)
            candidates = [task for task in tasks if task.tool_name == "python_sandbox"]
            assert len(candidates) == 1
            task = candidates[0]
            sandbox = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=20))
            generated = None
            generated_error = None
            try:
                generated = sandbox.execute(task.params["code"], task.params["tests"])
            except ValueError as exc:
                generated_error = str(exc)
            independent = sandbox.execute(task.params["code"], CHECKS[case])
            records.append(
                {
                    "case": case,
                    "repeat": repeat,
                    "source_response_sha256": digest(original.read_text()),
                    "candidate_code_sha256": digest(task.params["code"]),
                    "with_origin_screen_rejected": rejection is not None,
                    "diagnostic": rejection,
                    "without_origin_screen_generated_tests_pass": bool(
                        generated and execution_passed(generated, len(task.params["tests"]))
                    ),
                    "without_origin_screen_independent_checks_pass": execution_passed(
                        independent, len(CHECKS[case])
                    ),
                    "generated_execution": generated.model_dump(mode="json") if generated else None,
                    "generated_admission_error": generated_error,
                    "independent_execution": independent.model_dump(mode="json"),
                    "original_delivered_answer": json.loads(
                        (directory / "outcome.json").read_text()
                    )["delivered_answer"],
                }
            )
    save(
        output,
        {
            "records": records,
            "live_model_calls": 0,
            "limitations": [
                "Selected known failed development responses, not representative outcomes.",
                "Only candidate execution is ablated; no final answer or successful runtime is reconstructed.",
                "Passing checks do not prove semantic correctness of the oracle.",
                "Product origin checks remain enabled; original failures remain failures.",
            ],
        },
    )
    print(
        json.dumps(
            {
                "candidates": len(records),
                "rejected_by_origin": sum(r["with_origin_screen_rejected"] for r in records),
                "generated_checks_pass": sum(
                    r["without_origin_screen_generated_tests_pass"] for r in records
                ),
                "independent_checks_pass": sum(
                    r["without_origin_screen_independent_checks_pass"] for r in records
                ),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    probe(args.run, args.output)
