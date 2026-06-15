# PolyaBrain: Detailed Nine-Engine Framework Report

> Source-of-truth note: this document explains architecture concepts. If it disagrees with `../../PolyaBrain_Product_Implementation_Master_Plan.md`, follow the master plan.

**Author:** Manus AI
**Date:** May 25, 2026

## 1. Introduction

PolyaBrain is an advanced artificial intelligence system designed to emulate human-like problem-solving through a structured, iterative process. At its core, PolyaBrain operationalizes George Pólya’s renowned problem-solving methodology—Understand the Problem, Devise a Plan, Carry Out the Plan, and Look Back—into a sophisticated framework comprising nine interconnected engines [1]. This report provides an in-depth examination of each of these engines, detailing their individual functionalities, internal logic, data interfaces, and their synergistic roles within the overarching Polya problem-solving loop.

This modular design ensures that PolyaBrain can not only process information but also reason, learn, and adapt to novel and complex challenges by explicitly managing its knowledge state and problem-solving trajectory.

## 2. The Nine-Engine Framework

The PolyaBrain architecture is meticulously engineered around nine specialized engines, each contributing a distinct cognitive function to the problem-solving process. These engines are orchestrated to work in concert, forming a dynamic and reflective system capable of tackling diverse problems from first principles.

### 2.1. Problem Representation Engine

The initial gateway for any problem, this engine is responsible for transforming raw, unstructured input into a precise, computable format. This foundational step is crucial for all subsequent reasoning.

*   **Functionality:**
    *   **Input Parsing:** Accepts diverse inputs including natural language text, mathematical equations, logical statements, or even structured data.
    *   **NLP Pipelines:** Employs advanced Natural Language Processing (NLP) techniques for tokenization, named entity recognition, and dependency parsing.
    *   **LLM Semantic Parsing:** Utilizes large language models (LLMs) to semantically interpret the input, extracting key entities, their relationships, initial conditions, and implicit contextual information.
    *   **Problem Reframing:** Produces the literal framing, possible deeper framing, and wrong-problem warning when the user may be asking a question that would lead to an unhelpful solution.
    *   **Approach Selection:** Classifies the problem into the existing product mode and problem type so later stages can use the right playbook and verification checklist. If the user does not provide a mode, the engine infers it, records the reason, and asks for clarification when confidence is low.
    *   **Constraint Discovery:** Identifies and formalizes both explicit constraints (e.g., 
"A > B") and implicit constraints (e.g., "variables must be non-negative") that govern the problem space.
*   **Data Interfaces:**
    *   **Input:** Raw problem statement (string, JSON, etc.).
    *   **Output:** A formalized JSON schema representing the problem, including `problem_id`, `entities`, `constraints`, `goal`, and `state`.
*   **Role in Polya Loop:** Corresponds to the initial "Understand the Problem" stage, providing a clear, unambiguous definition for the system.

### 2.2. Knowledge Gap Detector

This engine embodies PolyaBrain's self-awareness, actively identifying what information is missing to solve a given problem. It prevents hallucination by explicitly flagging unknowns.

*   **Functionality:**
    *   **Knowledge State Comparison:** Compares the requirements derived from the Problem Representation Engine against the system's current knowledge base, which spans Semantic, Procedural, and Episodic memories.
    *   **Vector Similarity Search:** Queries the Semantic Memory (Vector Database) using embeddings of problem elements to find relevant factual knowledge. A low similarity score indicates a potential knowledge gap.
    *   **Graph Traversal:** Explores the Procedural Memory (Graph Database) to determine if a known strategy or method exists for the current problem type. A missing path signifies a procedural gap.
    *   **Episodic Memory Query:** Searches the Episodic Memory (Relational Database) for similar past problems and their solutions, identifying if a novel situation requires new information.
    *   **Gap Prioritization:** Ranks identified knowledge gaps based on their criticality and potential impact on the problem-solving process, guiding the Research Engine.
