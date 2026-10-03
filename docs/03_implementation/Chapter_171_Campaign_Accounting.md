# Chapter 171 — Aggregate evaluation accounting

Status: offline inventory complete for the specified artifacts; paid evaluation
remains paused. Snapshot: 2026-10-03. This is resource-accounting evidence, not
product-quality evidence or invoice reconciliation.

## Finding

The historical ledgers covered overlapping but different subsets of the same $5
campaign. The verified-coding ledger included the original matched coding batches,
its later coding batches, CLI demos and QuixBugs runs, but omitted both source-packet
batches. Adding two summary totals would double-count the original matched batches.

The new inventory instead reads each guarded call's reservation, reported cost and
saved response. Returned response IDs and contents are checked; duplicate paths and
identical returned responses are counted once. Explicitly selected CLI traces cover
calls made outside the spend guard. No historical artifacts were changed.

| Accounting category | Amount / count |
| --- | --- |
| Guarded returned calls | 512, each response agrees with its reported ledger |
| Additional trace-only calls | 9, without saved provider response IDs |
| Total reported through responses or traces | $4.38000975 |
| Unresolved guarded calls | 10 |
| Retained local reservations | $0.58703925 |
| Recorded reported costs plus reservations | **$4.96704900** |
| Nominal difference from $5 | **$0.03295100; not spendable clearance** |
| Duplicate returned response IDs found | 0 |

The earlier `runs/verified-coding/campaign-ledger.json` total of $4.79385600
reconciles exactly after adding the omitted $0.17319300 of source-packet reported
costs and reservations. Its `remaining_usd` and `worst_case_total_usd` are historical
labels, not a current balance or a proven invoice upper bound. Preserve that file.
The original launch-readiness subset is also preserved.

## Unresolved calls

Paths below are relative to `runs/`; numbers identify spend-ledger call stems.

| Batch / call | Retained reservation |
| --- | --- |
| launch-readiness/2026-10-02-source-packet-v2 / 11 | $0.04337250 |
| verified-coding/2026-10-02-dev-v2 / 5 | $0.06386025 |
| verified-coding/2026-10-02-dev-v3 / 13 | $0.05881050 |
| verified-change/quixbugs-v1/shard-1 / 16 | $0.05978925 |
| verified-change/quixbugs-v2/shard-2 / 8 | $0.06049800 |
| verified-change/quixbugs-v2/shard-3 / 10 | $0.06030825 |
| verified-change/quixbugs-v2/shard-4 / 10 | $0.06022875 |
| verified-change/quixbugs-v2b/shard-1 / 9 | $0.06050925 |
| verified-change/quixbugs-v2c / 8 | $0.05967675 |
| verified-change/quixbugs-v2d / 1 | $0.05998575 |

The two interrupted coding calls have no unknown marker; their outstanding
reservations are still retained. Failure classification does not reconcile billing.
An HTTP 402 observed later cannot establish the cost of earlier missing responses.

The Chapter 174 development trace `runs/verified-claims/dev-1/trace.json` has no
itemized model calls. Its documented refusal is not accompanied by saved billing
proof. The inventory records this as a coverage gap, not a zero-cost call. The call
count and totals above exclude that unquantified gap.

## Reproduce and inspect

Run from the repository root with a new output path (existing audits are not
replaced):

```sh
.venv/bin/python -m evals.launch_readiness.spend_audit \
  --root runs/launch-readiness --root runs/verified-coding --root runs/verified-change \
  --trace runs/verified-coding/cli-smoke/smoke-kth/trace.json \
  --trace runs/verified-change/demo-prorate/trace.json \
  --trace runs/verified-change/demo-units/trace.json \
  --trace runs/verified-change/demo-units-2/trace.json \
  --trace runs/verified-change/demo-units-3/trace.json \
  --trace runs/verified-claims/dev-1/trace.json \
  --output runs/launch-readiness/2026-10-03-campaign-inventory.json
```

The JSON contains per-call accounting, SHA-256 artifact identities, duplicates,
coverage problems and explicit `safe_to_resume_paid_calls: false`. It reads local
files only and imports no provider client. Explicit trace selection is intentional:
blindly summing every trace would count guarded calls and offline replays again.
This inventory does not claim to discover unsaved calls or unrelated account use.

Seventeen new offline tests pass: decimal validation, overlapping roots, copied
responses, conflicting response identities, interrupted calls without markers,
malformed/missing records, trace overlap, unknown markers and above-reservation
costs. Ruff passes. Evidence: `runs/launch-readiness/2026-10-03-spend-audit-final.xml`
and `.log`. No product-runtime changes, provider requests, deployment, or repeat of
unchanged backend/browser suites were needed.

## Next action

Continue local reliability and recovery work. Paid experiments require resolution
or explicit disposition of unknown charges, a complete aggregate inventory and
applicable bounded authorization. Neither this arithmetic nor additional account
credits grants that authorization. Reservations are estimates; account-level billing
and caps remain unverified. Do not claim a fresh live-model or real-user result from
this accounting work.
