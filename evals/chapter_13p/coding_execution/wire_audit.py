"""Replay saved gateway responses to measure request bytes without provider calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.cognition.model_contracts import ConclusionCheckOutput, DeliberationCapabilityOutput
from app.cognition.model_gateway import CognitiveModelGateway
from app.graph.state import ExecutionOutput, create_initial_state
from app.llm import FakeLLMClient, LLMResponse
from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    KnowledgeGap,
    PlanTask,
    StructuredProblem,
    VerificationReport,
)

OUTPUTS = {"deliberator": DeliberationCapabilityOutput, "conclusion_checker": ConclusionCheckOutput}
RECORDS = {
    "gaps": KnowledgeGap,
    "evidence": EvidenceItem,
    "hypotheses": Hypothesis,
    "plan": PlanTask,
    "execution_outputs": ExecutionOutput,
}


def message_bytes(request):
    return sum(len(message["content"].encode()) for message in request["messages"])


def audit(directory: Path):
    results = []
    for path in sorted(directory.glob("model-*.request.json")):
        original = json.loads(path.read_text())
        prompt = original["messages"][0]["content"]
        incoming = json.loads(original["messages"][1]["content"])
        if "original_input" in incoming or "CAPABILITY_RULES:" not in prompt:
            continue
        capability = prompt.split("Capability: ", 1)[1].splitlines()[0]
        if capability not in OUTPUTS:
            continue
        current = incoming["current_state"]
        state = create_initial_state(current["raw_input"])
        for key, cls in RECORDS.items():
            state[key] = [cls.model_validate(item) for item in current[key]]
        for key, cls in (
            ("structured_problem", StructuredProblem),
            ("verification", VerificationReport),
        ):
            state[key] = cls.model_validate(current[key]) if current[key] is not None else None
        index = int(path.name.split("-")[1].split(".")[0])
        responses, old_requests = [], []
        for i in range(index, index + 2):
            request_path = directory / f"model-{i}.request.json"
            if not request_path.exists():
                break
            request = json.loads(request_path.read_text())
            if i > index and "original_input" not in json.loads(request["messages"][1]["content"]):
                break
            old_requests.append(request)
            responses.append(
                LLMResponse.model_validate(
                    json.loads((directory / f"model-{i}.response.json").read_text())
                )
            )
        fake = FakeLLMClient(responses)
        CognitiveModelGateway(fake, original["model"]).complete(
            capability=capability,
            instructions=prompt.split("CAPABILITY_RULES:\n", 1)[1].split("\n\nReturn exactly", 1)[
                0
            ],
            output_type=OUTPUTS[capability],
            state=state,
            context=incoming["capability_context"],
            max_output_tokens=original["options"]["max_output_tokens"],
        )
        if len(fake.requests) != len(old_requests):
            raise ValueError("Replay request count differs; cannot make a paired byte comparison")
        results.append(
            {
                "run": str(directory),
                "capability": capability,
                "requests": len(old_requests),
                "old_message_bytes": sum(message_bytes(r) for r in old_requests),
                "compact_message_bytes": sum(
                    message_bytes(r.model_dump(mode="json")) for r in fake.requests
                ),
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = [r for directory in args.directories for r in audit(directory)]
    if not results:
        parser.error("No compatible saved requests found")
    old = sum(r["old_message_bytes"] for r in results)
    new = sum(r["compact_message_bytes"] for r in results)
    report = {
        "version": "model_wire_audit@0.1.0",
        "provider_calls": 0,
        "old_message_bytes": old,
        "compact_message_bytes": new,
        "byte_reduction_percent": round(100 * (old - new) / old, 2),
        "limitations": "Saved responses replayed unchanged. Bytes are not tokens or total live cost. Framing excluded. No outcome or live call-saving claim.",
        "records": results,
    }
    with args.output.open("x") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "records"}))


if __name__ == "__main__":
    main()
