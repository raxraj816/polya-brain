**Diagnosis:** The free Nemotron model explicitly logs session data for training/improvement (per OpenRouter's own model page), which conflicts with `OPENROUTER_DATA_COLLECTION=deny`. OpenRouter correctly returns 404 because no provider endpoint for that model satisfies the privacy policy.

**Recommendation:** **Do not weaken privacy globally.** The `deny` policy is a correct fail-closed default.

**Action:**
1. **Production:** Switch to a paid model that offers a Zero Data Retention (ZDR) endpoint and set `OPENROUTER_ZDR=true`. Only ZDR endpoints honor `data_collection=deny`.
2. **Evaluation-only path:** Create a separate config (e.g., `.env.eval`) that sets `OPENROUTER_DATA_COLLECTION=allow` and `OPENROUTER_ZDR=false` for the free model. Document this as **non-confidential evaluation only**.
3. **CI/Tests:** Use the eval config for automated probes; keep the main `.env` (or production secrets) on the strict ZDR-backed model.

This preserves the safe default while giving you a reproducible, explicitly-labeled evaluation route.
