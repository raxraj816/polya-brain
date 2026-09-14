# Chapter 13-L: Investigator Runtime Delivery

Status: local runtime delivery gate complete. Broader product delivery remains open.
Chapter 13-M adds local checkpoint recovery and clarification continuation to
the delivery baseline described here.

## Product behavior

`./polyabrain investigate` now composes the same Cognitive Runtime used by
the API. It executes the actual problem-understanding, acquisition, evidence,
hypothesis, execution, verification, and reflection capabilities selected by the
controller. It exports their real outputs. The older curated-template workflow
is available as `./polyabrain proof`; no template answer can silently substitute
for a failed runtime investigation.

```bash
make setup
./polyabrain investigate "What is 17 * 6?" --offline
./polyabrain investigate "Fix it." --offline
./polyabrain investigate "Your problem, observations, and success criteria" --max-model-calls 12
```

Semantic tasks use the existing OpenRouter configuration. `--offline` clears
model/search credentials in memory and enforces zero model and external calls.
Known deterministic representation and arithmetic now have separate zero-call
reservations, so the hard budget does not reject a procedure that uses no model.
Unknown inputs cannot enter those deterministic capabilities.

To read an explicit file, allow its directory and quote the file in the problem:

```bash
./polyabrain investigate "Using only the manual at '/path/to/manual.txt', determine the documented timeout and state the exact rule." --artifact-root /path/to --offline
```

Use `--allow-code-execution` to enable the configured ephemeral Docker Python
tool. It does not permit modifying source files on the host. The specialized
Chapter 13-K source-patch proposal capability is still experimental and is not
registered by the default production composer.

## Auditable outputs

Each invocation creates a new directory under `runs/investigator/`, or the
specified `--output-root`. `--run-id` selects a new plain folder name. There is
no destructive cleanup option in the runtime command.

- `report.md` and `report.json`: conclusion, confidence, evidence for/against,
  checks, contradictions, open questions, next action, and audit reference.
- `state.json`, `trace.json`, `evidence.json`, `hypotheses.json`, `plan.json`,
  `execution.json`, `verification.json`, and `reflection.json`: actual outputs.
- `run.json`: status, cycles, elapsed time, budgets, resource usage, used
  capability versions, code revision, dirty-worktree flag, and limitations.
- `manifest.json`: hashes of the exported files. This detects accidental
  changes; it is not an authenticated signature or permission to replay state.
- `error.json`: safe failure type when an unexpected error or interruption
  prevents normal export.

Directories use owner-only access and files use owner-only read/write access.
Known credential patterns are redacted. Settings and API keys are never dumped.
Artifacts can still contain user-supplied source or other sensitive problem
data; the default output root is gitignored.

Exit codes are `0` for a verified outcome, `2` for a clarification pause or
invalid CLI syntax, `3` for no verified outcome, `1` for configuration/runtime
failure, and `130` for interruption. `--json` supplies the precise runtime
status for automation. Chapter 13-M supports `polyabrain resume RUN_DIRECTORY
--answer "full revised problem"` using the original runtime options; the
persisted API also supports responding in-session.

## Verification fixes

Source-patch execution previously checked admitted URIs and then reopened the
files without comparing their contents to the admitted excerpts. It could
therefore execute changed source or a replaced regression check. Version
`source_patch_sandbox@0.2.0` requires full matching snapshots, rejects partial
excerpts and inconsistent line identities before container launch, and records
hashes of source, check, and patched source. Historical evaluation files retain
their original versions and are not retroactively rescored.

These are integrity checks. Passing a supplied test does not establish that the
test is sufficient or that a lexical diagnosis is causally correct. Code and
check still execute inside one isolated Python environment; adversarial
tampering with the in-process test harness remains a hardening requirement
before accepting hostile code as independently verified.

The persisted API now records accepted execution outputs and reflection from
canonical state, independently of the event names used by fused capability
producers. This closes a database-only defect in which reports lost reflection
and the audit trail omitted the independent recalculation output.

## Validation

The full local suite passes **423 tests**, including all database integration
tests against a fresh migrated Postgres/pgvector instance and the available
Docker source-patch checks. Repository Ruff, formatting, and strict mypy pass.
All six legacy proof bundles and all ten Chapter 11 examples verify, and Docker
Compose configuration validates. No live provider comparison was rerun for this
chapter; these results establish implementation behavior, not a new competitive
benchmark win.

Historical raw live-run files remain local pending export review. The portable
`evals/chapter_13k/historical_qualification_summary.json` preserves the frozen
generation-4 metrics, limitations, original artifact hash, and the requirement
to requalify current code. It does not replace independent review of the raw
traces or the remaining fresh-case and human-use gates.

## Remaining product gates

This is local delivery, not completion of the end-to-end product. Independent
blind review, fresh field cases, controlled procedure transfer, broader
repository investigation, broader recovery beyond Chapter 13-M's safe boundaries, frontend interaction,
authentication, tenant isolation, deployment, and pilot repeat use remain open.
Confidence labels are heuristic. Normalized cost is not currency. Local runs
do not load the API's durable memory stores. None of this chapter's checks
establishes general intelligence or broad competitive superiority.
