# First-proposal source-repair recovery

This is a developer-authored controlled failure experiment. The first proposal
is deliberately injected: it fixes exponential retry backoff but leaves an
incorrect inclusive deadline. The production runtime must execute that candidate,
observe failure, recover once against the original source/check, and freshly
verify its replacement. It cannot modify host files or the check.

`case.json` was frozen before the first attempt. Both admitted files and the task
are visible to the model. The 3,000 seeded independent comparisons are withheld
until the run ends. The test suite checks that the original and injected partial
fix both fail those comparisons, and the reference correction passes.

```sh
PYTHONPATH=backend:. .venv/bin/python -m evals.chapter_13p.source_recovery.run \
  --output runs/source-recovery/new-run --model google/gemini-3.7-flash
```

Existing configured provider credentials and the pinned Docker sandbox are used.
`--offline` injects the first proposal without calling a remote model afterward.
Each run requires a new directory; every provider request/response and all runtime
artifacts are retained. The runtime's six-call ceiling includes the injected
proposal. The summary separately counts real provider calls and their reported
tokens; an injected response is not model intelligence or remote compute.

| Run | Result | Real calls | Reported real tokens | Runtime elapsed |
| --- | --- | ---: | ---: | ---: |
| `retry-deadline-before` (offline) | Insufficient evidence | 0 | 0 | 0.50 s |
| `retry-deadline-live-before` | Insufficient evidence | 2 | 10,030 | 19.90 s |
| `retry-deadline-live-after` | Completed; independent checks pass | 1 | 3,290 | 11.43 s |
| `retry-deadline-live-after-repeat` | Completed; independent checks pass | 1 | 3,334 | 11.71 s |

Artifacts are under `runs/source-recovery/`. The failed live run routes through
the generic planner and never produces a verified repair. Both repaired runs
record patch verdicts `[false, true]`, retain failed verification, keep the host
snapshots unchanged and make only the successful replacement eligible for memory.
Elapsed figures cover the runtime, excluding export and independent scoring.

This proves a bounded recovery mechanism on one controlled case. It does not
prove autonomous initial diagnosis, general repair reliability, real-user value,
or an advantage over a competing tool. The comparison is before/after the runtime
repair, not a matched competitive baseline. These costs exclude development work.
