# Chapter 13-N: Source-Visible Investigation Delivery

Status: local delivery validated; fresh user-case proof remains pending. This is an experimental source/check
workflow, not general repository repair or hostile-code verification.

## Public workflow

```bash
./polyabrain investigate "Explain the failure and propose the smallest correction" \
  --source /path/to/case/source.py --check /path/to/case/check.py \
  --artifact-root /path/to/case \
  --experimental-source-patch --allow-code-execution \
  --max-model-calls 4
```

The source and check must be distinct Python files in the same allowed directory.
The check defines `verify(implementation)` and raises when the observed behavior
is wrong. Source and check load inside a Python 3.14 container with standard
library dependencies. The pair must fit a bounded 18,000-character serialized
payload. No host directories are mounted and no original files are edited.

The CLI admits only the selected complete snapshots and derives the declared
task shape without a representation model call. Actual constraint discovery and
gap detection still run. The shared runtime composer registers the specialized
proposal capability only for the explicit source/check workflow. Semantic work
uses the existing OpenRouter configuration and resource limits.

The model proposes one exact replacement, a diagnosis, and a check interpretation.
Both files must still match the admitted snapshots at execution. Separate
ephemeral containers execute the same check against the original source and the
candidate edit. A verified candidate requires a completed failing original check
and a completed passing candidate check. An already-passing check, missing test
result, timeout, truncated output, or failing edit cannot verify a correction.

## Inspectable result

Alongside the normal trace and report, the run exports:

- `candidate_edit.json`: exact replacement and original content hash.
- `candidate.patch`: a reviewable textual diff; apply changes manually in the
  real project and run its full test suite before accepting the fix.
- `execution.json`: both execution results, source/check/candidate hashes, and
  the explicitly limited verification scope.
- `hypotheses.json`: the original proposal and uncertainties recorded before
  execution. The final report distinguishes these from measured outcomes.

Checkpoint recovery retains the selected workflow and its budgets. Repeat the
original artifact roots, execution opt-in, and budget settings when resuming.
Normal text-only investigations and the API do not silently gain this capability.

## Verification boundary

The diagnosis remains a proposal. Identifier overlap is a grounding check, not
proof of causal correctness. Passing a supplied check establishes only that
check's coverage. The check and implementation still share a Python process;
adversarial code can tamper with the in-process harness. The result must not be
represented as independent attestation of hostile code. Further integration
checks and human review remain required before acting on a candidate edit.

No multi-file edits, dependency installation, external network, host writes,
automatic deployment, or broad repository repair are enabled by this workflow.

## Observed delivery evidence

A live public-CLI invocation on the existing historical PySnooper reduced
reproduction proposed the concrete `output_path` to `output` correction using
one model call and 1,619 tokens. Its original check failed with exit 1 and its
candidate check passed with exit 0 in separate containers. Total measured
invocation time was approximately 14.57 seconds. The live artifacts are private
under `runs/investigator/chapter13n-live-source`.

This is a new execution of a historical, contamination-prone reduced case, not
a fresh held-out case, full-project reproduction, or competitive superiority
claim. The model's before-execution wording in that initial live report exposed
a report-timing issue; the current report renderer uses measured outcomes and
preserves the earlier wording only in the proposal artifact.

The full local suite passed 439 tests with database integration enabled against
a fresh isolated Postgres/pgvector instance. Repository lint, backend formatting,
and strict mypy pass.

Regression coverage includes the shared production composer, one-call successful
proposal, unchanged host source, preexisting-pass rejection, ineffective-edit
rejection, explicit execution permission, root containment, missing-provider
accounting, and existing snapshot-integrity checks. CI now prepares the pinned
Docker image so sandbox tests run rather than silently skipping for missing images.

The user-facing workbench, independent human review, fresh real-user cases,
cross-case transfer, and cloud delivery remain open.
