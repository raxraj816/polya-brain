# PolyaBrain: Engine Interaction and the Stateful Polya Loop

> Source-of-truth note: this document explains architecture concepts. If it disagrees with `../../PolyaBrain_Product_Implementation_Master_Plan.md`, follow the master plan.

**Author:** Manus AI
**Date:** May 25, 2026

## 1. Introduction

The true intelligence of PolyaBrain does not reside within any single engine, but rather in the dynamic, stateful interactions between its nine core components. Orchestrated by LangGraph, these engines collaborate in a cyclic workflow that mirrors George Pólya's problem-solving methodology [1]. This document explains the flow of data, the decision-making routing, and the iterative loops that define the PolyaBrain architecture.

## 2. The Linear Flow: From Input to Initial Plan

While problem-solving is inherently iterative, the process begins with a linear progression to establish understanding and formulate an initial strategy.

### 2.1. Initialization and Formalization
1.  **User Input:** The process begins when a user submits a problem to the system.
2.  **Problem Representation Engine:** This engine receives the raw input. It parses the text, identifies entities, and extracts constraints.
    *   *Output:* A formalized JSON schema representing the problem.
    *   *Interaction:* This schema is written to the global LangGraph state, making it accessible to all subsequent engines.

### 2.2. The Knowledge Audit
3.  **Knowledge Gap Detector:** Triggered by the formalized schema, this engine audits the system's current knowledge.
    *   *Interaction:* It queries the **Memory System** (Semantic, Procedural, and Episodic databases) to see if the required facts and strategies are already known.
    *   *Decision Point:*
        *   If all necessary knowledge is present, the state routes directly to the **Reasoning & Hypothesis Generator**.
        *   If gaps are found, it generates a prioritized list of `KnowledgeGap` objects and routes the state to the **Research & Information Acquisition Engine**.

### 2.3. Dynamic Acquisition (If Gaps Exist)
4.  **Research & Information Acquisition Engine:** Receives the `KnowledgeGap` objects.
    *   *Interaction:* It formulates queries, interacts with external APIs, and scrapes web content to find the missing information.
    *   *Output:* Raw, unstructured data snippets.
5.  **Evidence Evaluation Engine:** Receives the raw data.
    *   *Interaction:* It cross-references this new data against the **Memory System** to check for consistency and scores its credibility.
    *   *Output:* Validated facts. These are temporarily added to the global state (and eventually to Semantic Memory) to fill the identified gaps.
    *   *Routing:* Once gaps are filled, the state routes to the **Reasoning & Hypothesis Generator**.

### 2.4. Strategy Formulation
6.  **Reasoning & Hypothesis Generator:** Now equipped with a formalized problem and a complete set of validated knowledge, this engine devises a plan.
    *   *Interaction:* It queries **Procedural Memory** for relevant heuristics and applies first-principles thinking to generate a step-by-step `ProblemSolvingPlan`.
    *   *Routing:* The plan is passed to the **Execution Engine**.

## 3. The Cyclic Flow: Execution, Verification, and Replanning

The core of PolyaBrain's robustness lies in its ability to execute, verify, and iterate. This is where the cyclic nature of LangGraph is fully utilized.

### 3.1. The Execution-Verification Loop
7.  **Execution Engine:** Receives the `ProblemSolvingPlan`.
    *   *Interaction:* It translates the plan into concrete actions, running code in secure sandboxes or calling external tools.
    *   *Output:* Raw execution results and intermediate states.
8.  **Verification Engine:** Receives the execution results and the original problem constraints (from the global state).
    *   *Interaction:* It rigorously tests the output against the constraints.
    *   *Decision Point (The Critical Junction):*
        *   **Success:** If the output satisfies all constraints, the problem is considered solved. The state routes to the **Reflection & Learning Engine**.
        *   **Failure:** If the output fails verification, the engine generates a `VerificationReport` detailing the failure. The state is routed *backwards* in the loop.

### 3.2. The Replanning Routing (Handling Failures)
When the Verification Engine detects a failure, LangGraph intelligently routes the state based on the nature of the error:
*   **Logic/Calculation Error:** If the plan was sound but the execution failed (e.g., a math error in generated code), the state routes back to the **Execution Engine** for a retry or to the **Reasoning Engine** to generate alternative code.
*   **Strategic Error:** If the plan itself was flawed (e.g., it led to a dead end), the state routes back to the **Reasoning & Hypothesis Generator** to devise a new plan, utilizing the failure data as a new constraint.
*   **Information Error:** If the failure reveals that the system acted on incorrect or insufficient information, the state routes all the way back to the **Knowledge Gap Detector** or **Research Engine** to acquire better data.

This cyclic routing continues until the Verification Engine confirms a successful solution or a predefined iteration limit is reached.

## 4. The Final Stage: Reflection and Memory Update

9.  **Reflection & Learning Engine:** Once a solution is verified (or the system exhausts its attempts), this engine activates.
    *   *Interaction:* It analyzes the entire problem-solving trace stored in the global state.
    *   *Memory Updates:*
        *   It writes the complete episode to **Episodic Memory**.
        *   It extracts new, validated facts and writes them to **Semantic Memory**.
        *   It refines successful strategies and updates the graph in **Procedural Memory**.
    *   *RL Update:* It adjusts internal policy weights based on the efficiency of the path taken.

## 5. Summary of Interactions

The interaction between the engines is not a static pipeline but a dynamic, state-driven conversation.
*   The **Problem Representation Engine** sets the terms of the conversation.
*   The **Knowledge Gap Detector**, **Research Engine**, and **Evidence Evaluation Engine** ensure the system is fully informed before acting.
*   The **Reasoning Engine** and **Execution Engine** propose and enact solutions.
*   The **Verification Engine** acts as the strict judge, forcing iterative loops until correctness is achieved.
*   The **Reflection Engine** ensures that every interaction, successful or not, makes the system smarter for the next problem.
*   The **Memory System** serves as the shared foundation, constantly queried and updated by all other engines.

## References

[1] George Pólya, *How to Solve It: A New Aspect of Mathematical Method*. Princeton University Press, 1945.
