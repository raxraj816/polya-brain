# Chapter 13-G: Deadline-Aware Cognition

Status: complete in the current working tree.

## Problem

Model calls are not a sufficient compute budget. A two-call route can still be
slower than a six-call route if a provider hangs, retries, or repairs malformed
output. Polya must govern wall-clock time explicitly and fail closed when a
capability's worst-case timeout cannot fit the remaining run deadline.

## Mechanism

- Extend the experimental cognitive budget with maximum duration.
- Charge measured capability duration through audited resource events.
- Make declared capability timeout part of the controller's hard reservation
  check.
- Apply identical rules to normal kernel actions and compiled procedures.
- Keep provider timeout failures distinct from reasoning failures and never
  turn a deadline into a forced conclusion.

The earlier LLM-boundary correction supplies a total deadline across attempts,
backoff, and structured-output repair. Chapter 13-G governs the larger run that
may contain deterministic, external, human, and model capabilities.

## Implemented

- `CognitiveResourceBudget.max_duration_ms` declares the hard run envelope.
- `CognitiveResourceUsage.duration_ms` charges measured capability time through
  append-only `cognitive_resource_usage` events.
- Controller reservations compare the registered capability timeout with the
  remaining duration before ranking.
- The kernel also measures real elapsed wall-clock time, including controller
  overhead, and emits `cognitive_run_deadline_exhausted` before returning
  `insufficient_evidence`.
- Governed compiled procedures use the same timeout reservation and actual
  duration charging path.
- Model capability versions include the configured route fingerprint, so a
  different endpoint starts a new health profile.

## Verification

- A 120-second web capability is rejected when only 20 seconds remain, and a
  five-second inspector is selected.
- A zero-duration budget executes no capability, creates no final answer, and
  emits the terminal deadline event.
- Actual non-negative duration is present in usage and observation traces.
- A compiled procedure with no remaining duration is rejected before step one.
- Full suite: 317 passed, 23 skipped.
- Ruff, format check, and strict mypy over 99 source files pass.
