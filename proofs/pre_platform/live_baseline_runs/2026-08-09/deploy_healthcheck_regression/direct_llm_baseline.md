**Isolate the deploy change first.** Increasing the timeout treats the symptom and risks routing traffic to unhealthy pods.

**Why not increase the timeout:**
- Readiness probes exist to keep traffic off pods that aren't ready to serve requests. A 40% failure rate isn't "slow startup"—it's a systemic issue.
- Longer timeouts mask the real problem (startup crashes, config errors, DB connection exhaustion, resource limits, downstream dependency failures) and make debugging harder.
- Unhealthy pods receiving traffic can cascade failures to dependencies.

**Do this instead (5–15 min investigation):**
1. **Check pod events/logs** for the failing pods:
   ```bash
   kubectl describe pod <failing-pod> -n <ns>
   kubectl logs <failing-pod> -n <ns> --previous  # if restarting
   ```
2. **Compare spec differences** between healthy and failing pods (image, env, resource requests/limits, init containers).
3. **Look at what changed in the deploy**: code, configmaps, secrets, migrations, feature flags, downstream service versions.
4. **Check node/az distribution**—are failures concentrated? (points to node pressure, zone-specific DNS, etc.)
5. **If unclear, roll back** the deploy while you investigate. A rollback is faster and safer than flying blind with a longer timeout.

**Only consider a timeout bump** if you prove the new code *genuinely* needs more time (e.g., a new warm-up step) and you've verified the pods *do* become healthy—then update the probe with evidence, not hope.
