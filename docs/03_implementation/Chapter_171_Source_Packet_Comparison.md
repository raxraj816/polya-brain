# Chapter 171: source-packet investigation comparison

Prepared 2026-10-02. Status: **incomplete development evidence; no superiority
claim**. This is one narrow post-acquisition reasoning lane, not the full
Investigator workflow or a real-user pilot.

## Protocol

Four developer-authored synthetic tasks and rubrics are frozen in
`evals/launch_readiness/investigation-cases.json`. The two arms receive the same
question and source snapshots, use `google/gemini-3.7-flash`, have no external
tools, and share six-call, 18,000-output-token, 180-second per-attempt ceilings.
The lean arm drafts and self-reviews in two calls. Polya runs its actual cognitive
runtime with the same snapshots seeded as evidence. The rubric is excluded from
solver requests. The runner saves full requests, responses, outcome artifacts,
source hashes and a condition-shuffled review packet. Condition style may still
be recognizable. Human semantic ratings are deliberately null.

The cases cover at-least-once delivery, version-specific defaults, conflicting
documentation and a malicious instruction embedded in a source. They probe
useful behavior and source discipline, but are neither independently sourced nor
held out. Their `.example` citations identify the supplied synthetic passages;
they are not live public documentation or source-acquisition evidence.

## Preserved first batch and repair

The first batch is retained in
`runs/launch-readiness/2026-10-02-source-packet-v1/`. It completed all eight
attempts and 15 provider calls, reported **$0.07404150**, and reconciled every
reservation with a reported response. Polya delivered one report; three runs
stopped with `insufficient_evidence` during initial framing despite supplied
snapshots. The lean arm delivered four answers. Delivery is not semantic
correctness, and those four answers have not received independent judgments.

The root cause of the three Polya stops was that initial framing received the
question but not the already-seeded evidence. The versioned representation
prompt now receives bounded snapshots as untrusted user-role data, with raw
excerpt/claim distinctions and truncation markers. It asks for a conditional
answer when the requested deliverable can be supported by the supplied text,
while preserving genuinely unknown deployment observations. This changes the
framing request, not the core evidence contract or admission of source truth.

Focused tests verify JSON placement, injection isolation from the system role,
truncation/omission bounds, no state mutation and repair retention. They do not
prove that every model will obey the instructions.

## Separate follow-up and stop

The after-change batch is retained in
`runs/launch-readiness/2026-10-02-source-packet-v2/`. On the two paired cases
completed before the stop, Polya delivered reports (including a conditional
version answer), and the lean arm also delivered answers. Two remaining cases
have no matched after-change result. On the eleventh provider call, the provider
client raised `LLMClientError` without a response or cost; the spend guard retained
the **$0.04337250** reservation and stopped the rest of the batch. Ten responses
report **$0.05577900**; the conservative batch charge is **$0.09915150**.
No further paid calls should be made until the unknown call is reconciled or a
new explicit bounded disposition is recorded. Do not infer that the unobserved
call was free, or score the unrun cases as results.

The two completed pairs are diagnostic development cases, not a fresh full-corpus
win. Polya's internal `passed` verification status means its own verifier accepted
the report; an independent reviewer has not validated citation support or
correctness. Latency, tokens and cost are in each attempt's `outcome.json` and
the spend ledger. The favorable version-case delivery is a bounded repair signal
only. Preserve the original failures when assessing progress.

## Independent evidence pending

The unsent invitation, intake and session templates in
`evals/launch_readiness/pilot/` prepare independent technical review and three
real-user pilot sessions. No reviewer or user was recruited or contacted, no
judgments exist, and voluntary second use has not occurred. The review packet
cannot be self-scored into independent evidence. For a broader investigation
comparison, match tool access to the user's normal workflow, freeze independent
tasks before any tuning, and record usefulness and human effort as well as
correctness, money and time. Production launch still requires its separate
security and operations gates.
