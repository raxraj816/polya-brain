# Independent trial and pilot protocol

Status: prepared; no invitations sent, participants enrolled or judgments collected.

## Independent task intake

Recruit two technical reviewers who did not build or tune the evaluated changes.
Ask each to disclose relevant conflicts and prior familiarity. Use a pseudonymous
ID. Ask for a fresh problem, visible inputs, permission to use those inputs, and
acceptance criteria. Keep their reference answer and checks separate from solver
input. The source-packet runner accepts the `Case` structure in `investigation.py`;
it excludes `rubric` from model requests. Its current lane supplies complete source
snapshots to both arms and has no external tools. It must not be used to claim a
comparison of autonomous acquisition or arbitrary debugging workflows.

For a full investigation pilot, record the user's normal tools and permitted tool
access before choosing a baseline. If tool access cannot be matched, report that
limitation and do not treat the result as a fair comparison. Freeze tasks, rubrics,
runtime hashes, model, limits, prices and exclusions before execution. Do not tune
on the tasks and then reuse them as held out. Public availability does not prove a
task was absent from model training.

## Review

Give each reviewer the packet and rubric; withhold the private condition key and
cost results until initial ratings are locked. Style can reveal the method, so
describe this as condition labels withheld rather than guaranteed blinding.
Record correctness, source support, unsupported claims, missing required outcomes,
repair effort and elapsed review time. An honest refusal can be correct but still
unhelpful; score safety and usefulness separately. Treat absent output as missing
delivery, not a tie. Preserve disagreements and record adjudication separately.

## Pilot session

Select three consenting target users with real tasks; the small sample is formative
evidence only. Run locally in an explicitly authorized environment. Do not deploy
the prototype or share credentials to facilitate the pilot. Explain evidence,
uncertainty and controls, then observe without solving the problem for the user.
Record their success criterion and usual workflow before beginning. Keep unsuccessful
sessions, interruptions and dropouts. Ask what they would use next time and why.

Record consent, a pseudonymous participant ID, task ID, start/end times, outcome,
evidence inspected, unsupported claims, repairs, assistance and preferred workflow.
Leave unobserved fields null. Store any participant material outside tracked source
control and only with permission; link authorized evidence records rather than
copying private information into reports.

Agree on an observation window for optional continued local access. Record a second
use only if it actually occurs, on a different task. Mark who initiated it and what
assistance was provided. Requested, coached or scheduled repetition is not voluntary
return. Non-return and withdrawal remain in the record. Do not manufacture usage,
identities, consent, ratings or retention percentages from empty templates.

## Decisions

Developer checks, independent task outcomes, reviewer ratings and user return are
four separate evidence classes. Examine every failure before aggregate scores.
Use total human effort and verified useful outcomes alongside cost/time. Keep the
public-launch decision separate from pilot findings; hosted security and operations
remain required. No deadline or favorable small sample waives these gates.
