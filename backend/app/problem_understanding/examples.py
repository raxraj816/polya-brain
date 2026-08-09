"""Ten validated local examples required by the Chapter 11 prompt gate."""

from __future__ import annotations

from app.models.contracts import ProductMode
from app.problem_understanding.contracts import (
    ProblemUnderstandingExample,
    ProblemUnderstandingOutput,
    PromptExampleCategory,
)


def _output(**overrides: object) -> ProblemUnderstandingOutput:
    payload: dict[str, object] = {
        "literal_framing": "Solve the stated problem.",
        "deeper_framing": "Identify the desired result and the constraints that determine it.",
        "wrong_problem_warning": None,
        "goal": "Produce a correct, verifiable result.",
        "problem_type": "general_reasoning",
        "domain": None,
        "selected_mode": ProductMode.EXPLORE,
        "mode_confidence": 0.9,
        "mode_selection_reason": "The user asks to solve an open problem.",
        "needs_clarification": False,
        "clarifying_questions": [],
        "given": [],
        "unknown": [],
        "constraints": [],
        "success_criteria": ["The result is derived and independently checked."],
        "affected_entities": [],
        "time_window": {},
        "required_data_sources": [],
    }
    payload.update(overrides)
    return ProblemUnderstandingOutput.model_validate(payload)


