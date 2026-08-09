# PolyaBrain Investigation Report: Investigate search ranking drop before changing relevance logic

## Final conclusion
The leading path is: The issue may be an indexing or pipeline regression rather than a ranking-model problem. Do not treat this as final until the verification checks below are run.

## Confidence level
Moderate (0.62). The recommendation is directionally useful, but the evidence is still incomplete until checks are run.

## Evidence used
- `ev_user_problem` (user_input:cli:problem): The user reports this technical problem: Product search conversion dropped after yesterday's catalog sync. The team wants to tune ranking weights immediately. Should we change ranking logic or inspect indexing and sync quality first?
- `ev_missing_measurements` (analysis:polya:gap-detection): The prompt does not include enough direct measurements to safely choose a permanent fix.

## Evidence against
- `ev_change_risk` (constraint:polya:mvp-safety-rule): The system should avoid changing ranking logic before checking index freshness until the failure mode is verified.
- A different failure mode may explain the symptom once direct measurements are collected.

## Checks performed
- Final report includes all required audit sections.
- Every evidence item includes source_type, source_uri, claim, reliability_score, and relevance_score.
- Hypotheses do not use novelty_score as a core MVP field.
- Evidence against or uncertainty is explicitly listed before recommendation.
- Permanent architecture or production changes are not recommended before verification.

## Open questions
- Did catalog sync change field completeness, availability, or boosts?
- Are top queries missing expected products or just ordered differently?
- Does a replay against the previous index restore conversion-sensitive result sets?

## Recommended next action
Check index freshness, missing fields, and top-query result diffs before changing ranking weights; only tune relevance after confirming the index pipeline is healthy.

## Audit trace
- `explore` / `problem_representation`: Parsed the input into a technical_investigation run.
- `reframe` / `problem_representation`: Separated the reported symptom from the safest verified next action.
- `compare` / `evidence_evaluation`: Compared supplied evidence, missing measurements, constraints, and analogical patterns.
- `compare` / `hypothesis_reasoning`: Generated 3 candidate explanations and selected h_index_or_pipeline_regression as the best-supported next path.
- `verify` / `verification`: Created a technical investigation checklist with contradiction and irreversible-change checks.
- `reflect` / `reflection_memory`: Recorded that the next product step should convert uncertainty into measured evidence.

## Hypotheses considered
- `h_index_or_pipeline_regression` [selected] confidence=0.62: The issue may be an indexing or pipeline regression rather than a ranking-model problem.
- `h_apply_obvious_fix` [deferred] confidence=0.31: Apply the first obvious fix suggested by the symptom.
- `h_external_or_random_noise` [rejected] confidence=0.18: The problem is caused by an external dependency or random transient noise.
