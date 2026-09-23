# Chapter 13-F Adaptive Scheduler Benchmark

This offline routing benchmark compares the static Chapter 13-D controller
with the Chapter 13-F performance policy on 12 held-out task families. It uses
five repetitions and rotates controller execution order. The prior history for
each task family represents one of four capability regimes: healthy, degraded,
recovered, or version-changed.

The held-out decision is never inserted into the prior ledger. A deterministic
fixture independently scores whether the selected route resolves the present
case and assigns calls, tokens, and latency. This is a scheduler benchmark, not
evidence that PolyaBrain is generally more intelligent than current models.

Run it from the repository root:

```bash
PYTHONPATH=backend .venv/bin/python \
  evals/chapter_13f/run_adaptive_scheduler_benchmark.py \
  --repetitions 5 --write-artifact
```
