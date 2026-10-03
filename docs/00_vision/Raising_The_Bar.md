# Raising the bar: what the evidence says PolyaBrain must become

> **Superseded for identity and direction** by
> [PolyaBrain Founding Thesis](PolyaBrain_Founding_Thesis.md) (2026-10-03). PolyaBrain is
> an intelligence system that learns from experience, outside the model; verification
> is one organ of it, not the product's identity. The evidence and verification
> lessons below remain valid inside that thesis.

Prepared 2026-10-03 after Chapters 171–173. Status: Chapter 174 approved and built
(`docs/03_implementation/Chapter_174_Verified_Claims.md`); its frozen live evaluation
awaits provider credits and a budget. Binding product decisions live in the master plan.

## The one-sentence product

**PolyaBrain turns difficult objectives into outcomes it can prove.** Other systems
generate answers; PolyaBrain re-derives them independently, runs them, compares,
tests itself against controls, and says exactly what is proven, what is wrong and
what remains unknown.

## What the evidence now shows

1. **Generation is a commodity; proof is not.** A one-call lean model was correct on
   30/30 clearly specified held-out coding attempts and beat the four-call kernel on
   cost (Chapters 171–172). PolyaBrain cannot win by thinking longer than frontier
   models. It wins by knowing when an answer is right.
2. **Independent re-derivation works.** On 38 real QuixBugs defects presented as
   "no behavior change" refactors, verify-change flagged 38/38 with concrete inputs
   and raised 0/37 false alarms on behavior-identical controls, for about 0.008 USD
   per program (Chapter 173). That is a real capability, not a demo.
3. **The verifier must be verified.** Controls and adversarial probes exposed three
   harness comparison defects (7 false alarms in QuixBugs v1), 19 silent false-pass
   paths (bool/int equality, sets, iterator prefixes, dropped checks), coverage gaps,
   and a withheld-check namespace bug that fabricated failures. Each was invisible
   until a control or probe forced it out. Trust is earned by self-audit.
4. **Cheap first, prove after.** Lean-first solving with verification and bounded
   repair cost about 40% less than one kernel attempt and never certified wrong code.
   Heavy orchestration before evidence of need is the wrong default.
5. **The flagship's verification is still mostly a model reviewing a model.** In
   investigations, the terminal check is `conclusion_checker`, a model pass, plus
   citation provenance. In the source-packet comparison PolyaBrain stopped with
   "insufficient evidence" on 3 of 4 tasks in the first batch where a lean model
   answered. By the playbook's own kill gate ("verification is mostly decorative"),
   the Investigator wedge needs executable verification.
6. **PolyaBrain does not yet learn from verification.** Episodes and strategies are
   stored only in API sessions; the CLI learns nothing; verify-change and verified
   coding never read lessons back; capability performance is lost on restart. The
   playbook's moat ("memory makes repeated cases better") is unproven.
7. **No real user has used it.** The pilot kit is unsent. The overhead test, the
   only test that decides whether this is a product, has never been run.
8. **Provider reliability is a product issue.** Repeated `LLMClientError` failures
   stopped evaluation batches. The product's safe stop worked; users still need a
   fallback route rather than a stopped run.

## The bar, stated as product requirements

1. **Every claim carries a proof status.** Proven by independent execution, supported
   by quoted source, contradicted, or unverified. No unlabeled claim reaches a user.
2. **Proof means independent derivation plus a deterministic comparison.** A model
   agreeing with itself is never proof.
3. **The verifier publishes its own calibration.** Each domain shows measured catch
   and false-alarm rates on frozen controls; certificates cite them.
4. **Cheap first.** Answer lean, verify, escalate only on disagreement or missing
   evidence. Report cost per verified outcome.
5. **Every confirmed failure becomes reusable knowledge.** Failure patterns (what went
   wrong, which input exposed it, which check confirmed it) are stored, retrieved and
   measured for whether they make the next verification better or cheaper.
6. **One proof, many domains.** The same propose → derive independently → compare →
   control → adjudicate → certify loop must win in code, data, investigations and
   research claims. Generality is shown by these wins, not asserted.
7. **The second visit.** A real technical user brings a second hard problem by choice.

## Recommended next build: Chapter 174, verified claims in investigations

**What:** For an investigation over the user's own data (CSV/JSON tables, logs) and
supplied sources, answer lean, extract each quantitative and factual claim, and prove
or refute it:

- Quantitative claims about supplied data: two independent executable derivations
  (the answer's own analysis, and an oracle written without seeing it, cross-checked
  against the existing deterministic `TableMeasurementTool` where it applies),
  compared deterministically, with controls such as perturbed data on which the claim
  must change and identity transforms on which it must not.
- Source claims: verbatim quote support (existing citation provenance).
- Everything else: labeled unverified, never silently passed.
- Disagreements go through the existing quoted-requirement adjudication; the report
  shows claim-by-claim proof status and the concrete evidence.

**Why this first:**

- It moves the proven verification core into the flagship Investigator wedge and
  fixes the decorative-verification gap where the product most needs it.
- Wrong numbers in confident AI analyses are a daily pain for founders and engineers,
  and numbers are cheap to recompute exactly.
- It is the second domain for the same loop, the first real evidence of generality.
- It reuses existing parts: sandbox, differential harness, adjudication, table
  measurement, citation provenance, certificate projection and the workbench card.

**How it is judged (frozen before any run):** questions with known answers over
public datasets (a public data-analysis benchmark, subject to download approval)
plus behavior-preserving controls. Report lean vs lean+verification: wrong answers
caught, correct answers harmed, false alarms, unverified rate, cost and time.

**Built alongside, small:** a persistent failure-pattern store (Postgres with a local
file fallback so the CLI learns too) fed by every confirmed defect and retrieved into
input generation, with a with/without-memory comparison on a frozen set.

**Later, only when data earns it:** a small model distilled from verified traces for
one narrow job (input generation, defect classification or routing), kept only if a
frozen comparison shows it is better or cheaper than routed models.

## What only the founder can do

- Recruit 3–5 technical users for the pilot kit in `evals/launch_readiness/pilot/` and
  run real problems through verify-change and verified investigations.
- Approve data sources and model budget for each frozen evaluation.
- Decide what "winning" is measured by each quarter: verified outcomes, second-visit
  rate and cost per verified outcome.

## What must not change

Honest denominators, preserved failures, frozen held-out sets, controls on every
evaluation, and "insufficient evidence" when proof fails. Raising the bar means
raising what is proven, never lowering what counts as proof.
