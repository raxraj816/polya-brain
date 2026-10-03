# Chapter 172: incomplete comparison coverage

Implementation date: 2026-10-02. Harness `differential_harness@0.3.0`.

## Problem and delivered behavior

A few successful samples could previously lead to clean certification even when
the generator failed on other sizes or the reference timed out. A requested scale
generator could fail or supply malformed arguments and be silently skipped. Seven
failing checks in the initial eight-case probe reproduced these paths and the
missing bounded retry/report behavior.

The existing result counters now determine a `coverage_failure` property, without
adding a stored core field. Generator errors, reference timeouts and zero completed
comparisons prevent a clean agreement claim. Unusable requested scale inputs enter
the existing setup-error channel. The coding and change pipelines retry unusable
generation within their existing attempt ceiling; exhausted attempts deliver an
unverified result with the actual partial counts and reason retained.

Concrete counterexamples remain useful despite incomplete sampling. Change review
can still report an observed regression with the coverage limitation. Merely
intended observed differences cannot produce an `only_intended_changes` certificate
when other samples were unavailable. The coding pipeline rechecks coverage after
repair; resolving a counterexample alone cannot certify a partially tested repair.

The reports retain the concrete reason, including generator-error and timeout
counts. Previously completed comparisons remain in trace/certificate artifacts.
No model prompts, oracle answers or user code are altered to obtain a pass.

## Verification

- `backend/tests/test_differential_coverage.py`: ten controls, including actual
  sandbox partial generation/reference timeout/scale failure, bounded recovery,
  retained regressions, coding report projection and the post-repair decision gate.
  The post-repair decision test injects result objects; other execution tests use
  actual Docker and scripted model outputs. These scopes must not be conflated.
- `backend/tests/test_change_replay.py`: four checks for binding historical call
  order/telemetry, dataset identity, unavailable attempts and zero new replay cost.
- Original failures: `runs/launch-readiness/2026-10-02-coverage-before.xml/.log`.
- First focused regression group: `2026-10-02-coverage-after.xml/.log`, 78 passing
  checks, with change-report examples in `-after-temp/`.
- Additional final controls: `2026-10-02-coverage-final.xml/.log`, 14 passing checks.
- Full backend: `2026-10-03-coverage-full.xml/.log`, **1,325 passed, zero skips**,
  154.86 seconds, with scratch PostgreSQL and the pinned Docker sandbox. The total
  includes other current working-tree work, not just this chapter's 14 tests.
  Ruff lint/format, strict mypy on three changed runtime modules and
  `git diff --check` pass. There are 843 dependency deprecation warnings.

## Offline public-bug replay

`evals/verified_change/replay.py` uses the locally saved QuixBugs dataset and the
historical `runs/verified-change/quixbugs-v1/` responses. It verifies dataset source
hashes and matches each returned response to recorded call order, model, tokens
and cost before executing anything. Missing responses remain unavailable. It
freezes source/response hashes before replay, uses only `FakeLLMClient`, explicitly
sets replay usage/cost to zero, and cannot dispatch a new provider request.

Each bug arm compares the dataset's corrected program with its buggy program;
each control compares the corrected program with an AST-reformatted equivalent.
Saved model input generators and equivalence functions are reused, not regenerated.
Reports, certificates, traces, historical statuses and missing attempts are retained
in `runs/launch-readiness/2026-10-02-quixbugs-offline-replay/`. New retry requests
with no saved response stop as unverified rather than inventing a response.

This is a replay of public algorithm-bug fixtures, not an independent live trial
or representative real-user code-change catch rate. The historical runtime differs
in more ways than this chapter alone, so changed outcomes are not an isolated
ablation of the coverage repair. False alarms, unverified attempts and missing
responses remain part of the denominator. Paid evaluations remain paused while
the recorded provider-cost reservation is unresolved.

The offline replay completed all **80 expected arm records across 40 programs**:

| Arm | Observed result | Missing or unverified |
| --- | --- | --- |
| Bug | 38 reported regressions | Two historical attempts unavailable |
| Equivalent control | 34 reported no behavior change; zero regression reports | Three unverified; three historical responses/attempts unavailable |

Thus 75 attempts had saved responses that could be replayed. The three unverified
controls are `flatten` (iterator limit), `sqrt` and `wrap` (reference timeouts).
They are abstentions, not passes. The historical seven control false alarms do
not recur with the replayed runtime, which includes other prior harness repairs;
this is not evidence that coverage checking alone fixed them. The two missing
programs are `shortest_paths` and `subsequences`; the fifth missing arm is the
`reverse_linked_list` control whose provider call failed. No missing response was
reconstructed. There were **zero new provider calls**.

## Limits

Zero execution errors do not prove adequate semantic coverage. A generator may
produce duplicate inputs or miss the important region without throwing an error.
The report states the actual sampled sizes and counts; these checks add no claim
of exhaustive input-space coverage. Model references/equivalence functions and
the same-process sandbox limitations from the preceding adversarial chapter
remain. Independent judgments and real-user usefulness are still required.
