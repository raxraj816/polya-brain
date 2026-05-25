# PolyaBrain: Problem-Solving Examples through the Polya Loop

**Author:** Manus AI
**Date:** May 25, 2026

## 1. Introduction

PolyaBrain's core strength lies in its ability to apply George Pólya's problem-solving methodology—Understand, Plan, Execute, and Reflect—in a dynamic, iterative loop. This process is orchestrated by LangGraph, which intelligently routes the problem state between PolyaBrain's nine specialized engines. This document illustrates how PolyaBrain navigates various problem types, demonstrating the intricate interactions and adaptive capabilities of its framework.

## 2. Example 1: Solving a Complex Mathematical Optimization Problem

**Problem Statement:** "Find the maximum value of `f(x, y) = x^2 + y^2` subject to the constraint `x + y = 10` and `x, y >= 0`."

### 2.1. Understand the Problem

1.  **Problem Representation Engine:**
    *   **Input:** The natural language problem statement.
    *   **Process:** Parses the statement, identifying the objective function `f(x, y) = x^2 + y^2`, the equality constraint `x + y = 10`, and the inequality constraints `x >= 0, y >= 0`. It formalizes these into a JSON schema: `{"type": "optimization", "objective": "maximize x^2 + y^2", "constraints": ["x + y = 10", "x >= 0", "y >= 0"]}`.
    *   **Output:** Formalized problem schema.

2.  **Knowledge Gap Detector:**
    *   **Process:** Compares the formalized problem with **Semantic Memory** (for definitions of optimization, calculus) and **Procedural Memory** (for known optimization techniques like Lagrange multipliers, substitution). It identifies that the problem is a constrained optimization, and the substitution method is a known strategy.
    *   **Output:** No critical knowledge gaps requiring external research; a known procedural strategy (substitution) is identified.

### 2.2. Devise a Plan

1.  **Reasoning & Hypothesis Generator:**
    *   **Process:** Accesses **Procedural Memory** to retrieve the 
substitution method for constrained optimization. It formulates a plan:
        1.  Express `y` in terms of `x` from the constraint `x + y = 10` (i.e., `y = 10 - x`).
        2.  Substitute `y` into the objective function to get `f(x) = x^2 + (10 - x)^2`.
        3.  Find the derivative `f'(x)` and set it to zero to find critical points.
        4.  Evaluate `f(x)` at critical points and boundary conditions (`x=0`, `x=10`).
    *   **Output:** A `ProblemSolvingPlan` detailing these steps.

### 2.3. Carry Out the Plan

1.  **Execution Engine:**
    *   **Process:** Executes the plan step-by-step in a secure Python sandbox:
        *   `y = 10 - x`
        *   `f(x) = x**2 + (10 - x)**2 = x**2 + 100 - 20x + x**2 = 2x**2 - 20x + 100`
        *   `f'(x) = 4x - 20`. Setting `f'(x) = 0` gives `4x = 20`, so `x = 5`.
        *   If `x = 5`, then `y = 10 - 5 = 5`.
        *   Evaluate `f(5, 5) = 5^2 + 5^2 = 25 + 25 = 50`.
        *   Evaluate boundary conditions: `f(0, 10) = 0^2 + 10^2 = 100`, `f(10, 0) = 10^2 + 0^2 = 100`.
    *   **Output:** Intermediate calculations and final values: `x=5, y=5, f(5,5)=50` and boundary values `f(0,10)=100, f(10,0)=100`.

2.  **Verification Engine:**
    *   **Process:** Compares the results against the problem constraints and objective.
        *   Checks `x=5, y=5`: `x+y=10` (True), `x>=0, y>=0` (True).
        *   Identifies the maximum value among `50, 100, 100` as `100`.
        *   Realizes that the critical point `(5,5)` yielded a local minimum, and the maximum occurs at the boundaries.
    *   **Output:** `VerificationReport` indicating the maximum value is 100, occurring at `(0, 10)` or `(10, 0)`.

### 2.4. Look Back

1.  **Reflection & Learning Engine:**
    *   **Process:** Analyzes the entire trace. It notes that while the substitution method was correct, the initial assumption of an interior maximum was flawed. It identifies the importance of checking boundary conditions in constrained optimization problems.
    *   **Memory Updates:**
        *   **Episodic Memory:** Stores the full problem-solving trace, including the initial plan, execution steps, and the verification outcome that highlighted the boundary condition importance.
        *   **Procedural Memory:** Updates the graph to emphasize a heuristic: "For constrained optimization, always evaluate objective function at critical points *and* boundary conditions of the feasible region."
    *   **Output:** Updated memory systems and refined procedural heuristics.

