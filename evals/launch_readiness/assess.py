"""Offline audit and blinded packet for saved matched development experiments."""

from __future__ import annotations

import argparse
import json
import math
import secrets
from pathlib import Path

from evals.chapter_13p.coding_execution.evidence import (
    checks_digest,
    digest,
    execution_passed,
    extract_code,
)
from evals.chapter_13p.coding_execution.matched import save
from evals.chapter_13p.coding_execution.verify import CHECKS

from app.execution.sandbox import SandboxExecutionResult


def read(path):
    return json.loads(path.read_text())


def audit_attempt(root, manifest, case, repeat, arm):
    directory = root / f"{case}-{repeat}-{arm}"
    result = dict(
        case=case,
        repeat=repeat,
        arm=arm,
        valid=False,
        passed=False,
        errors=[],
        cost_usd=None,
        tokens=None,
        elapsed_ms=None,
        answer=None,
    )
    errors = result["errors"]
    try:
        entry, outcome, score = (
            read(directory / name) for name in ("input.json", "outcome.json", "score.json")
        )
        if entry != {
            "prompt": manifest["cases"][case],
            "model": manifest["model"],
            "limits": manifest["limits"],
        }:
            errors.append("Input or limits differ from frozen manifest")
        if any(score.get(k) != v for k, v in outcome.items()):
            errors.append("Score does not preserve outcome")
        if (score["case"], score["repeat"], score["arm"], score["prompt_sha256"]) != (
            case,
            repeat,
            arm,
            digest(manifest["cases"][case]),
        ):
            errors.append("Attempt identity mismatch")
        check_hash = checks_digest(CHECKS[case])
        if (
            manifest["checks"][case] != check_hash
            or score["independent"]["checks_sha256"] != check_hash
        ):
            errors.append("Independent checks differ from frozen manifest")
        answer = outcome["delivered_answer"]
        result["answer"] = answer
        code = extract_code(answer or "")
        passed = False
        if code is not None:
            independent = score["independent"]
            if independent.get("code_sha256") != digest(code):
                errors.append("Scored code differs from delivered code")
            execution = SandboxExecutionResult.model_validate(independent["execution"])
            passed = execution_passed(execution, len(CHECKS[case]))
        elif "execution" in score["independent"]:
            errors.append("Execution recorded without delivered code")
        if score["independent"]["passed"] is not passed:
            errors.append("Saved pass disagrees with recorded execution")
        usage = outcome["usage"]
        responses = []
        requests = sorted(directory.glob("model-*.request.json"))
        if (
            len(requests) != usage["model_calls"]
            or len(requests) > manifest["limits"]["model_calls"]
        ):
            errors.append("Model call count mismatch or limit exceeded")
        if {p.name for p in requests} != {
            f"model-{i}.request.json" for i in range(1, len(requests) + 1)
        }:
            errors.append("Model request sequence mismatch")
        if len(list(directory.glob("model-*.response.json"))) + len(
            list(directory.glob("model-*.failure.json"))
        ) != len(requests):
            errors.append("Response/failure inventory mismatch")
        for request_path in requests:
            request = read(request_path)
            options = request["options"]
            if (
                request["model"] != manifest["model"]
                or options["max_retries"] != 0
                or options["max_output_tokens"] > manifest["limits"]["per_request_output_tokens"]
            ):
                errors.append("Request route, retry or output ceiling mismatch")
            response_path = request_path.with_name(request_path.name.replace("request", "response"))
            if response_path.exists():
                response = read(response_path)
                responses.append(response)
                if response["model"] != manifest["model"]:
                    errors.append("Observed model mismatch")
        if usage["usage_complete"]:
            if len(responses) != len(requests):
                errors.append("Complete usage claimed with missing responses")
            for key in ("input_tokens", "output_tokens"):
                if usage[key] != sum(r["usage"][key] for r in responses):
                    errors.append(f"{key} total mismatch")
            result["tokens"] = usage["input_tokens"] + usage["output_tokens"]
        else:
            errors.append("Usage incomplete; cost comparison unavailable")
        costs = [r["usage"].get("estimated_cost_usd") for r in responses]
        if len(responses) == len(requests) and all(
            isinstance(c, (int, float)) and math.isfinite(c) and c >= 0 for c in costs
        ):
            result["cost_usd"] = sum(costs)
        else:
            errors.append("Provider cost incomplete")
        if len(list(directory.glob("sandbox-*.request.json"))) != usage["sandbox_calls"]:
            errors.append("Sandbox call count mismatch")
        result["elapsed_ms"] = usage["elapsed_ms"]
        result["runtime_acceptance"] = score.get("runtime_acceptance", {}).get("passed")
        result["valid"] = not errors
        result["passed"] = passed and not errors
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Missing or malformed artifact: {type(exc).__name__}")
    return result


