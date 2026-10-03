# PolyaBrain Founding Thesis

Agreed by the founder and the Co-Founder/CTO. The founder's vision was recorded and
reviewed point by point on 2026-10-02, and the identity was confirmed on 2026-10-03.
This document is binding through the master plan section "Founding thesis and
strategy".

PolyaBrain must win; there is no other option. Every decision is held to the bar of
Google, Nvidia, OpenAI, AWS and Microsoft. Every claim is labelled as one of three
kinds:

- **measured:** we have run it;
- **argued:** it is reasoning we believe;
- **to prove:** an open bet with a test that settles it.

## 1. Where the idea came from (the founder's vision)

India has no Nvidia, and most of the technology platforms its people use are
foreign-owned. Competing by training ever-larger language models means competing on
capital, compute and data with the richest companies on earth, and those models were
trained on the web anyway.

PolyaBrain started from George Pólya's *How to Solve It*. The idea is an intelligence
system, a brain, that does not need massive data, compute or model training. When it
is given a problem, including an unknown kind of problem, it does the following:

- works out what information is missing;
- learns it from the internet;
- understands it and combines it;
- solves the problem.

That is what a person does: they read and try until it becomes clear. For a coding
problem, someone has usually already solved something similar and written about it.

PolyaBrain was born from India's constraint and is built for the world.

## 2. What PolyaBrain is

> **PolyaBrain is an intelligence system that learns from experience, outside the model.**
> It gets smarter with every problem it solves, without training.

PolyaBrain is not:

- a chatbot;
- a wrapper around one model;
- a search engine;
- an auditing company.

Verification is one of its organs, Pólya's "look back", and it is what makes the
learning trustworthy. It is not the company.

"Intelligence OS" is the destination. It is claimed only when other applications and
developers depend on PolyaBrain in production.

## 3. What we kept, and what the evidence changed

Kept:

- **Knowledge does not have to live inside a model** (argued, with outside support).
  Looking things up can substitute for memorising. DeepMind's RETRO (2021) matched
  much larger models on language-modelling benchmarks by retrieving from a text
  database. That is support, not proof for our tasks.
- **Intelligence includes knowing what you don't know** (argued). A system that names
  its gap and fills it is a different kind of intelligence from one that answers from
  memory.
- **Don't fight the compute war** (founder decision).

Changed:

- **Retrieval alone cannot read** (measured). The web holds information, not
  understanding. Chapter 176 built a reader with no model, over Wikipedia and
  Wikidata, and ran it once on a frozen set of simple factual questions. 18 trusted
  answers were right and 6 were wrong (trusted precision 0.75). It also answered 1 of
  7 questions that have no answer.

  This shows that *our* deterministic reader is not good enough. It does not prove
  that no model-free reader could be. It is enough to decide not to bet the company
  on one.
- **Finding is not adapting** (argued). Finding a similar solution is the easy part.
  Adapting it to your code, versions and constraints needs language understanding.

The result: a small rented or open-weight model becomes **one part of the brain**, like
the regions that read and speak. It is not the brain, and PolyaBrain never depends on
any one model.

## 4. How the brain works

Pólya's method, made into a running system:

1. **Understand.** What is unknown, what is given, what are the conditions? Reframe
   the problem when the user may be asking the wrong question.
2. **Know what it doesn't know.** Name the exact missing pieces, for example "I don't
   know how this library handles time zones".
3. **Learn it.** Search the web, read documentation and code, and find related solved
   problems. Use whatever trusted tools exist.
4. **Test its understanding by experiment.** Write a small experiment, run it in a
   sandbox, and check whether the understanding was right. People learn by trying,
   not only by reading.
5. **Combine and solve.** Use deterministic procedures where possible and bounded
   model calls where needed.
6. **Look back.** Verify the result independently, or say "insufficient evidence".
7. **Remember.** Keep what was learned as PolyaBrain's own growing knowledge:
   - facts it checked, with their sources;
   - procedures that worked;
   - results of its experiments;
   - mistakes and how they were caught.

   This knowledge is inspectable, owned by PolyaBrain, and usable with any model.

**The objective** is to maximise verified correct outcomes per unit of money, time and
human attention, within the task's risk. The cheapest model is not the goal; it is used
when, with PolyaBrain around it, it delivers.

**Scope.** Learning is trustworthy where results can be checked: code, data,
calculations, and facts with sources. That is where we start. Where results cannot be
checked (strategy, taste, predictions), PolyaBrain shows its evidence and reasoning,
labels the result unverified, and never stores it as verified knowledge.

## 5. What is new

Today's AI works in two ways:

- **Frontier models.** Intelligence is frozen in the weights. Making them smarter
  means another expensive training run, which only a few companies can afford.
- **AI agents** (research agents, coding agents). They search and act during a task,
  then mostly start the next task from zero. Their intelligence still belongs to the
  model vendor.