## 3. Example 2: Real-time Technical Research for a Novel API

**Problem Statement:** "A user wants to integrate a new `async` feature from the `Rust` programming language into an existing codebase. The feature is called `async traits`. Provide a code example and explain its usage."

### 3.1. Understand the Problem

1.  **Problem Representation Engine:**
    *   **Input:** The natural language request.
    *   **Process:** Identifies key entities: `Rust`, `async traits`, `code example`, `explanation`. Formalizes into: `{"type": "technical_research", "topic": "Rust async traits", "output_format": "code_example, explanation"}`.
    *   **Output:** Formalized problem schema.

2.  **Knowledge Gap Detector:**
    *   **Process:** Queries **Semantic Memory** for `Rust`, `async`, `traits`. Finds general knowledge but no specific, up-to-date information on `async traits` (as it might be a new or evolving feature). Queries **Procedural Memory** for `code generation` and `technical explanation` strategies.
    *   **Output:** `KnowledgeGap` for "current status and usage of Rust async traits," "best practices for async traits," and "example code for async traits."

### 3.2. Devise a Plan (Initial, with Research)

1.  **Reasoning & Hypothesis Generator:**
    *   **Process:** Recognizes the need for external information. Formulates a research plan:
        1.  Search for "Rust async traits status" and "Rust async traits example".
        2.  Evaluate search results for official documentation, blog posts, and code repositories.
        3.  Extract relevant information and code snippets.
        4.  Synthesize explanation and generate a code example.
    *   **Output:** A `ProblemSolvingPlan` with research steps.

### 3.3. Carry Out the Plan (with Iteration)

1.  **Research & Information Acquisition Engine:**
    *   **Process:** Executes search queries (e.g., using Tavily API). Finds recent RFCs, compiler issue trackers, and community discussions, indicating `async traits` are still experimental or unstable.
    *   **Output:** URLs and snippets from `rust-lang.github.io/rfcs`, `github.com/rust-lang/rust/issues`, and relevant blog posts.

2.  **Evidence Evaluation Engine:**
    *   **Process:** Assesses credibility (high for official Rust sources, moderate for community blogs). Notes that the feature is still under active development and requires nightly Rust.
    *   **Output:** Validated information: `async traits` are experimental, require nightly, and current syntax might change.

3.  **Reasoning & Hypothesis Generator (Re-plan):**
    *   **Process:** Updates its understanding based on validated evidence. The initial plan to provide a stable code example is revised. The new plan is to explain the experimental nature, provide a *nightly* example, and warn about instability.
    *   **Output:** Revised `ProblemSolvingPlan`.

4.  **Execution Engine:**
    *   **Process:** Generates a code example using the identified nightly syntax. Writes a detailed explanation covering the feature, its experimental status, and how to enable it.
    *   **Output:** Markdown formatted explanation and code snippet.

5.  **Verification Engine:**
    *   **Process:** Checks if the explanation is clear, the code example is syntactically correct (for nightly Rust), and all parts of the original problem (code example, explanation, usage) are addressed. It also verifies that the experimental nature is clearly stated.
    *   **Output:** `VerificationReport` (Success).

### 3.4. Look Back

1.  **Reflection & Learning Engine:**
    *   **Process:** Analyzes the trace. It notes the successful adaptation to an evolving technical landscape. It reinforces the procedural heuristic: "For cutting-edge technical queries, prioritize official RFCs, issue trackers, and recent community discussions over older documentation."
    *   **Memory Updates:**
        *   **Episodic Memory:** Stores the full trace, including the dynamic adaptation to the feature's experimental status.
        *   **Semantic Memory:** Updates with the current status of `Rust async traits`.
        *   **Procedural Memory:** Strengthens the link between "novel technical feature" and "research official sources, check stability."
    *   **Output:** Updated memory systems and refined procedural heuristics.

## 4. Example 3: Debugging a Software Bug in a Web Application

**Problem Statement:** "A user reports that the 'Add to Cart' button on the e-commerce website is not working, and no items are being added to the cart. Provide a root cause analysis and a fix."

### 4.1. Understand the Problem

1.  **Problem Representation Engine:**
    *   **Input:** User bug report.
    *   **Process:** Identifies `e-commerce website`, `Add to Cart button`, `not working`, `no items added`. Formalizes into: `{"type": "software_bug", "component": "Add to Cart", "symptom": "items not added", "severity": "critical"}`.
    *   **Output:** Formalized problem schema.

