# Creative Problem-Solving Product Translation

> Source-of-truth note: this research translation supports implementation decisions. If it disagrees with `../../PolyaBrain_Product_Implementation_Master_Plan.md`, follow the master plan.

## Why This Matters

The useful lesson from creativity and brain-science research is not that PolyaBrain should simulate a brain. The useful lesson is that hard problems improve when a system can alternate between open exploration and disciplined evaluation, use prior knowledge flexibly, reframe weak problem constructions, and verify what survives.

For PolyaBrain, creativity means: generate useful alternatives, transfer structure from past cases, expose uncertainty, and prove or reject candidates.

## Product Mechanisms To Adopt

1. **Divergent before convergent reasoning**
   Generate several meaningfully different hypotheses or solution paths before ranking. This protects against early anchoring.

2. **Convergent filtering**
   Rank candidates by evidence support, evidence against, constraint fit, falsifiability, feasibility, verification cost, and risk.

3. **Knowledge-rich analogical transfer**
   Retrieve structurally similar solved cases, strategies, and patterns, including cross-domain cases. Require the engine to state what transfers, what does not transfer, and what needs verification.

4. **Bounded incubation/reframe pass**
   After initial evidence gathering, ask what assumption, framing, analogy, or missing angle may have been overlooked. Treat outputs as candidates only; route them back through evidence evaluation and verification.

5. **Trace-visible reasoning modes**
   Label reasoning events as `explore`, `compare`, `reframe`, `execute`, `verify`, or `reflect` so users can audit how the system moved from possibilities to conclusions.

## Product Behaviors To Avoid

- Do not add a user-facing "daydreaming mode."
- Do not use default-mode network, executive network, salience network, cerebellum, alpha waves, or other brain terms as product UI labels.
- Do not reward novelty unless it remains useful, evidence-linked, falsifiable, and verified.
- Do not add a separate creativity engine for the MVP. Put these behaviors into the existing hypothesis, memory, verification, and reflection engines.

## Implementation Surface

- **Problem representation:** preserve assumptions and possible alternate framings.
- **Approach selection:** choose the investigation mode and checklist before planning. Infer mode when absent, ask when uncertain, and allow user override.
- **Memory retrieval:** support similarity by structure, mechanism, and strategy, not only keyword or domain.
- **Hypothesis engine:** record `origin`, `analogical_source_ids`, `falsification_criteria`, and `selection_rationale`. Measure hypothesis diversity at the run/evaluation level rather than storing novelty as a core per-hypothesis score.
- **Verification engine:** explicitly test analogies and reframes rather than accepting them as explanations. Use mode-specific checklists for technical research, debugging, architecture tradeoffs, data analysis, ambiguous input, and creative synthesis.
- **Reflection engine:** store which hypothesis-generation, analogy, and reframe strategies helped or failed.
- **Benchmarks:** include cases where the correct behavior requires multiple hypotheses, cross-domain analogy, reframing, and evidence-backed selection.

## Practical Problem-Solving Additions

These sources are practical advice rather than scientific authority, but they reinforce useful product behavior:

- Define and redefine the problem before solving.
- Choose the right paradigm or approach before planning.
- Use systematic checklists to avoid missing important checks.
- Treat failure as feedback for reflection and future strategy.

Product translation:

- Add a problem reframe pass before hypothesis generation.
- Select the investigation approach using existing product modes and problem types.
- Use mode-specific verification checklists instead of generic verification.
- Keep these as prompt behavior, trace details, procedural strategies, and eval criteria unless they later earn core contract status.

## Source Notes

- Lone Star Neurology, daydreaming and problem solving: useful as a practical description of mind wandering, but weaker than primary literature. Product translation: bounded reframe pass, not an answer generator. https://lonestarneurology.net/others/how-daydreaming-influences-problem-solving-and-creativity-in-the-brain/
- NIH/PMC article on creative brain activity during creative problem solving: useful support for separating internally focused generation from evaluation. Product translation: do not over-control the first generation pass. https://pmc.ncbi.nlm.nih.gov/articles/PMC6871103/
- ScienceDirect, "Creative problem solving in knowledge-rich contexts": strongest product-relevant source. Product translation: analogical transfer over rich memory, especially when solving real technical problems. https://www.sciencedirect.com/science/article/abs/pii/S1364661322001565
- HBS Online, creative problem solving: useful operational framing around divergence and convergence. https://online.hbs.edu/blog/post/what-is-creative-problem-solving
- Stanford Medicine, creativity and executive control: useful warning against premature evaluation during idea generation. https://med.stanford.edu/news/all-news/2015/05/researchers-tie-unexpected-brain-structures-to-creativity.html
- Penn LPS, science of creativity: useful summary of divergent/convergent thinking, associative thinking, reframing, constraints, and environment. https://lpsonline.sas.upenn.edu/features/science-creativity-how-train-your-brain-innovative-thinking
- APA Monitor, science behind creativity: useful summary of creativity as a process involving coordination between spontaneous and controlled cognition. https://www.apa.org/monitor/2022/04/cover-science-creativity
- Braintastic Science, creativity in problem solving: useful accessible framing of novelty plus usefulness and divergent/convergent reasoning. https://www.braintasticscience.com/post/creativity-problem-solving
- Psychology Today, creativity and the brain: useful summary of default, executive, and salience network coordination; translate only into product mode switching, not neuroscience claims. https://www.psychologytoday.com/us/blog/how-my-brain-works/202403/creativity-and-the-brain
- Brian Tracy, creative thinking and problem solving: useful practical framing around problem definition, redefining the problem, gathering data, systematic checklists, and feedback. https://www.briantracy.com/blog/personal-success/are-you-a-genius-how-geniuses-use-creative-thinking-to-solve-problems/
- IdeaScale, creative problem-solving techniques: useful as a source of procedural strategy cards such as analogy, reverse thinking, perspective taking, and structured perspective separation. https://ideascale.com/blog/creative-problem-solving-techniques/
- Amy Rees Anderson, problem solving and inner genius: useful practical framing around curiosity, persistence, validating ideas, and turning complaints into solvable problems. https://www.amyreesanderson.com/blog/be-a-problem-solver-and-discover-your-inner-genius/
- TIME/Quora, solving hard problems: useful practical framing around choosing the right paradigm, pattern recognition, and insight. https://time.com/2827513/how-can-i-improve-my-ability-to-solve-hard-problems/
