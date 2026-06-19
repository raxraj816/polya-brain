# PolyaBrain Investigation Report: Investigate duplicate billing webhooks before blaming provider retries

## Final conclusion
The leading path is: The issue may be an idempotency or retry-handling gap rather than a provider failure. Do not treat this as final until the verification checks below are run.

## Confidence level
Moderate (0.62). The recommendation is directionally useful, but the evidence is still incomplete until checks are run.

## Evidence used
- `ev_user_problem` (user_input:cli:problem): The user reports this technical problem: Some customers were charged twice after billing webhooks retried during a provider incident. The first proposal is to disable retries. Should we disable provider retries or verify idempotency handling first?
- `ev_missing_measurements` (analysis:polya:gap-detection): The prompt does not include enough direct measurements to safely choose a permanent fix.

## Evidence against
- `ev_change_risk` (constraint:polya:mvp-safety-rule): The system should avoid changing provider settings before checking idempotency until the failure mode is verified.
- A different failure mode may explain the symptom once direct measurements are collected.

## Checks performed
- Final report includes all required audit sections.
- Every evidence item includes source_type, source_uri, claim, reliability_score, and relevance_score.
- Hypotheses do not use novelty_score as a core MVP field.
- Evidence against or uncertainty is explicitly listed before recommendation.
- Permanent architecture or production changes are not recommended before verification.

## Open questions
- Were duplicate events processed with the same provider event id?
- Does the handler persist idempotency before or after creating the charge?
- Can replaying the same event twice create more than one internal charge?

## Recommended next action
Audit webhook event ids against charge creation ids, add an idempotency assertion in a replay test, and only change retry settings after proving duplicate handling is safe.

## Audit trace
- `explore` / `problem_representation`: Parsed the input into a technical_investigation run.
- `reframe` / `problem_representation`: Separated the reported symptom from the safest verified next action.
- `compare` / `evidence_evaluation`: Compared supplied evidence, missing measurements, constraints, and analogical patterns.
- `compare` / `hypothesis_reasoning`: Generated 3 candidate explanations and selected h_idempotency_gap as the best-supported next path.
- `verify` / `verification`: Created a technical investigation checklist with contradiction and irreversible-change checks.
- `reflect` / `reflection_memory`: Recorded that the next product step should convert uncertainty into measured evidence.

## Hypotheses considered
- `h_idempotency_gap` [selected] confidence=0.62: The issue may be an idempotency or retry-handling gap rather than a provider failure.
- `h_apply_obvious_fix` [deferred] confidence=0.31: Apply the first obvious fix suggested by the symptom.
- `h_external_or_random_noise` [rejected] confidence=0.18: The problem is caused by an external dependency or random transient noise.