PROBLEM_UNDERSTANDING_EXAMPLES: tuple[ProblemUnderstandingExample, ...] = (
    ProblemUnderstandingExample(
        category=PromptExampleCategory.MATH,
        raw_input="A rectangle has perimeter 30 and width 5. What is its area?",
        domain_hint="mathematics",
        output=_output(
            literal_framing="Find the area of a rectangle from its perimeter and width.",
            deeper_framing="Derive the missing length from the perimeter constraint before calculating area.",
            goal="Calculate and verify the rectangle's area.",
            problem_type="algebra_word_problem",
            domain="mathematics",
            given=["Perimeter is 30.", "Width is 5."],
            unknown=["Rectangle length.", "Rectangle area."],
            constraints=["For a rectangle, perimeter equals twice length plus twice width."],
            success_criteria=[
                "Length satisfies the perimeter equation.",
                "Area equals length times width.",
            ],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.LOGIC,
        raw_input="Either A or B is true, but not both. A is false. Which is true?",
        domain_hint="logic",
        output=_output(
            literal_framing="Determine which proposition is true under exclusive-or constraints.",
            deeper_framing="Apply the exclusivity constraint after using the known truth value of A.",
            goal="Determine whether B is true and verify there is no contradiction.",
            problem_type="deductive_logic",
            domain="logic",
            given=["Exactly one of A and B is true.", "A is false."],
            unknown=["Truth value of B."],
            constraints=["A and B cannot both be true or both be false."],
            success_criteria=["The selected truth values satisfy exclusive-or."],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.SOFTWARE_DEBUGGING,
        raw_input="API p95 latency doubled after yesterday's deploy. Should we add Redis?",
        mode_hint=ProductMode.INVESTIGATE,
        domain_hint="software_debugging",
        output=_output(
            literal_framing="Decide whether Redis is the right response to a latency regression.",
            deeper_framing="Identify the deploy-related bottleneck before choosing a permanent fix.",
            wrong_problem_warning="Adding cache before isolating the regression may solve the wrong problem.",
            goal="Identify the safest diagnostic that can explain the latency regression.",
            problem_type="software_root_cause_investigation",
            domain="software_debugging",
            selected_mode=ProductMode.INVESTIGATE,
            mode_confidence=0.97,
            mode_selection_reason="The user supplied an anomaly and asks which cause or response to investigate.",
            given=["API p95 latency doubled.", "The change followed yesterday's deploy."],
            unknown=[
                "Which component contributes the added latency.",
                "Whether the deploy caused the regression.",
            ],
            constraints=["Avoid adding infrastructure before measuring the bottleneck."],
            success_criteria=[
                "A reversible check distinguishes query, application, and dependency latency."
            ],
            affected_entities=["API", "deployment", "query path"],
            time_window={"relative": "after yesterday's deploy"},
            required_data_sources=["distributed traces", "deploy diff", "query metrics"],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.TECHNICAL_RESEARCH,
        raw_input="What is the current browser support for WebGPU and what should our app assume?",
        domain_hint="technical_research",
        output=_output(
            literal_framing="Research current WebGPU browser support and derive implementation assumptions.",
            deeper_framing="Separate current official support from fallback requirements for the app's target users.",
            goal="Produce a current, source-grounded WebGPU compatibility recommendation.",
            problem_type="current_technology_research",
            domain="technical_research",
            selected_mode=ProductMode.EXPLORE,
            mode_confidence=0.88,
            mode_selection_reason="The task requires current external evidence before recommending an approach.",
            given=["The application may use WebGPU."],
            unknown=[
                "Current support by browser and platform.",
                "Target-user browser distribution.",
            ],
            constraints=["Currentness must be verified with primary sources."],
            success_criteria=["Support claims are sourced and fallback assumptions are explicit."],
            required_data_sources=[
                "official browser documentation",
                "WebGPU specification or status pages",
            ],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.DATA_ANALYSIS,
        raw_input="Compare this month's conversion rate with last month and explain the largest segment changes.",
        mode_hint=ProductMode.COMPARE,
        domain_hint="data_analysis",
        output=_output(
            literal_framing="Compare conversion rates across two periods and explain segment deltas.",
            deeper_framing="Determine whether aggregate movement is driven by within-segment change or mix shift.",
            goal="Quantify and explain the conversion-rate change by segment.",
            problem_type="period_over_period_segment_analysis",
            domain="data_analysis",
            selected_mode=ProductMode.COMPARE,
            mode_confidence=0.99,
            mode_selection_reason="The user explicitly requests a baseline comparison.",
            given=["The comparison periods are this month and last month."],
            unknown=["Conversion counts and denominators.", "Available segment dimensions."],
            constraints=["Use aligned definitions and complete time windows."],
            success_criteria=["Aggregate and segment deltas reconcile to the source data."],
            time_window={"current": "this month", "baseline": "last month"},
            required_data_sources=["conversion table with period and segment fields"],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.PLANNING,
        raw_input="Plan a safe migration from a monolith database to service-owned schemas.",
        domain_hint="architecture_planning",
        output=_output(
            literal_framing="Create a safe database-ownership migration plan.",
            deeper_framing="Sequence reversible ownership boundaries and compatibility steps before physical separation.",
            goal="Produce a phased, verifiable migration plan with rollback points.",
            problem_type="technical_migration_planning",
            domain="architecture_planning",
            selected_mode=ProductMode.EXPLORE,
            mode_confidence=0.91,
            mode_selection_reason="The user asks to devise a plan rather than diagnose an observed anomaly.",
            given=[
                "The current system uses a monolith database.",
                "The target uses service-owned schemas.",
            ],
            unknown=[
                "Service boundaries.",
                "Downtime tolerance.",
                "Cross-service transaction requirements.",
            ],
            constraints=["Migration must be reversible and preserve data integrity."],
            success_criteria=[
                "Each phase has entry, verification, rollback, and ownership criteria."
            ],
            affected_entities=["services", "database schemas", "data owners"],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.SCIENTIFIC_REASONING,
        raw_input="Battery capacity fell after changing electrolyte concentration. Design the next experiment.",
        domain_hint="scientific_reasoning",
        output=_output(
            literal_framing="Design an experiment to test whether electrolyte concentration reduced capacity.",
            deeper_framing="Separate concentration effects from batch, temperature, and measurement confounders.",
            goal="Design a controlled experiment that can support or falsify the concentration hypothesis.",
            problem_type="controlled_experiment_design",
            domain="scientific_reasoning",
            selected_mode=ProductMode.INVESTIGATE,
            mode_confidence=0.9,
            mode_selection_reason="The task investigates a possible causal explanation for an observed change.",
            given=["Measured battery capacity fell after electrolyte concentration changed."],
            unknown=[
                "Whether concentration caused the drop.",
                "Relevant batch and temperature effects.",
            ],
            constraints=["Control non-concentration variables and include replication."],
            success_criteria=[
                "The experiment has controls, replicates, measurements, and falsification criteria."
            ],
            affected_entities=["battery cells", "electrolyte batches"],
            required_data_sources=[
                "capacity measurements",
                "batch metadata",
                "temperature records",
            ],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.AMBIGUOUS_INPUT,
        raw_input="Make it faster.",
        output=_output(
            literal_framing="Improve an unspecified system's speed.",
            deeper_framing="Identify the target workflow, current baseline, and acceptable tradeoffs before optimizing.",
            wrong_problem_warning="Optimizing without a target metric or bottleneck could add cost without user value.",
            goal="Clarify what must become faster and how improvement will be measured.",
            problem_type="underspecified_performance_request",
            selected_mode=ProductMode.EXPLORE,
            mode_confidence=0.42,
            mode_selection_reason="The request lacks a target system, metric, baseline, and desired outcome.",
            needs_clarification=True,
            clarifying_questions=[
                "Which system or workflow should become faster?",
                "What metric and current baseline define the performance problem?",
            ],
            given=["The user wants a speed improvement."],
            unknown=[
                "Target system.",
                "Performance metric.",
                "Current baseline.",
                "Acceptable tradeoffs.",
            ],
            constraints=["Do not choose an optimization before the target and metric are known."],
            success_criteria=["The user identifies a measurable target and acceptable tradeoffs."],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.LOW_CONFIDENCE_MODE,
        raw_input="Look at our architecture proposal and tell me what to do.",
        output=_output(
            literal_framing="Evaluate an architecture proposal and recommend an action.",
            deeper_framing="Clarify whether the user wants review, comparison, or implementation planning.",
            goal="Select the intended evaluation approach before analyzing the proposal.",
            problem_type="ambiguous_architecture_decision",
            domain="software_architecture",
            selected_mode=ProductMode.REVIEW,
            mode_confidence=0.48,
            mode_selection_reason="The word proposal suggests review, but the requested decision and alternatives are absent.",
            needs_clarification=True,
            clarifying_questions=[
                "Should PolyaBrain review one proposal, compare alternatives, or plan implementation?",
                "What constraints and decision criteria should the proposal satisfy?",
            ],
            given=["An architecture proposal exists."],
            unknown=["Proposal content.", "Decision criteria.", "Desired product mode."],
            constraints=["Preserve the user's mode override after clarification."],
            success_criteria=["The requested mode and decision criteria are explicit."],
            required_data_sources=["architecture proposal"],
        ),
    ),
    ProblemUnderstandingExample(
        category=PromptExampleCategory.WRONG_PROBLEM_FRAMING,
        raw_input="Our checkout times out, so choose which cache vendor we should buy.",
        mode_hint=ProductMode.INVESTIGATE,
        domain_hint="software_debugging",
        output=_output(
            literal_framing="Choose a cache vendor to address checkout timeouts.",
            deeper_framing="Identify the verified checkout timeout mechanism before selecting infrastructure.",
            wrong_problem_warning="Vendor selection assumes caching is the solution before the timeout cause is known.",
            goal="Determine the checkout timeout cause and the smallest reversible next check.",
            problem_type="software_root_cause_investigation",
            domain="software_debugging",
            selected_mode=ProductMode.INVESTIGATE,
            mode_confidence=0.96,
            mode_selection_reason="The user override and reported timeout make root-cause investigation the correct approach.",
            given=["Checkout requests time out.", "The user proposes buying a cache service."],
            unknown=[
                "Timeout mechanism.",
                "Dominant latency component.",
                "Whether caching addresses it.",
            ],
            constraints=["Do not recommend a vendor before verifying the solution class."],
            success_criteria=[
                "Evidence identifies the timeout mechanism before infrastructure selection."
            ],
            affected_entities=["checkout", "dependencies", "data access path"],
            required_data_sources=["checkout traces", "timeout logs", "dependency latency"],
        ),
    ),
)
