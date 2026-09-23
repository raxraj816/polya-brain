# Chapter 13-D On-Demand Task Learning Proof

This offline proof runs six deliberately fictional micro-world cases across
three paired structural families. The real Polya controller, capability
registry, kernel, hard resource budget, task-model trace, verification gate,
and procedural-memory transfer are exercised.

Run from the repository root:

```bash
PYTHONPATH=backend .venv/bin/python \
  evals/chapter_13d/run_micro_world_proof.py
```

The first case in each pair deliberately attempts public search, which cannot
contain the fictional rule, then recovers through the supplied authoritative
manual. Only a completed verified run may teach procedural memory. The transfer
case must inspect the supplied manual directly, avoid the known failed search,
and verify the new case-specific answer.

The output also describes direct, full-context, and ordinary-retrieval
information conditions. Those three conditions are deterministic simulations
in this offline proof. They test the scoring and reporting contract; they are
not evidence that one real system beats another. A scientific product claim
requires a later same-model repeated held-out live comparison.

With an explicitly configured non-confidential provider, probe the fused
post-evidence semantic path:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
PYTHONPATH=backend .venv/bin/python \
  evals/chapter_13d/run_live_on_demand_probe.py
```

The probe passes only when the fictional answer is verified, the audit task
model is present, and hypothesis/plan/analysis plus conclusion/reflection use
no more than two premium-model calls after evidence admission.

Run the stricter raw-input-to-report probe with local unfamiliar knowledge:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
PYTHONPATH=backend .venv/bin/python \
  evals/chapter_13d/run_live_end_to_end_probe.py
```

This path must construct the problem, detect the explicit gap without a model,
inspect the referenced manual, admit its evidence, deliberate, verify, reflect,
and report within three normal model calls total.

Run the live four-condition unfamiliar-corpus benchmark:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
PYTHONPATH=backend:. .venv/bin/python \
  evals/chapter_13d/run_live_four_condition_benchmark.py --repetitions 3
```

The four conditions are closed-book direct, full context, ordinary deterministic
top-1 retrieval plus answer model, and Polya adaptive retrieval/evidence gate/
deterministic verified procedure. The narrow gate may establish an efficiency
claim only for exact unfamiliar-corpus lookups. It never establishes a general
intelligence win.
