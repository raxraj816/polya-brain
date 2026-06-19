# Direct LLM Baseline

For this problem, a reasonable first answer is to investigate the most obvious likely cause and apply the common fix: Our API p95 latency jumped after deploy. Should we add Redis or inspect the query path first?

Recommended next step: inspect the relevant logs or metrics, try the likely fix in a safe environment, and measure whether the issue improves.
