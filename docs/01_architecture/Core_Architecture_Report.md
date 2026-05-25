# PolyaBrain: Core Architecture Report

> Source-of-truth note: this document explains architecture concepts. If it disagrees with `../../PolyaBrain_Product_Implementation_Master_Plan.md`, follow the master plan.

**Author:** Manus AI
**Date:** May 25, 2026

## 1. Introduction

PolyaBrain represents a paradigm shift in artificial intelligence, moving away from systems that rely solely on massive parameter counts and memorization. Inspired by the problem-solving methodology of mathematician George Pólya, PolyaBrain is designed as a "real intelligence" system [1]. Its core objective is to understand novel problems, reason from first principles, dynamically acquire missing information, and rigorously verify its solutions.

This report details the core architecture of PolyaBrain, explaining the nine interconnected engines that drive its cognitive processes, the hybrid memory system that supports continuous learning, and the orchestration framework that binds them together.

## 2. The Nine-Engine Architecture

The PolyaBrain architecture operationalizes Pólya's four stages—Understand the Problem, Devise a Plan, Carry Out the Plan, and Look Back—into a robust, modular system composed of nine distinct engines [2].

### 2.1. Problem Representation Engine
The first step in solving any problem is understanding it. The Problem Representation Engine is responsible for parsing raw user input (text, equations, or logical statements) and structuring it into a computable format.
*   **Functionality:** It utilizes advanced NLP pipelines and LLM-based semantic parsing to extract key entities, relationships, initial conditions, and, most importantly, the explicit and implicit constraints of the problem.
*   **Output:** A formalized JSON schema representing the problem's parameters, which serves as the foundational input for all subsequent engines.

### 2.2. Knowledge Gap Detector
Unlike traditional LLMs that attempt to answer based solely on pre-trained weights, PolyaBrain explicitly acknowledges what it does not know.
*   **Functionality:** This engine compares the formalized problem representation against the system's current knowledge state (housed in Semantic and Episodic memory). It uses vector similarity search and graph traversal to identify missing facts, unknown concepts, or unfamiliar procedures required to solve the problem.
*   **Output:** A prioritized list of specific knowledge gaps that must be filled before a reliable plan can be devised.

### 2.3. Research & Information Acquisition Engine
Once knowledge gaps are identified, PolyaBrain actively seeks the missing information.
*   **Functionality:** This engine dynamically formulates optimized search queries based on the identified gaps. It interacts with external search APIs (e.g., Tavily, SerpAPI) and utilizes robust web scrapers to extract relevant textual content from the internet, bypassing boilerplate and irrelevant data.
*   **Output:** Raw, unstructured information retrieved from external sources, targeted specifically at the identified knowledge gaps.

### 2.4. Evidence Evaluation Engine
Information retrieved from the internet is inherently noisy and potentially unreliable. This engine acts as a critical filter.
*   **Functionality:** It rigorously assesses the credibility of sources using predefined heuristics (e.g., domain authority, presence of citations). Furthermore, it cross-references newly acquired data with existing knowledge to detect contradictions and scores the relevance of the information to the original problem.
*   **Output:** Validated, structured information with assigned confidence scores, ready to be integrated into the reasoning process.

### 2.5. Reasoning & Hypothesis Generator
This engine embodies the "Devise a Plan" stage of Pólya's method.
*   **Functionality:** Utilizing advanced LLMs (such as GPT-4o or Claude 3.5 Sonnet) and constraint logic programming, this engine applies first-principles thinking to generate potential solution paths. It breaks down complex problems into manageable sub-tasks and formulates hypotheses on how to achieve the desired outcome, drawing heavily on Procedural Memory for proven strategies.
*   **Output:** A step-by-step, executable plan.

### 2.6. Execution Engine
The Execution Engine is responsible for "Carrying Out the Plan."
*   **Functionality:** It translates the generated plan into actionable steps. This includes executing generated code (e.g., Python scripts for mathematical calculations or data processing) within secure, isolated Dockerized sandboxes or firecracker microVMs. It also manages interactions with external tool registries (e.g., calculators, specialized APIs).
*   **Output:** The raw results of the executed plan, including intermediate states and final computational outputs.

