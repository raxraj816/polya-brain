# Chapter 13-E Verifier Benchmark

This benchmark compares acceptance/rejection at a fixed verification checkpoint
across six fictional held-out cases in two families: multi-rule decisions and
structured debugging.

Conditions:

- `direct_model`: one model receives the complete structured observation;
- `full_context`: the same model receives all observation documents plus
  distractors;
- `ordinary_retrieval`: the same model receives fixed lexical top-two results;
- `polya`: the deterministic verifier factory executes typed criterion checks.

Run only with fictional non-confidential fixtures:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
  .venv/bin/python evals/chapter_13e/run_live_verifier_benchmark.py --repetitions 3
```

If a provider interruption occurs after case artifacts are written, resume
without repeating completed calls:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
  .venv/bin/python evals/chapter_13e/run_live_verifier_benchmark.py \
  --repetitions 3 --resume-dir evals/chapter_13e/live_runs/YYYY-MM-DD/RUN_ID
```

The gate measures verdict correctness, false passes, criterion coverage, calls,
tokens, and latency. It deliberately does not claim end-to-end or general
intelligence superiority.

The configured DeepSeek reasoning endpoint may require
`OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false` because strict OpenRouter
parameter routing can return no eligible provider. The typed parser and scoring
still reject malformed or unsupported verdicts.
