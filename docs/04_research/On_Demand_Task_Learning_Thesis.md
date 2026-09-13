# On-Demand Task Learning Thesis

## Product Claim

PolyaBrain should not compete by pretraining a larger general-purpose model.
It should compete as a model-independent cognitive runtime that constructs the
smallest useful task model, detects what prevents verification, acquires only
that missing knowledge, applies deterministic procedures when available, and
consolidates only verified reusable behavior.

This is a product hypothesis to test, not a claim that retrieval removes the
need for learned priors. A language model remains useful for semantic
interpretation, hypothesis formation, synthesis, and difficult judgment. The
runtime owns state, action choice, evidence admission, budgets, verification,
and learning.

## Mechanism

```text
raw problem
  -> temporary task model
  -> current impasse
  -> candidate cognitive actions
  -> expected verified progress / marginal cost
  -> capability observation
  -> evidence gate and task-model update
  -> execute/check
  -> verify or recover
  -> consolidate verified fact, episode, or procedure
```

The temporary task model is derived from canonical state and audit events. It
does not become a second mutable truth store. An impasse is a specific obstacle
such as missing user intent, missing external fact, unavailable artifact,
unperformed calculation, untested hypothesis, failed execution, or incomplete
verification.

## Compute Doctrine

1. If a reliable procedure is known, run it deterministically.
2. If verified memory is relevant, retrieve it before new acquisition.
3. If a gap can be answered by an exact local tool, prefer it over a model.
4. Acquire external knowledge only for a current verification-blocking gap.
5. Use a semantic model when interpretation or synthesis cannot yet be
   represented as a reliable procedure.
6. Fuse compatible semantic responsibilities, but never fuse away independent
   verification.
7. Stop when the expected verified progress of remaining actions does not
   justify their cost or risk.

## What Existing Research Supports—and Does Not

Retrieval-augmented generation, RETRO, and Atlas show that external knowledge
can reduce dependence on parameters or improve knowledge-intensive performance.
MRKL, Toolformer, ReAct, and PAL show the value of tool-mediated and
neuro-symbolic computation. Soar provides a useful product analogy for explicit
working state, operator selection, impasses, and procedural chunking.
DreamCoder, Voyager, and ExpeL support the idea that reusable non-parametric
procedures or experience can improve later tasks.

None of these results proves that a small runtime plus browsing is general
intelligence. Retrieval can return irrelevant or false material; a controller
can spend more calls than a direct answer; learned procedures can transfer
incorrectly; and verification can be performed by the same fallible model. The
benchmark therefore has to measure the quality-cost frontier on unfamiliar and
held-out tasks, not merely demonstrate an agent loop.

## Falsifiable Win Condition

PolyaBrain wins its first scientific claim only if, on repeated held-out
micro-world and real investigation cases, it produces more verified useful
outcomes per unit cost than direct, full-context, and ordinary retrieval
baselines using fair models and tools. It must also show that verified transfer
reduces work on the second task without increasing unsupported conclusions.

Until those results exist, the honest product label is “on-demand cognitive
runtime under evaluation,” not “general intelligence achieved.”

## Primary References

- Lewis et al., [Retrieval-Augmented Generation](https://proceedings.neurips.cc/paper/2020/hash/6b493230-Abstract.html).
- Borgeaud et al., [Improving language models by retrieving from trillions of tokens](https://arxiv.org/abs/2112.04426).
- Izacard et al., [Atlas: Few-shot Learning with Retrieval Augmented Language Models](https://arxiv.org/abs/2208.03299).
- Karpas et al., [MRKL Systems](https://arxiv.org/abs/2205.00445).
- Yao et al., [ReAct](https://openreview.net/forum?id=WE_vluYUL-X).
- Schick et al., [Toolformer](https://proceedings.neurips.cc/paper_files/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html).
- Gao et al., [PAL: Program-aided Language Models](https://arxiv.org/abs/2211.10435).
- Laird, [The Soar Architecture](https://soar.eecs.umich.edu/soar_manual/02_TheSoarArchitecture/).
- Ellis et al., [DreamCoder](https://people.csail.mit.edu/asolar/papers/EllisWNSMHCST21.pdf).
- Wang et al., [Voyager](https://arxiv.org/abs/2305.16291).
- Zhao et al., [ExpeL](https://arxiv.org/abs/2308.10144).
