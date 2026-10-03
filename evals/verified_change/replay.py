"""Replay bound saved QuixBugs generator responses offline; never call a provider."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from evals.verified_change.quixbugs import INTENT, versions_for

from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.verified_change.pipeline import ChangeLimits, ChangeVerifier
from app.verified_change.report import render
from app.verified_change.source import analyse


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind_shard(shard, dataset):
    """Validate ordered records against saved responses before any execution."""
    manifest = json.loads((shard / "manifest.json").read_text())
    for relative, expected in manifest["quixbugs_files_sha256"].items():
        path = (dataset / relative).resolve()
        if not path.is_relative_to(dataset.resolve()) or digest(path) != expected:
            raise ValueError(f"Dataset hash mismatch: {relative}")
    cursor, bound = 0, []
    for name in manifest["programs"]:
        record_path = shard / f"{name}.json"
        record = json.loads(record_path.read_text()) if record_path.exists() else {}
        for arm in ("bug", "control"):
            attempt = record.get(arm, {})
            responses, files = [], []
            missing = not attempt or not attempt.get("model_calls")
            for call in attempt.get("model_calls", []):
                cursor += 1
                path = shard / "spend" / f"{cursor}.response.json"
                if call["outcome"] != "ok":
                    missing = True
                    if path.exists():
                        raise ValueError(
                            "Failed call unexpectedly has a response; reconcile binding"
                        )
                    continue
                response = LLMResponse.model_validate_json(path.read_text())
                usage = response.usage
                if (
                    response.model != call["model"]
                    or usage.input_tokens != call["input_tokens"]
                    or usage.output_tokens != call["output_tokens"]
                    or usage.estimated_cost_usd != call["cost_usd"]
                ):
                    raise ValueError(f"Saved response does not match recorded call: {path}")
                # Saved telemetry remains in its original artifact; replay costs zero.
                responses.append(
                    response.model_copy(
                        update={
                            "provider": "offline-replay",
                            "duration_ms": 0,
                            "usage": LLMTokenUsage(
                                input_tokens=0, output_tokens=0, estimated_cost_usd=0
                            ),
                        }
                    )
                )
                files.append({"path": str(path), "sha256": digest(path)})
            bound.append(
                (name, arm, attempt.get("status", "missing"), [] if missing else responses, files)
            )
    expected_files = {f"{index}.response.json" for index in range(1, cursor + 1)}
    if any(p.name not in expected_files for p in (shard / "spend").glob("*.response.json")):
        raise ValueError("Unbound response exists after recorded attempts")
    return bound


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    shards = sorted(p for p in args.historical.glob("shard-*") if p.is_dir())
    bound = [(shard.name, row) for shard in shards for row in bind_shard(shard, args.dataset)]
    if not bound:
        parser.error("No bound historical attempts")
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "manifest.json").write_text(
        json.dumps(
            {
                "version": "offline_quixbugs_replay@1",
                "paid_calls": 0,
                "historical": str(args.historical),
                "dataset": str(args.dataset),
                "runtime_sha256": {
                    str(p): digest(p)
                    for base in (
                        Path("backend/app/verified_change"),
                        Path("backend/app/verified_coding"),
                    )
                    for p in sorted(base.glob("*.py"))
                },
                "attempts": [
                    {
                        "shard": shard,
                        "program": row[0],
                        "arm": row[1],
                        "historical_status": row[2],
                        "response_files": row[4],
                        "replayable": bool(row[3]),
                    }
                    for shard, row in bound
                ],
                "limits": [
                    "Saved model proposals, no new reasoning or catch-rate estimate.",
                    "Public algorithm bugs, not representative real-user changes.",
                    "Missing historical responses remain missing; no invented replacements.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    rows = []
    for shard, (name, arm, previous, responses, _files) in bound:
        row = {"shard": shard, "program": name, "arm": arm, "historical_status": previous}
        if not responses:
            row["status"] = "historical_response_unavailable"
        else:
            directory = args.output / f"{name}-{arm}"
            directory.mkdir()
            versions = versions_for(args.dataset, name)[arm]
            client = FakeLLMClient(responses)
            try:
                outcome = ChangeVerifier(
                    client,
                    responses[0].model,
                    DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=5)),
                    limits=ChangeLimits(max_retries=0),
                ).verify(versions, analyse(versions, name), INTENT)
                row.update(
                    status=outcome.certificate.status.value,
                    cases=outcome.certificate.cases_compared,
                    reason=outcome.certificate.reason,
                    replay_requests=len(client.requests),
                )
                (directory / "report.md").write_text(render(outcome))
                (directory / "certificate.json").write_text(
                    outcome.certificate.model_dump_json(indent=2)
                )
                (directory / "trace.json").write_text(json.dumps(outcome.events, indent=2))
            except Exception as exc:
                row.update(status="replay_error", reason=f"{type(exc).__name__}: {str(exc)[:200]}")
        rows.append(row)
        (args.output / "progress.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
    summary = {
        "paid_calls": 0,
        "attempts": len(rows),
        "rows": rows,
        "by_arm": {
            arm: dict(Counter(r["status"] for r in rows if r["arm"] == arm))
            for arm in ("bug", "control")
        },
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
