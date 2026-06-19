# Direct LLM Baseline

For this problem, a reasonable first answer is to investigate the most obvious likely cause and apply the common fix: Our background worker RSS grows from 600MB to 3GB over six hours and then gets OOM-killed. The quick fix suggested is doubling pod memory. Should we scale memory now or find the root cause first?

Recommended next step: inspect the relevant logs or metrics, try the likely fix in a safe environment, and measure whether the issue improves.
