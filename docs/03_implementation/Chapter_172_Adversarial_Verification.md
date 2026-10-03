# Chapter 172: adversarial differential verification

Implementation date: 2026-10-02. Harness `differential_harness@0.2.0`.
Scope: developer controls for false success in the existing coding and change
verification paths. These controls do not measure live problem-solving quality.

## Failures exposed

The first 25-case probe produced 19 failures and six passing controls. Python's
ordinary equality silently equates booleans and integers, and sometimes integers
and floats. The harness applied its stricter policy to ordinary sequences but
missed mapping keys, sets, unordered sequences and stated boolean/integer examples.
Set and frozenset results could also be treated as interchangeable.

Two iterators with different values after their first 10,000 items were accepted
because only their matching prefixes were compared. Required examples and pinned
regressions whose expected values or arguments could not be evaluated were silently
dropped. A saved passing result marker could override a sandbox timeout, nonzero
exit or truncated output.

Further probes exposed two snapshot failures (type-only argument mutation and
plain-object fields) and two exceptional-return mutation failures. A function can
change an input and then raise the same exception as the reference; exception
parity does not make those argument changes equivalent.

## Repair

- Collection checks retain recursive type comparison. Numeric-type relaxation
  can permit integer/float equivalence; it never equates booleans with numbers.
  Unordered sequence matching preserves multiplicity and recursive type rules.
  It uses a sorted fast path, then bounded matching; exceeding 50,000 matching
  comparisons yields an unverified result rather than guessing equivalence.
- Snapshots tag atomic types and preserve them in object fields. Mutation is
  checked on successful and exceptional returns, in absolute and relative modes.
- Iterator materialization beyond 10,000 items stops verification as incomplete.
  An iterator ending at exactly 10,000 remains comparable. This is a verification
  capacity limit, not a defect in the submitted implementation.
- Required checks that cannot be evaluated stop with an explicit reason.
- Transport completion is checked before interpreting the result marker.
- The existing coding certificate limitations retain the concrete stopping reason,
  so the delivered report explains the incomplete check. No core field was added.

## Evidence

`backend/tests/test_differential_adversarial.py` contains **32 developer controls**.
They cover negative cases and valid equivalents under the supported relaxations.
The actual Docker sandbox executes candidate and reference code. Model proposals
in the two pipeline integration checks are scripted `FakeLLMClient` responses.
Both the coding report and the change report say **Not verified** when an iterator
cannot be fully compared; the coding projection has failing verification and no
reusable success lesson. The reports and certificates are retained in the focused
test artifact directory.

The focused suite, including existing coding and change-verification tests, passes
**70 checks, zero skips**. Ruff lint/format and strict mypy on the two changed
runtime modules pass. Full-suite results are recorded in the readiness ledger.

Artifacts under `runs/launch-readiness/`:

- `2026-10-02-differential-adversarial-before.xml/.log`: 19 failures, six passes.
- `2026-10-02-differential-mutation-before.xml/.log`: two snapshot failures.
- `2026-10-02-differential-exception-before.xml/.log`: two failures, two passes.
- `2026-10-02-differential-complete.xml/.log` and `-complete-temp/`: final focused
  checks, including user-facing reports and certificates from both paths.
- `2026-10-02-differential-full.xml/.log`: full backend regression run.

Intermediate failures are preserved too. The integration fixtures initially used
identical old/new source (correctly taking the no-change shortcut), compared code
without accounting for its normalized trailing newline, and assumed an unverified
result had no reflection. The existing reflection correctly described failure with
no reusable lesson. Those were test assumptions corrected without changing product
behavior to satisfy them.

## Limits and next evidence

No live model calls, paid evaluation or external research were performed. These
cases challenge the verifier; they are not 32 independently solved hard problems.
Random differential testing still cannot prove correctness. Model-generated
references and custom equivalence functions can share a wrong interpretation.
Candidate and reference namespaces share one sandbox process; this mechanism is
not a security proof against deliberately self-inspecting or harness-tampering
programs. Large or unsupported comparisons may remain unverified.

The original live comparison failures and the unresolved provider-cost reservation
remain intact. Next evidence should exercise realistic failing changes and
independent user specifications, keeping catch rate, false alarms, verification
overhead and human judgments separate. No public-launch verdict changes.