def assess(root):
    manifest = read(root / "manifest.json")
    records = [
        audit_attempt(root, manifest, case, repeat, arm)
        for repeat in range(manifest["repeats"])
        for case in manifest["cases"]
        for arm in ("lean", "polya")
    ]
    totals = {}
    for arm in ("lean", "polya"):
        selected = [r for r in records if r["arm"] == arm]
        totals[arm] = {
            "attempts": len(selected),
            "audited": sum(r["valid"] for r in selected),
            "independent_passes": sum(r["passed"] for r in selected),
        }
        for key in ("cost_usd", "tokens", "elapsed_ms"):
            totals[arm][key] = (
                sum(r[key] for r in selected)
                if all(r["valid"] and r[key] is not None for r in selected)
                else None
            )
    ratios = {
        key: totals["polya"][key] / totals["lean"][key]
        if totals["polya"][key] is not None and totals["lean"][key]
        else None
        for key in ("cost_usd", "tokens", "elapsed_ms")
    }
    return {
        "records": records,
        "totals": totals,
        "polya_to_lean": ratios,
        "all_artifacts_valid": all(r["valid"] for r in records),
        "superiority_established": False,
        "limitations": [
            "Known development cases; repeats are not independent tasks.",
            "Recorded sandbox execution audited, not re-executed.",
            "Hash consistency is not signed provenance or semantic proof.",
            "Provider-reported costs are not invoices; elapsed time excludes independent scoring.",
            "Independent explanation review and real-user value remain unmeasured.",
        ],
    }


def review_markdown(packet):
    lines = [
        "# Independent response review",
        "",
        "Status: unreviewed. Rate both responses independently; use the opaque IDs in the JSON rating form.",
        "Record correctness, counterexamples, explanation quality, unsupported claims and required repairs.",
        "Choose either response, tie, or neither. Do not infer success from confident wording.",
        "",
    ]
    for pair in packet["pairs"]:
        lines.extend([f"## Pair {pair['pair_id']}", "", pair["problem"], ""])
        for response in pair["responses"]:
            lines.extend(
                [f"### Response {response['response_id']}", "", response["answer"], "", "---", ""]
            )
    return "\n".join(lines)


def build_packet(root, output):
    report = assess(root)
    manifest = read(root / "manifest.json")
    output.mkdir(parents=True, exist_ok=False)
    save(output / "audit.json", report)
    review, key = [], []
    rng = secrets.SystemRandom()
    for repeat in range(manifest["repeats"]):
        for case, prompt in manifest["cases"].items():
            pair_id = secrets.token_hex(8)
            pair = [r for r in report["records"] if r["case"] == case and r["repeat"] == repeat]
            rng.shuffle(pair)
            answers = []
            for record in pair:
                response_id = secrets.token_hex(8)
                answers.append(
                    {
                        "response_id": response_id,
                        "answer": record["answer"] or "[No answer delivered]",
                    }
                )
                key.append(
                    {
                        "pair_id": pair_id,
                        "response_id": response_id,
                        "case": case,
                        "repeat": repeat,
                        "arm": record["arm"],
                    }
                )
            review.append(
                {
                    "pair_id": pair_id,
                    "problem": prompt,
                    "responses": answers,
                    "ratings": {
                        "preferred_response_id_or_tie": None,
                        "correctness_and_counterexample": None,
                        "explanation_and_complexity": None,
                        "unsupported_claims": None,
                        "usefulness_and_required_repairs": None,
                    },
                }
            )
    rng.shuffle(review)
    packet = {"review_status": "unreviewed", "pairs": review}
    save(output / "review-packet.json", packet)
    with (output / "review-packet.md").open("x") as stream:
        stream.write(review_markdown(packet))
    save(output / "private-condition-key.json", key)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_packet(args.run, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
