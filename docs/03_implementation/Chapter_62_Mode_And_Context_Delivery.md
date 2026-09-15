# Chapter 62: Mode and context delivery

The local workbench now exposes the existing Investigate, Compare, and Review
modes, plus optional time-window, metric/success-criterion, and affected-entity
inputs. Explicit context is appended as user-provided text in the saved problem;
no inferred fact or new core contract field is introduced.

The API previously persisted the mode but omitted it when constructing problem
representation. It now passes the saved mode and optional domain through the
shared composer to the representation engine. Existing parser validation requires
the provider to preserve the supplied override, and the selected approach remains
visible in trace metadata. CLI callers without a hint retain mode inference.
The source/check workflow remains explicitly Investigate.

Downstream bounded model requests receive the validated selected mode and a mode
verification checklist, including when a capability uses a reduced state
projection. Compare requests identify alternatives and common criteria, Review
requests examine claims/acceptance criteria and counterexamples, and Investigate
requests distinguish symptoms from causes and seek discriminating evidence.
Missing requirements must remain unresolved or cause clarification; these
checklists cannot fabricate facts, bypass deterministic checks, or promote an
unsupported conclusion. This is prompt/trace policy, not a new ranking score.

The shared capability prompt is `cognitive_capability@0.2.0`. Model-capability
versions now include the prompt-policy fingerprint, and representation versions
include mode/domain hints, so persisted procedures and adaptive profiles cannot
silently reuse identities from different configurations.

Verification covers all existing modes through the shared composer, explicit
mode/domain preservation through the actual API, downstream checklist propagation
with reduced projections, rejection of unrelated trace events as mode producers,
and browser mode/context request payloads. These tests prove the wiring and policy
boundary. Fresh substantive Compare/Review outcomes still require independent
evaluation; a selected mode or successful arithmetic run is not that evidence.

Validation: 468 backend tests passed with migrated Postgres, strict Python checks
passed, frontend type checking and production build passed, and six ordinary
browser tests passed. The opt-in live-source test was not rerun for this mode-only
change; its earlier result remains documented separately in Chapter 13-O.
