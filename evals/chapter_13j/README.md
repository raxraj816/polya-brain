# Chapter 13-J Adversarial Epistemic-Control Evaluation

This track compares PolyaBrain with a direct same-model agent on synthetic,
non-confidential evidence environments. Both conditions receive the same
pre-structured problem, search batches, source metadata, call limits, token
limits, and instruction that retrieved content is untrusted data.

The cases include answerable controls and intentionally unanswerable tasks.
Scoring separates answer accuracy from abstention precision/recall and records
unsupported conclusions, forbidden injected output, provenance, verification,
query revision, model calls, external calls, tokens, and latency.

Run a paid live comparison only with explicit opt-in:

```bash
set -a
source .env
set +a
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
  .venv/bin/python evals/chapter_13j/run_epistemic_control_comparison.py \
  --repetitions 3
```

Passing this synthetic gate is evidence of bounded epistemic-control value,
not general-intelligence or open-world superiority.

After a completed run, create condition-blinded artifacts and keep the key away
from reviewers until scoring is complete:

```bash
.venv/bin/python evals/chapter_13j/build_blind_review_packet.py \
  evals/chapter_13j/live_runs/YYYY-MM-DD/RUN_ID/summary.json
```
