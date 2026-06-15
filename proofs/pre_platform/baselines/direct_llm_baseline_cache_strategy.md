# Direct LLM Baseline: Cache Strategy Investigation

The likely best move is to add Redis caching for the slow endpoint because caches
often reduce latency and take pressure off the database. Start with a simple
read-through cache and set a short TTL so stale data risk is low.

If the endpoint is still slow after adding Redis, inspect the database queries and
indexes. You may also want to profile the request path and check whether external
API calls are part of the latency.

Recommended next step: prototype Redis caching for the endpoint and measure p95
latency before and after.
