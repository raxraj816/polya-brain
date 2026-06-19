# Direct LLM Baseline

For this problem, a reasonable first answer is to investigate the most obvious likely cause and apply the common fix: Our account dashboard endpoint has p95 latency around 2.4s. A teammate wants to add Redis caching this sprint. Should we do that first, or investigate/fix something else?

Recommended next step: inspect the relevant logs or metrics, try the likely fix in a safe environment, and measure whether the issue improves.
