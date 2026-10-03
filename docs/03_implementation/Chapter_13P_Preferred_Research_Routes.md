# Chapter 13-P: preferred research route admission

Implementation date: 2026-10-02. Controller `cognitive-controller-v0.5.12`.

## Defect and repair

The scope reviewer and public page reader were selected early using their static
capability definitions. A registered capability can reserve different resources
for a particular invocation. The old early selection could therefore choose an
over-budget route or skip an affordable route. It also bypassed ordinary support,
prior-failure and sensitive-data checks for these preferred routes. When source
evaluation was pending but unavailable, a fallback could purchase more search
instead of stopping with the unresolved evidence.

Preferred candidates now pass the same admission conditions as other candidates,
including the actual invocation reservation. A rejected preferred candidate stays
in the candidate set so the decision trace records why it was refused. A safe
ordinary route may continue. A pending evaluation has priority even when its
candidate is ineligible; if it cannot run, the kernel stops with insufficient
evidence and retains the source data.

## Verification and limit

Five before-fix failures and one passing check are retained in
`runs/launch-readiness/2026-10-02-preferred-before.xml/.log`. The focused
after-fix group passes 89 checks, zero skips, in the corresponding `-after`
artifacts. Cases vary static and invocation reservations in both directions for
each preferred route, and verify that missing or budget-denied evaluation cannot
cause a new search. All providers and capabilities in these checks are local
fixtures; this does not measure source-selection quality or solve the saved DART
task. The source-packet development comparison is a separate post-acquisition
lane, not verification of live research routing.

No frontend or database behavior changed in this repair. Deployment and hosted
recovery are outside this chapter. Work remains uncommitted on
`feature/launch-readiness`.
