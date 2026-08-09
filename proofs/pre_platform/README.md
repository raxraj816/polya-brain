# Pre-Platform Proof Harness

This is the executable proof gate before full platform infrastructure.

It tests whether a thin PolyaBrain investigation loop can produce a more
auditable artifact than a direct model-style answer on the same realistic
technical investigation case.

## Run A Free-Form Investigation

```bash
./polyabrain investigate "Our API p95 latency jumped after deploy. Should we add Redis or inspect the query path first?" --clean
python3 proofs/pre_platform/verify_pre_platform_proof.py --run-dir proofs/pre_platform/runs/our_api_p95_latency_jumped_after_deploy
```

The CLI accepts arbitrary problem input and writes the same artifact bundle as
the original fixed harness.

## Run The Original Proof Case

```bash
python3 proofs/pre_platform/run_pre_platform_proof.py --clean
python3 proofs/pre_platform/verify_pre_platform_proof.py
```

The runner writes file-based artifacts under:

```text
proofs/pre_platform/runs/cache_investigation/
```

Generated artifacts:

- `trace.jsonl`
- `direct_llm_baseline.md`
- `case.json`
- `evidence.json`
- `hypotheses.json`
- `verification_checklist.json`
- `report.md`
- `baseline_comparison.json`

## Run Curated Cases

```bash
./polyabrain investigate --case proofs/pre_platform/cases/deploy_healthcheck_regression.json --clean
./polyabrain investigate --case proofs/pre_platform/cases/memory_growth_worker.json --clean
./polyabrain investigate --case proofs/pre_platform/cases/search_ranking_drop.json --clean
./polyabrain investigate --case proofs/pre_platform/cases/billing_webhook_duplicates.json --clean
python3 proofs/pre_platform/verify_pre_platform_proof.py --all
```

## Direct LLM Baseline

By default, the CLI uses `--baseline-provider auto`. It prefers OpenRouter when
`OPENROUTER_API_KEY` and `OPENROUTER_MODEL` are available, otherwise it uses the
OpenAI Responses API when `OPENAI_API_KEY` is available. If no supported key is
available, it writes an explicit local direct-answer template so the proof can
still run offline.

To force an OpenRouter baseline:

```bash
set -a
. ./.env
set +a
./polyabrain investigate --case proofs/pre_platform/cases/cache_investigation.json \
  --baseline-provider openrouter --clean
```

To force a real OpenAI baseline:

```bash
OPENAI_API_KEY=... ./polyabrain investigate "Investigate this technical problem..." --baseline-provider openai --clean
```

To smoke-test the OpenAI-compatible HTTP runner without an external API call:

```bash
python3 proofs/pre_platform/verify_openai_baseline_runner.py
```

## What This Proves

This harness proves the minimum product behavior, not the final platform:

- The loop creates explicit problem framing, evidence, hypotheses, checks, and report artifacts.
- The trace exposes reasoning modes such as `explore`, `reframe`, `compare`, `verify`, and `reflect`.
- Evidence items carry source metadata.
- Hypotheses avoid `novelty_score` and use evidence, checks, falsification criteria, confidence, and selection rationale.
- Verification includes deterministic/non-LLM checks.
- The output is compared against a direct LLM baseline runner or an explicit offline fallback.

The live-provider baseline runners are intentionally only baselines.
PolyaBrain's own artifact contract stays deterministic in this pre-platform
proof so failures are easy to inspect.

Live baseline comparisons measure the current direct model honestly. Structural
audit-section scoring alone is not evidence that PolyaBrain is more useful or
lower-overhead; inspect the direct answer and the Polya report together.
