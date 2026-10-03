# Launch-preparation development evaluations

These are known development problems, not an independent benchmark. See
`docs/03_implementation/Chapter_171_Readiness_Evidence_Package.md` for the protocol,
results, limitations and human review instructions.

- `coding-regression-cases.json`: frozen six-case corpus used by the two full batches.
- `bounds-repair-cases.json`: integer-coverage-only follow-up after parameter repair.
- `assess.py`: offline saved-artifact consistency audit and randomized blinded packet.
- `admission_probe.py`: selected saved-candidate ablation in networkless Docker;
  never turns the original unsuccessful run into a delivered answer.
- `../chapter_13p/coding_execution/budgeted.py`: matched runner with shared serial
  model-call spend reservations. Raw responses and failures are retained.
- `investigation-cases.json` / `investigation.py`: four synthetic source-packet
  cases and a matched post-acquisition reasoning lane; see
  `docs/03_implementation/Chapter_171_Source_Packet_Comparison.md`.
- `pilot/`: unsent reviewer invitation, independent task intake and pilot session
  protocol/templates. Empty templates are not evidence of participants or return use.

Offline packet command (writes exclusively to a new directory):

```sh
PYTHONPATH=backend:. .venv/bin/python -m evals.launch_readiness.assess RUN_DIRECTORY NEW_PACKET_DIRECTORY
```

Give reviewers `review-packet.md` and `review-packet.json`, alongside the instructions. Keep
`private-condition-key.json` and `audit.json` private until ratings are locked.
No judgments or participants are fabricated. The packet includes every expected
attempt, including failures and missing outputs. Never replace a failed artifact
with a successful rerun. Use a new versioned run directory.

The authorized campaign ceiling is **US$5 total**, not per process or heartbeat.
Before further paid dispatch, reconcile completed batch spend and any unresolved
reservations. The local guard is a conservative estimate, not an account billing
limit. No automatic retry after an unknown-cost failure is allowed. Existing keys
stay in process memory; do not print `.env` or credentials. No new account or
credit purchase is authorized. A case should not be rerun simply to obtain a pass.

Current batch identities:

1. `2026-10-01-matched-v1`: original, 24 attempts, reported $0.65285175.
2. `2026-10-02-matched-v2`: 24 attempts completed, reported $0.66889875 from a $1 additional
   allowance, prompt/diagnostic repair at version 0.10.1.
3. `2026-10-02-bounds-v3`: four attempts completed, reported $0.10167225 from a $0.25 allowance,
   parser-boundary size repair at version 0.10.2. Targeted development follow-up;
   it cannot replace the full corpus results. It overlaps the tail of batch 2,
   so neither batch supplies isolated host-performance evidence.

4. `2026-10-02-source-packet-v1`: four paired developer source-packet attempts,
   15 returned calls, $0.07404150 reported. Polya delivered 1/4; lean 4/4.
   Delivery is not independent correctness.
5. `2026-10-02-source-packet-v2`: separate follow-up after bounded source context;
   two paired cases completed. Ten calls reported $0.05577900. The next call
   returned no response/cost, so $0.04337250 remains reserved and remaining cases
   were stopped. Do not rerun it as if the original batch had passed.

Read the updated reconciliation and readiness ledger before any new live run.
Campaign total is $1.55324325 provider-reported plus an unresolved $0.04337250
local reservation. The nominal remaining amount after reservation is $3.40338425,
but **paid dispatch is stopped pending reconciliation**. No invoice or account-cap
verification is claimed.

## Offline aggregate spending inventory

`python -m evals.launch_readiness.spend_audit` joins saved per-call ledgers across
explicit roots and separately selected unguarded traces. It makes no provider
requests and never authorizes spending. See
[Chapter 171 accounting](../../docs/03_implementation/Chapter_171_Campaign_Accounting.md)
for the reproducible command, current findings and unresolved billing gaps.