*   **Data Interfaces:**
    *   **Input:** Formalized problem schema from Problem Representation Engine, current state of Semantic, Procedural, and Episodic Memories.
    *   **Output:** A prioritized list of `KnowledgeGap` objects, each specifying the type of missing information (fact, procedure, data), its context, and its criticality.
*   **Role in Polya Loop:** A crucial part of "Understand the Problem," it triggers the dynamic information acquisition process.

### 2.3. Research & Information Acquisition Engine

When a knowledge gap is detected, this engine takes the initiative to find the necessary information from external sources.

*   **Functionality:**
    *   **Query Formulation:** Translates `KnowledgeGap` objects into optimized search queries for external search APIs (e.g., Tavily, SerpAPI) or internal knowledge bases.
    *   **External API Integration:** Manages secure interactions with various web search and data APIs, handling rate limits and API keys.
    *   **Smart Web Scraping:** Deploys robust, adaptive web scrapers to extract structured and unstructured content from web pages, intelligently filtering out boilerplate, advertisements, and irrelevant sections.
    *   **Data Extraction:** Uses LLMs to extract specific facts, definitions, or data points from the retrieved content, aligning with the identified knowledge gap.
*   **Data Interfaces:**
    *   **Input:** Prioritized `KnowledgeGap` objects from the Knowledge Gap Detector.
    *   **Output:** Raw, potentially noisy, but targeted information (text, data snippets, URLs) from external sources, stored in a temporary staging area.
*   **Role in Polya Loop:** Part of "Understand the Problem," it actively fills knowledge deficits.

### 2.4. Evidence Evaluation Engine

This engine acts as PolyaBrain's critical filter, ensuring the integrity and reliability of all acquired information before it influences reasoning.

*   **Functionality:**
    *   **Credibility Assessment:** Employs a set of predefined heuristics and LLM-based analysis to assess the trustworthiness of information sources (e.g., domain authority, publication reputation, presence of citations, recency).
    *   **Consistency Checks:** Cross-references newly acquired data with existing information in Semantic and Episodic memories to detect contradictions, inconsistencies, or logical fallacies.
    *   **Relevance Scoring:** Determines how pertinent the acquired information is to the specific knowledge gap and the overall problem, assigning a relevance score.
    *   **Ambiguity Handling:** Identifies ambiguous or incomplete information and, if necessary, triggers a feedback loop to the Research Engine for further clarification or to the user for human input.
*   **Data Interfaces:**
    *   **Input:** Raw information from the Research & Information Acquisition Engine, existing Semantic and Episodic Memories.
    *   **Output:** Validated, structured information with associated credibility and relevance scores. This information is then ready for integration into the Memory System or direct use by the Reasoning Engine.
*   **Role in Polya Loop:** A critical component of "Understand the Problem," ensuring data quality before proceeding to planning.

### 2.5. Reasoning & Hypothesis Generator

This engine is the core of PolyaBrain's "Devise a Plan" capability, translating understanding into actionable strategies.

*   **Functionality:**
    *   **First-Principles Thinking:** Utilizes advanced LLMs (e.g., GPT-4o, Claude 3.5 Sonnet) to decompose complex problems into fundamental components and reason from basic truths rather than relying on analogies as proof.
    *   **Knowledge-Rich Analogical Transfer:** Retrieves structurally similar past cases or strategies when analogy may help, then states what transfers, what does not, and what must be decomposed into first principles and verified.
    *   **Divergent/Convergent Reasoning:** Generates multiple meaningfully different hypotheses or plans before ranking and pruning them against evidence, constraints, falsifiability, and verification cost.
    *   **Reframe/Incubation Pass:** After initial evidence gathering, runs a bounded reframe pass to surface overlooked assumptions or alternative problem constructions. Any useful reframe must return through evidence evaluation and verification.
    *   **Plan Generation:** Generates a step-by-step, executable plan to solve the problem, taking into account the formalized problem statement, validated knowledge, and available tools.
    *   **Procedural Memory Integration:** Queries the Procedural Memory (Graph Database) to retrieve relevant problem-solving strategies, algorithms, and heuristics that have proven effective in similar contexts.
    *   **Hypothesis Formulation:** For uncertain or novel situations, it generates multiple hypotheses or alternative plans, each with an associated confidence level.
    *   **Constraint Adherence:** Ensures that all generated plans strictly adhere to the constraints identified by the Problem Representation Engine.
