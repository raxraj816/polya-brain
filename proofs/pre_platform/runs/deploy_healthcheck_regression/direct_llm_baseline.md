# Direct LLM Baseline

For this problem, a reasonable first answer is to investigate the most obvious likely cause and apply the common fix: After the latest API deploy, Kubernetes readiness checks fail for about 40% of pods. A teammate wants to roll forward with a larger timeout. Should we increase the timeout or isolate the deploy change first?

Recommended next step: inspect the relevant logs or metrics, try the likely fix in a safe environment, and measure whether the issue improves.
