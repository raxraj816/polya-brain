# Software Debugging

## Reproduce the failure

Turn a bug report into expected behavior, observed behavior, and a minimal reproducible case. Preserve the failing input and environment before changing code. If the failure cannot be reproduced, gather the missing version, configuration, timing, and state information rather than guessing a cause.

## Localize the change

Compare the last known good state with the first known bad state. Inspect deploy differences, dependency versions, configuration, and data migrations, then bisect one variable at a time. Temporal proximity suggests a candidate cause but does not prove its mechanism.

## Use observability as evidence

Logs show discrete events, metrics show aggregate behavior, and traces show request paths; use the signal that can distinguish competing hypotheses. Measure a baseline and the failing interval with the same definition. Preserve query text, stack traces, timestamps, and source metadata needed to audit the diagnosis.

## Verify the fix

A fix is incomplete until the original reproduction passes, relevant regression tests pass, and important boundaries are checked. Look for evidence against the proposed mechanism. When a change merely hides the symptom, keep the root-cause question open and state the remaining risk.