PolyaBrain is a third kind: **intelligence that compounds from verified experience,
outside the model.**

Research has explored parts of this, for example Voyager's skill library (2023) and
many memory systems (argued). What we believe is new is making it work at product
quality on real problems. That means a brain whose knowledge is:

- learned by reading **and experimenting**;
- stored only after it is **verified**;
- **reused** to make the next problem cheaper and more likely to succeed;
- **portable** across any model.

*To verify with a competitor scan before we claim it publicly.*

If it works, intelligence becomes something you grow by use, not something you buy
with capital. That is the founder's vision in its strongest form.

## 6. Strategy

**Rent tools, own the brain.** Use the best trusted external capability currently
available:

- model providers such as OpenRouter;
- web search APIs;
- sandboxes;
- data sources.

Uber does not own the cars and Google does not own the web. PolyaBrain owns the
intelligence:

- choosing what to learn, which tools and models to use, and how;
- testing its understanding by experiment;
- verifying results;
- accumulating knowledge.

PolyaBrain does not build or train foundation models. Owning our own search, models
or infrastructure, including training small specialist models, waits until we have
the resources. It is adopted only if it measurably beats renting.

**Product surfaces.**

- **PolyaBrain Investigator** is the workbench where people bring hard technical
  problems.
- Integrations (an API, an MCP server for other agents, a GitHub check) are later
  ways to reach users. They are not the identity.

**Who it is for first:** founders, engineers and researchers with hard technical
problems.

**Verification output.** When PolyaBrain verifies a result, it states what was
checked and what was not. Re-runnable evidence is never described as proof for all
cases.

**Evidence so far (measured, small samples):**

- *Chapter 173, verify-change on QuixBugs real bugs:* 38 of 38 bugs caught and 0 false
  alarms on 37 unchanged programs. This was after a harness fix found in the first
  run, which had produced 7 false alarms.
  A later offline replay with stricter coverage retained 38 bug detections and
  34 unchanged controls; three controls abstained for iterator limits/reference
  timeouts. Five of 80 expected historical arm records lacked a saved response
  or attempt. No control was reported as a regression. This replay is not a fresh
  catch-rate trial or real-user evidence; see
  [coverage results](../03_implementation/Chapter_172_Comparison_Coverage.md).
- *Chapter 172, differential verification:* 29 certified and correct, and 0 certified
  but wrong. However, the base model never failed those tasks, so verification has
  not yet been shown to *fix* anything.
- *Chapter 174:* failure-pattern memory exists, but whether it helps is unmeasured.
  The verified-claims frozen evaluation has not run yet; it is blocked on provider
  credits.
- *Learning that compounds across problems:* **not yet measured.** It is the central
  bet.

## 7. Build order

An experience ledger records every run from step 1: problem type, what was missing,
what was learned and how, tools and models used, cost, time, and verification result.

1. **Reliability.** A pinned default model, fallback across providers, and a recovery
   path for every stopped run. *Done when* the founder's next ten real problems all
   finish, with a verified result or an honest, explained stop.
2. **Learning by experiment.** When PolyaBrain lacks knowledge, it learns from
   sources and tests what it learned with sandbox experiments before using it.
3. **Memory that compounds.** Verified facts, procedures, experiment results and
   caught mistakes are stored with their sources. They are retrieved for new
   problems, and they reduce model calls and failures.
4. **The learning-curve benchmark: the proof.** The rules are frozen before any run,
   with the problems, models and prices named and the budget approved.
   - **Domain:** one domain with checkable answers, for example hard Python and data
     problems.
   - **Learning phase:** PolyaBrain solves a set of problems and builds memory.
   - **Test phase:** a held-out set of *new* problems of the same kinds.
   - **Arms on the test set:**
     - a frontier model alone;
     - the cheap model alone;
     - PolyaBrain with the cheap model and its memory **off**;
     - PolyaBrain with the cheap model and its memory **on**.
   - **Measures:** verified correctness, confident wrong answers, cost per correct
     answer, and model calls per problem.
   - **Default win condition** (frozen with the set):
     - memory-on beats memory-off on correctness or cost, by margins fixed at freeze
       time;
     - memory-on has fewer confident wrong answers than the frontier model;
     - memory-on comes within 5 points of the frontier model's correctness, at most
       one third of its cost per correct answer.
5. **Expansion.** More domains, unknown problem types, and integrations that let
   other applications use the brain: the path to the Intelligence OS.

## 8. What would prove us wrong

We will look for these early and report them honestly:

- Memory does not improve results or cost on *new* problems. This would mean the
  brain is not learning, only caching.
- Learning by reading and experiment does not let a cheap model approach frontier
  correctness at a fraction of the cost.
- Stored knowledge degrades results, by retrieving confidently but wrongly.
- Real users do not come back a second time with a hard problem.

If any of these happens, we change the method, not the mission. We never give up; we
find the way to win and keep winning.