2.  **Knowledge Gap Detector:**
    *   **Process:** Queries **Episodic Memory** for similar `Add to Cart` bugs, **Procedural Memory** for `web debugging strategies` (e.g., check network requests, console errors, backend logs), and **Semantic Memory** for `e-commerce cart logic`. Initially, it finds general debugging knowledge but no specific solution for this exact bug.
    *   **Output:** `KnowledgeGap` for "specific error messages," "network request details," "backend API response for add to cart."

### 4.2. Devise a Plan (Initial Debugging Strategy)

1.  **Reasoning & Hypothesis Generator:**
    *   **Process:** Formulates a debugging plan based on common web application issues:
        1.  Simulate user action (click 'Add to Cart').
        2.  Monitor browser console for JavaScript errors.
        3.  Inspect network requests (XHR/Fetch) for the 'Add to Cart' action.
        4.  Analyze the request payload and server response.
        5.  Check backend logs for errors related to cart operations.
        6.  Hypothesize potential causes (frontend JS error, incorrect API endpoint, backend validation failure, database issue).
    *   **Output:** A `ProblemSolvingPlan` for diagnostic steps.

### 4.3. Carry Out the Plan (with Iteration and Dynamic Tool Use)

1.  **Execution Engine:**
    *   **Process:** Simulates browser interaction. Executes commands to:
        *   Open the website in a headless browser.
        *   Click the 'Add to Cart' button.
        *   Capture browser console output.
        *   Intercept and log network requests for the 'Add to Cart' API call.
        *   Access and filter backend logs for relevant timestamps.
    *   **Output:** Console errors (e.g., `TypeError: Cannot read properties of undefined (reading 'productId')`), network request details (e.g., API call to `/api/cart/add` returns `400 Bad Request`), backend log entries (e.g., `ERROR: Product ID missing in request body`).

2.  **Verification Engine:**
    *   **Process:** Analyzes the collected data.
        *   **Console Error:** `TypeError` indicates a frontend JavaScript issue with accessing `productId`.
        *   **Network Request:** `400 Bad Request` from `/api/cart/add` confirms a server-side rejection due to invalid input.
        *   **Backend Log:** `Product ID missing` directly correlates with the frontend error.
    *   **Output:** `VerificationReport` indicating a clear root cause: the frontend is failing to send the `productId` in the API request payload.

### 4.4. Look Back (and Implement Fix)

1.  **Reflection & Learning Engine:**
    *   **Process:** Analyzes the debugging trace. The problem was a mismatch between frontend data access and backend API expectations. The diagnostic plan successfully pinpointed the issue.
    *   **Memory Updates:**
        *   **Episodic Memory:** Stores the full debugging session, including the diagnostic steps, observed errors, and the identified root cause.
        *   **Procedural Memory:** Strengthens the heuristic: "When 'Add to Cart' fails, systematically check frontend console errors, network request payloads/responses, and backend logs for input validation issues."
    *   **Output:** Updated memory systems.

2.  **Reasoning & Hypothesis Generator (Re-plan for Fix):**
    *   **Process:** Formulates a plan to fix the bug: Modify the frontend JavaScript to correctly retrieve the `productId` from the DOM and include it in the API request payload.
    *   **Output:** A `ProblemSolvingPlan` for code modification.

3.  **Execution Engine (Implement Fix):**
    *   **Process:** Edits the relevant frontend JavaScript file to correct the `productId` retrieval and payload construction.
    *   **Output:** Modified code.

4.  **Verification Engine (Verify Fix):**
    *   **Process:** Re-runs the 'Add to Cart' simulation. Checks console, network, and backend logs. Confirms item is added to cart successfully.
    *   **Output:** `VerificationReport` (Success - Bug Fixed).

## 5. Conclusion

These examples demonstrate PolyaBrain's adaptive and iterative problem-solving capabilities. From mathematical optimization to real-time research and software debugging, the framework consistently applies the Polya loop:

*   **Understanding:** Through the Problem Representation and Knowledge Gap Detector engines.
*   **Planning:** By the Reasoning & Hypothesis Generator, often dynamically re-planning based on new information or failures.
*   **Execution:** Via the Execution Engine, leveraging secure sandboxes and tool integration.
*   **Reflection:** Enabled by the Reflection & Learning Engine, which updates the hybrid memory system to ensure continuous improvement.

This dynamic interaction between specialized engines, orchestrated by LangGraph, allows PolyaBrain to not only find solutions but also to learn from its experiences, making it a truly intelligent and adaptable system.

## References

[1] George Pólya, *How to Solve It: A New Aspect of Mathematical Method*. Princeton University Press, 1945.