*   **Data Interfaces:**
    *   **Input:** Formalized problem schema, validated knowledge from Evidence Evaluation, relevant strategies from Procedural Memory.
    *   **Output:** A `ProblemSolvingPlan` object, detailing sequential steps, required tools, expected intermediate outcomes, and potential alternative paths.
*   **Role in Polya Loop:** The central component of "Devise a Plan," transforming understanding into a concrete strategy.

### 2.6. Execution Engine

This engine is responsible for "Carrying Out the Plan," translating abstract steps into concrete actions within a controlled environment.

*   **Functionality:**
    *   **Code Interpretation & Execution:** Executes generated code snippets (e.g., Python for mathematical calculations, data manipulation) within secure, isolated Docker containers or Firecracker microVMs. These sandboxes provide a safe environment, preventing unintended side effects.
    *   **Tool Orchestration:** Interacts with a registry of external and internal tools (e.g., calculators, specialized APIs, data analysis libraries). It translates plan steps into specific tool calls and manages their execution.
    *   **State Management:** Maintains the execution context and intermediate results, ensuring continuity across multiple steps of a plan.
    *   **Error Handling:** Implements robust error detection and retry mechanisms, reporting execution failures back to the Orchestration Layer.
*   **Data Interfaces:**
    *   **Input:** `ProblemSolvingPlan` from the Reasoning Engine, current execution state.
    *   **Output:** Raw execution results, intermediate data, and status logs.
*   **Role in Polya Loop:** The core of "Carry Out the Plan," performing the actual work.

### 2.7. Verification Engine

PolyaBrain does not assume success; it rigorously verifies every outcome. This engine ensures that the executed plan has indeed solved the problem according to its constraints.

*   **Functionality:**
    *   **Output Validation:** Compares the raw execution results against the expected outcomes and original problem constraints. This can involve numerical checks, semantic comparisons (using LLMs), or logical assertions.
    *   **Mode-Specific Checklists:** Applies different required checks for technical research, debugging/root-cause analysis, architecture tradeoffs, data analysis, ambiguous input, and creative synthesis.
    *   **Hypothesis Testing:** For problems with multiple hypotheses, it actively generates additional test cases or searches for counter-examples to rigorously validate the chosen solution. This can involve generating adversarial inputs or edge cases.
    *   **Semantic Verification:** Utilizes LLMs to semantically evaluate the correctness and completeness of qualitative or open-ended solutions.
    *   **Failure Analysis:** If verification fails, it performs an initial analysis to pinpoint the stage of failure (e.g., incorrect plan, execution error, faulty data) and provides feedback to the Orchestration Layer, potentially triggering a replanning or re-acquisition loop.
*   **Data Interfaces:**
    *   **Input:** Raw execution results from the Execution Engine, original problem schema, generated plan, and any hypotheses.
    *   **Output:** A `VerificationReport` indicating success or failure, along with details of any discrepancies or errors.
*   **Role in Polya Loop:** The final stage of "Carry Out the Plan," ensuring solution integrity.

### 2.8. Reflection & Learning Engine

This engine embodies the "Look Back" stage, transforming individual problem-solving attempts into systemic improvements and continuous learning.

