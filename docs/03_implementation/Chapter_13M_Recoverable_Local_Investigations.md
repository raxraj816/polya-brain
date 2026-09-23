# Chapter 13-M: Recoverable Local Investigations

Status: local recovery gate complete; broader product delivery remains open.

## User workflow

The local Investigator can continue a bounded run and accept a revised problem
after a missing-input pause, without losing session identity or resetting its
resource budget. Every invocation exports to a new private directory. Earlier
reports and evidence remain available for comparison.

```bash
./polyabrain investigate "What is 17 * 6?" --offline --max-cycles 3 --run-id paused
./polyabrain resume runs/investigator/paused --offline --run-id continued

./polyabrain investigate "Fix it." --offline --run-id needs-context
./polyabrain resume runs/investigator/needs-context --offline --answer "What is 17 * 6?"
```

`--max-cycles` bounds this invocation. Model calls, tokens, external calls,
normalized cost, and active execution time retain the original cumulative
limits. Time waiting for a person to reply is excluded. Repeat the original
runtime options, including `--offline`, artifact roots, code execution opt-in,
and any resource ceilings. The original report directory, current code,
dependency versions, and configuration must match. Credential values are neither saved nor required to remain the
same; provider availability and configuration must match.

`--answer` is the complete revised problem, including the requested context.
It is accepted only for a missing-input pause. The runtime rebuilds its
representation, evidence, plan, and verification, preserving prior charges and
an explicit link to the parent audit. Old conclusions cannot satisfy the new
problem's checks. An answer grants no additional tool permissions.

## Recovery authority and failure behavior

`recovery.json` contains a local recovery identifier. Executable state resides
in an owner-private SQLite store at `~/.local/state/polyabrain`; override the
directory with `POLYABRAIN_RECOVERY_HOME`. No Postgres or Redis service is needed.
Editable `state.json`, report files, and manifests are never loaded as runtime
state. The private store is trusted application data owned by the local user;
this is not an authenticated multi-user or portable checkpoint service.

Each capability dispatch first commits an in-flight marker. A completed
observation commits its updated state and actual resource ledger. A process
lease prevents a second process from resuming live work; an atomic transaction
transfers recovery rights from the parent to one continuation. A failed
transaction leaves the parent's recovery right available.

If a process dies at a saved boundary, completed capabilities are not replayed.
If it dies during dispatch, the outcome and usage may be unknown: automatic
replay is refused. This conservative stop also covers a crash after a call
finishes but before its result is durably saved. This chapter does not infer
zero usage from a missing response or promise exactly-once external execution.
A slow checkpoint write is charged as active overhead and cannot cause a
capability to dispatch after its resource reservation becomes invalid.

Known secret patterns are redacted before private persistence and exports. If
redaction changes checkpoint state, that snapshot cannot be resumed; altered
code or evidence must not become executable by accident. Recovery identifiers
are application references, not credentials. The store can still contain
user-supplied sensitive problem data, just like the private report bundle.

## Current boundaries

- macOS and Linux process leases use POSIX file locking; Windows is not supported.
- A checkpoint is consumed once. Use the new continuation directory for the
  next pause; copying a report cannot duplicate recovery rights.
- Completed and insufficient-evidence terminal runs cannot be reexecuted via
  resume. A new investigation has a new budget and must be requested explicitly.
- In-flight calls require manual reconciliation. No provider reconciliation or
  remote job attachment is implemented yet.
- Recovery preserves admitted evidence snapshots; it does not refresh web
  sources or establish that previously inspected artifacts are still current.
- No automatic retention or deletion is implemented. Deleting report bundles
  does not delete private recovery records. Removing the configured recovery
  directory while no local investigations are running deletes all local
  checkpoints and permanently disables recovery for those bundles.
- Export failure after terminal completion may leave only the private saved
  state; a terminal-report regeneration command is still missing.
- Durable learned memory, frontend interaction, cloud deployment, authentication,
  tenant isolation, independent review, fresh cases, and pilot repeat use remain
  separate open product gates.

## Verification

All **433 tests pass**, including database integration against an isolated,
fresh migrated Postgres/pgvector instance and ten new recovery regressions.
Repository Ruff, backend formatting, and strict mypy pass. A manual public CLI
run paused after three cycles and resumed to `17 * 6 = 102`, with zero model
calls, preserved session identity, independent arithmetic checks, and a new report.

Validation covers public CLI continuation and clarification, retained identity
and resources, no replay of completed calculation, modified export isolation,
duplicate and concurrent claims, in-flight refusal, redaction, code/configuration
mismatch, atomic rollback, and slow checkpoint budget enforcement. These are
recovery correctness checks, not a new competitive benchmark or product-value claim.
