# PolyaBrain Investigation Report: Investigate worker memory growth before scaling

## Final conclusion
The leading path is: The issue may be resource growth under load, so memory and queue behavior should be measured before scaling. Do not treat this as final until the verification checks below are run.

## Confidence level
Moderate (0.62). The recommendation is directionally useful, but the evidence is still incomplete until checks are run.

## Evidence used
- `ev_user_problem` (user_input:cli:problem): The user reports this technical problem: Our background worker RSS grows from 600MB to 3GB over six hours and then gets OOM-killed. The quick fix suggested is doubling pod memory. Should we scale memory now or find the root cause first?
- `ev_missing_measurements` (analysis:polya:gap-detection): The prompt does not include enough direct measurements to safely choose a permanent fix.

## Evidence against
- `ev_change_risk` (constraint:polya:mvp-safety-rule): The system should avoid scaling capacity before isolating the growth source until the failure mode is verified.
- A different failure mode may explain the symptom once direct measurements are collected.

## Checks performed
- Final report includes all required audit sections.
- Every evidence item includes source_type, source_uri, claim, reliability_score, and relevance_score.
- Hypotheses do not use novelty_score as a core MVP field.
- Evidence against or uncertainty is explicitly listed before recommendation.
- Permanent architecture or production changes are not recommended before verification.

## Open questions
- Does memory grow with processed job count, queue depth, payload size, or wall-clock time?
- Is the growth in heap, native memory, buffers, or child processes?
- Does memory return after GC or worker restart on a fixed-size batch?

## Recommended next action
Run a bounded reproduction with heap/RSS sampling and queue-depth correlation, then compare memory growth on a fixed input batch against live traffic growth.

## Audit trace
- `explore` / `problem_representation`: Parsed the input into a technical_investigation run.
- `reframe` / `problem_representation`: Separated the reported symptom from the safest verified next action.
- `compare` / `evidence_evaluation`: Compared supplied evidence, missing measurements, constraints, and analogical patterns.
- `compare` / `hypothesis_reasoning`: Generated 3 candidate explanations and selected h_resource_growth as the best-supported next path.
- `verify` / `verification`: Created a technical investigation checklist with contradiction and irreversible-change checks.
- `reflect` / `reflection_memory`: Recorded that the next product step should convert uncertainty into measured evidence.

## Hypotheses considered
- `h_resource_growth` [selected] confidence=0.62: The issue may be resource growth under load, so memory and queue behavior should be measured before scaling.
- `h_apply_obvious_fix` [deferred] confidence=0.31: Apply the first obvious fix suggested by the symptom.
- `h_external_or_random_noise` [rejected] confidence=0.18: The problem is caused by an external dependency or random transient noise.