*   **Functionality:**
    *   **Root Cause Analysis:** Analyzes the entire problem-solving trace (from problem representation to verification) to understand why a solution succeeded or failed. It identifies critical decision points, effective strategies, and areas for improvement.
    *   **Strategy Evaluation:** Evaluates the effectiveness of the problem-solving strategies employed, identifying sub-optimal steps or generalizable heuristics.
    *   **Memory Updates:** Based on the reflection, it triggers updates to the Memory System:
        *   New facts or concepts are ingested into Semantic Memory.
        *   Successful problem-solving patterns and their relationships are refined or added to Procedural Memory.
        *   The complete trace of the problem-solving attempt is stored in Episodic Memory for future reference.
    *   **Reinforcement Learning (RL):** Utilizes RL techniques (e.g., PPO, SAC) to optimize decision-making policies within the Polya loop, improving the selection of strategies, query formulation, and plan generation over time.
    *   **Ethical AI Considerations:** Monitors for potential biases in problem-solving outcomes and decision-making, providing insights for bias mitigation and enhancing explainability.
*   **Data Interfaces:**
    *   **Input:** Complete problem-solving trace (problem, plan, execution results, verification report), current state of all Memory Systems.
    *   **Output:** Updated Memory Systems, refined RL policies, and `LearningInsights` for system developers.
*   **Role in Polya Loop:** The core of "Look Back," driving continuous improvement and adaptation.

### 2.9. Memory System

While detailed in a separate report, the Memory System is an integral part of the nine-engine framework, providing the foundational knowledge base for all cognitive processes. It is not a single engine but a composite of three distinct memory types, each serving a specific purpose:

*   **Semantic Memory (The "What"):** Stores factual knowledge and concepts using a Vector Database (e.g., Pinecone, Milvus). It provides the declarative knowledge base.
*   **Procedural Memory (The "How"):** Stores problem-solving strategies, algorithms, and heuristics using a Graph Database (e.g., Neo4j). It provides the operational knowledge base.
*   **Episodic Memory (The "When and Where"):** Stores the complete history of problem-solving attempts, including context, plans, and outcomes, using a Relational Database (e.g., PostgreSQL). It provides the experiential knowledge base.

These memory components are constantly accessed and updated by the other engines, forming a dynamic and evolving knowledge graph that underpins PolyaBrain's intelligence.

## 3. Orchestration and Inter-Engine Communication

The seamless interaction between these nine engines is facilitated by **LangGraph**, which serves as the core orchestration framework. LangGraph's ability to manage stateful, cyclic workflows is paramount for PolyaBrain, enabling the system to:

*   **Iterate:** If the Verification Engine flags an issue, LangGraph can intelligently route the problem state back to the Reasoning Engine for replanning, or even to the Research Engine if new information is required.
*   **Maintain Context:** The global state object within LangGraph ensures that all engines operate with the most up-to-date understanding of the problem, current progress, and accumulated knowledge.
*   **Modularity:** Each engine is implemented as a distinct node in the LangGraph, promoting clear separation of concerns, easier debugging, and independent scaling.

This orchestration ensures that PolyaBrain can dynamically adapt its problem-solving approach, moving fluidly between understanding, planning, executing, and reflecting, much like a human expert.

## 4. Conclusion

The nine-engine framework of PolyaBrain represents a robust and comprehensive architecture for achieving artificial general intelligence grounded in first-principles reasoning. By meticulously designing each engine to perform a specific cognitive function—from problem representation and dynamic knowledge acquisition to rigorous execution and continuous learning—PolyaBrain moves beyond mere pattern recognition to genuinely understand and solve complex, novel problems. This modular, reflective design, coupled with a sophisticated hybrid memory system and intelligent orchestration, positions PolyaBrain as a leading-edge system in the pursuit of truly intelligent AI.

## References

[1] George Pólya, *How to Solve It: A New Aspect of Mathematical Method*. Princeton University Press, 1945.
[2] U. Lee et al., "Llama-Polya: Instruction Tuning for Large Language Model based on Polya’s Problem-solving," arXiv:2602.10597v1 [cs.CY], Feb 11, 2026. [Online]. Available: https://arxiv.org/html/2602.10597v1
