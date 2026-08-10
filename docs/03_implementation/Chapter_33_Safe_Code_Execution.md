# Chapter 33: Safe Code Execution and Test Runner

Status: complete for bounded Python programs and assertion-based tests.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Isolation Boundary

The `python_sandbox` capability executes only a plan task explicitly assigned
to it. It is disabled by default and requires a trusted Docker daemon plus the
configured, digest-pinned Python image.

Every execution uses an ephemeral container with:

- no network namespace access;
- no host filesystem mounts;
- a read-only root filesystem;
- a small `noexec,nosuid` tmpfs scratch directory;
- non-root UID/GID;
- all Linux capabilities dropped;
- `no-new-privileges`;
- CPU, memory, PID, file-descriptor, wall-clock, code-size, test-count, and
  combined-output limits;
- a unique container name that is forcibly removed on timeout or output-limit
  termination.

The runtime image is pinned to an immutable digest. Missing Docker, missing
image, invalid parameters, timeout, and output exhaustion fail closed through
typed capability observations.

## Test Runner

A task supplies bounded Python source plus up to twenty assertion programs.
The runner returns:

- stdout and stderr;
- exit code and runtime;
- timeout and truncation flags;
- number of tests requested;
- a structured pass/fail and error-type record for every executed assertion.

A failing implementation or assertion is a valid observed execution result,
not a fabricated capability failure. The result becomes an execution artifact
and evidence for the later verifier. Isolation-backend failures remain failed
capability observations and route through recovery.

## Controller Guard

The planner is told the actual available execution-tool set. It cannot emit a
`python_sandbox` task when code execution is disabled. The LLM proposes code and
tests; the deterministic controller selects the action, the container performs
the execution, and the verifier decides whether the outcome is acceptable.

## Verification

Live Docker tests prove:

- a correct program and assertion pass;
- a failing assertion is reported structurally;
- outbound network access is blocked;
- root filesystem writes are blocked;
- an infinite loop is terminated;
- excessive output is truncated and rejected;
- an allocation above the memory boundary cannot complete;
- capability results contain audit and execution artifacts.

These tests skip only when Docker or the pinned image is unavailable; on the
development machine they run against the real container backend.