### 2.7. Verification Engine
PolyaBrain does not blindly trust its own execution. The Verification Engine ensures the output is correct and aligns with the original problem.
*   **Functionality:** It automatically tests the execution output against the constraints identified by the Problem Representation Engine. It employs LLM-based semantic verification for qualitative answers and generates additional test cases or searches for counter-examples to rigorously validate hypotheses.
*   **Output:** A verified solution, or a failure signal that triggers a replanning loop.

### 2.8. Reflection & Learning Engine
The "Look Back" stage is critical for continuous improvement.
*   **Functionality:** After a problem-solving attempt (successful or not), this engine conducts a root cause analysis. It evaluates the effectiveness of the strategy used, identifies sub-optimal steps, and determines if the solution path can be generalized. It utilizes Reinforcement Learning (RL) techniques to optimize future decision-making within the Polya loop.
*   **Output:** Actionable insights and updated policy weights that are fed into the Memory System.

### 2.9. Memory System
The Memory System is the foundation that supports the entire architecture, providing context, history, and procedural guidance. (Detailed in Section 3).

## 3. The Hybrid Memory Hierarchy

PolyaBrain operates on the principle that memory supports reasoning, but memory is not intelligence itself. To achieve this, it employs a hybrid memory architecture divided into three distinct categories:

### 3.1. Semantic Memory (The "What")
*   **Purpose:** Stores factual knowledge, concepts, and definitions.
*   **Technology:** Implemented using a high-performance Vector Database (e.g., Pinecone or Milvus).
*   **Mechanism:** Facts are stored as high-dimensional embeddings, allowing the Knowledge Gap Detector to perform rapid similarity searches to determine if a required piece of information is already known.

### 3.2. Procedural Memory (The "How")
*   **Purpose:** Stores problem-solving strategies, algorithms, heuristics, and methods.
*   **Technology:** Implemented using a Graph Database (e.g., Neo4j).
*   **Mechanism:** This memory maps the relationships between specific types of problems and the strategies that have successfully solved them in the past. The Reasoning Engine queries this graph to find applicable methods when devising a plan.

### 3.3. Episodic Memory (The "When and Where")
*   **Purpose:** Preserves the complete history of past problem-solving traces, including the problem statement, the plan devised, the execution steps, and the final reflection.
*   **Technology:** Implemented using a robust Relational Database (e.g., PostgreSQL).
*   **Mechanism:** This provides the system with a historical context. By reviewing past episodes, PolyaBrain can avoid repeating mistakes and recognize structural similarities between new problems and previously solved ones.

## 4. Orchestration and the Polya Loop

The true power of PolyaBrain lies not just in its individual engines, but in how they are orchestrated. The system utilizes **LangGraph** as its core orchestration framework.

LangGraph was selected specifically for its ability to manage stateful, multi-agent, cyclic workflows. Unlike linear pipelines, problem-solving is inherently iterative. If the Verification Engine detects a failure, LangGraph routes the state back to the Reasoning Engine to devise a new plan, or back to the Research Engine if more information is needed. This cyclic graph structure perfectly models the iterative nature of human problem-solving and Pólya's methodology.

## 5. Conclusion

The PolyaBrain architecture represents a comprehensive approach to building artificial general intelligence focused on reasoning rather than mere pattern matching. By explicitly separating the concerns of problem representation, knowledge acquisition, execution, and reflection into dedicated engines, and supporting them with a structured, hybrid memory system, PolyaBrain is designed to tackle novel, unseen problems with the rigor of a human expert.

## References

[1] George Pólya, *How to Solve It: A New Aspect of Mathematical Method*. Princeton University Press, 1945.
[2] U. Lee et al., "Llama-Polya: Instruction Tuning for Large Language Model based on Polya’s Problem-solving," arXiv:2602.10597v1 [cs.CY], Feb 11, 2026. [Online]. Available: https://arxiv.org/html/2602.10597v1
