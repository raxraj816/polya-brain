"""Offline replay must bind source identity and saved call order before execution."""

import hashlib
import json

import pytest
from evals.verified_change.replay import bind_shard
from test_verified_change import response


@pytest.fixture
def recorded(tmp_path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    source = dataset / "f.py"
    source.write_text("def f(): return 1")
    shard = tmp_path / "shard"
    (shard / "spend").mkdir(parents=True)
    (shard / "manifest.json").write_text(
        json.dumps(
            {
                "programs": ["f", "missing"],
                "quixbugs_files_sha256": {"f.py": hashlib.sha256(source.read_bytes()).hexdigest()},
            }
        )
    )
    saved = response({"generator_code": "def generate(rng, size): return ()"})
    (shard / "spend" / "1.response.json").write_text(saved.model_dump_json())
    (shard / "f.json").write_text(
        json.dumps(
            {
                "bug": {
                    "status": "regressions_found",
                    "model_calls": [
                        {
                            "outcome": "ok",
                            "model": saved.model,
                            "input_tokens": saved.usage.input_tokens,
                            "output_tokens": saved.usage.output_tokens,
                            "cost_usd": saved.usage.estimated_cost_usd,
                        }
                    ],
                },
                "control": {"status": "unverified", "model_calls": [{"outcome": "LLMClientError"}]},
            }
        )
    )
    return shard, dataset


def test_binding_retains_missing_attempts_and_clears_replayed_cost(recorded):
    rows = bind_shard(*recorded)
    assert len(rows) == 4
    assert rows[0][3][0].usage.estimated_cost_usd == 0
    assert rows[0][4][0]["sha256"]
    assert all(not row[3] for row in rows[1:])


@pytest.mark.parametrize("corruption", ["source", "telemetry", "extra_response"])
def test_replay_rejects_unbound_or_changed_artifacts(recorded, corruption):
    shard, dataset = recorded
    if corruption == "source":
        (dataset / "f.py").write_text("def f(): return 2")
    elif corruption == "telemetry":
        path = shard / "spend" / "1.response.json"
        data = json.loads(path.read_text())
        data["usage"]["input_tokens"] += 1
        path.write_text(json.dumps(data))
    else:
        (shard / "spend" / "9.response.json").write_text("{}")
    with pytest.raises(ValueError):
        bind_shard(shard, dataset)
