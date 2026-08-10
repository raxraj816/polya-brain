# Chapter 15 Clarifying Question Flow

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Product Behavior

When representation cannot identify a required target, success condition, or
user-owned preference, PolyaBrain does not manufacture an answer. The cognitive
kernel returns `needs_input`; the session becomes `awaiting_user_input`; the
questions and expiry are durable; and the question appears in the audit trace
and server-sent event stream.

The user answers through:

```text
POST /api/v1/sessions/{session_id}/respond
```

The same session is claimed atomically, the answer is recorded, the existing
trace remains intact, and problem representation runs again using the original
request plus the clarification. A validated representation is canonicalized.
If the answer remains underspecified, the session can pause with a more focused
question. Duplicate and expired responses are rejected.

## Durable Data

Migration `20260809_0004` adds `clarification_requests` with:

- session id;
- ordered questions;
- status;
- requested and expiry timestamps;
- answer and answered timestamp.

The session status is `awaiting_user_input` while paused. Expired unanswered
requests stop safely with `clarification_expired` verification status.

## Trace And Streaming

The persisted trace contains:

- the controller's `interpret` decision;
- the representation engine's framing and `needs_input` result;
- `clarification_requested` with the questions;
- `clarification_answered` with the sanitized answer;
- the resumed representation and later controller decision.

`GET /api/v1/sessions/{session_id}/events/stream` tails persisted events as SSE
until the run pauses, stops, or reaches the bounded stream timeout.

## Safety Boundaries

- Ambiguous output is never stored as a canonical structured problem.
- Only a validated clarified representation is canonicalized.
- Blank, duplicate, missing-session, non-waiting, and expired responses fail
  explicitly.
- The answer is sanitized before trace persistence.
- Run and response claims use database locking and durable status transitions.
- Missing downstream capabilities produce an unverified safe stop, not a fake
  solution.

## Verification

- Unit/API coverage exercises response success, blank input, missing session,
  wrong-state conflict, question export, SSE pause delivery, deterministic
  clarified representation, insufficient clarification, and truthful stop.
- Real Postgres coverage exercises pause persistence, trace continuity,
  response, canonicalized clarified representation, duplicate response,
  timeout, and migration compatibility.
- Docker API smoke verified create -> run -> awaiting input -> respond ->
  re-understand -> truthful insufficient-evidence stop with 21 ordered events.

## Known Boundary

Chapter 15 makes clarification real, but it does not make the entire product
complete. After clarified representation, the persisted runtime currently has
no production constraint, acquisition, hypothesis, execution, or verification
capabilities. The controller therefore stops truthfully until those chapters are
implemented.
