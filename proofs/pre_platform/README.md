# Pre-Platform Proof Harness

This is the executable proof gate before full platform infrastructure.

It tests whether a thin PolyaBrain investigation loop can produce a more
auditable artifact than a direct model-style answer on the same realistic
technical investigation case.

## Run

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
- `evidence.json`
- `hypotheses.json`
- `verification_checklist.json`
- `report.md`
- `baseline_comparison.json`

## What This Proves

This harness proves the minimum product behavior, not the final platform:

- The loop creates explicit problem framing, evidence, hypotheses, checks, and report artifacts.
- The trace exposes reasoning modes such as `explore`, `reframe`, `compare`, `verify`, and `reflect`.
- Evidence items carry source metadata.
- Hypotheses avoid `novelty_score` and use evidence, checks, falsification criteria, confidence, and selection rationale.
- Verification includes deterministic/non-LLM checks.
- The output is compared against a direct LLM baseline fixture.

The baseline fixture should later be replaced or refreshed with actual direct model
outputs when an API-backed evaluation runner is added.
