# Chapter 13-P: learn, act, verify, reuse

This development experiment tests whether a successful source edit can become a
small reusable candidate that saves later model work without carrying forward a
past verdict. It does not test general algorithm learning or human equivalence.

`cases.json` was frozen before the first live attempt. Two invented protocol
families supply their rules, source and checks. Each has an initial repair, a
related task with a changed function/context and check, and an incompatible rule.
The related task retains the exact faulty edit fragment. Every condition uses the
production Cognitive Runtime, baseline/candidate Docker execution, and independent
deterministic verification. The cold comparator has the same inputs and execution
capabilities, with no candidate lessons. Checks are visible to both conditions.

Run with existing provider configuration and the configured pinned Docker image:

```sh
PYTHONPATH=backend .venv/bin/python -m evals.chapter_13p.repair_transfer.run --output runs/repair-transfer/new-run
```

The harness disables search, limits model requests to six, exports private run
artifacts, and serializes/deserializes only successfully learned lessons. If
learning fails it now skips the warm conditions explicitly. The API integration
test separately exercises durable, owner-scoped database storage and retrieval.

## Observed results

The second complete experiment, after numeric-literal relevance checking was
added, recorded:

| Family | Condition | Outcome | Model calls | Recorded tokens | Elapsed |
| --- | --- | --- | ---: | ---: | ---: |
| ORBIT-R17 | Learn | Completed | 1 | 1,484 | 6.346 s |
| ORBIT-R17 | Related cold | Completed | 1 | 1,519 | 6.405 s |
| ORBIT-R17 | Related warm | Completed | 0 | 0 | 0.371 s |
| ORBIT-R18 | Incompatible warm | Needs input; edit rejected | 2 | 8,094 | 14.791 s |
| MERIDIAN-C | Learn | Completed | 1 | 1,443 | 5.145 s |
| MERIDIAN-C | Related cold | Needs input; lexical false rejection | 2 | 5,140 | 11.876 s |
| MERIDIAN-C | Related warm | Completed | 0 | 0 | 0.394 s |
| MERIDIAN-D | Incompatible warm | Needs input; edit rejected | 1 | 3,220 | 3.792 s |

Both warm successes executed their new checks, observed a failing original and a
passing candidate, and used zero model requests. Serialized lessons were 464 and
474 bytes; these sizes exclude database, trace, sandbox and model storage. The
ORBIT learning-plus-transfer pair used 1,484 recorded tokens with memory versus
3,003 with cold transfer. This is one narrow successful comparison, excluding
development costs, not a statistical or whole-product cost claim.

A separate live API/workbench pair persisted a learned ORBIT edit (one request,
1,440 tokens, 5.297 seconds) and reused it on changed code (zero requests/tokens,
0.592 seconds). The browser displayed the completed report, memory proposal,
fresh checks and candidate diff. Host source files were unchanged.

## Failures and qualifications

`results.json` includes both complete experiments and the aborted first attempt.
The first attempt lost its runtime result when export found no artifact directory;
its provider usage is unknown beyond one known request. The first complete run
had timeouts and false lexical rejections. MERIDIAN failed learning, so its later
conditions were actually runs without memory despite their original warm labels.
Those records remain qualified, not counted as reuse.

In the second experiment the cold MERIDIAN proposal passed the supplied check but
was rejected because its diagnosis ended in `239.`. The lexical predicate treated
the terminal period as part of a decimal. A general boundary repair now accepts
that preserved proposal, with tests distinguishing other decimal values and
digits embedded in names. Only the predicate was replayed; the recorded failed
live run remains failed. Lexical relevance is never proof of causality.

Failed provider responses can leave usage incomplete. Normalized cost is an
internal scheduling weight, not money. Negative transfers were safely rejected,
but recovery still consumed model calls and did not produce a corrected outcome.
These are author-created synthetic cases; no independently held-out performance,
real-user preference, general procedure induction, broad semantic transfer, or
overall competitive advantage has been established.

Next evidence needed: unseen task families, semantic changes that cannot reuse
the same text, economical recovery after rejected transfer, and repeat-use value
against a strong direct-model workflow. Online acquisition reliability and exact
citation fidelity remain separate open gates recorded in Chapter 13-P.
