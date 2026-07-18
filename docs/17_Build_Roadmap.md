# 17 — Engineering Build Roadmap
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

This document outlines the concrete, step-by-step engineering sequence required to bring the current codebase up to parity with the Maximum-Depth Deliverables specified in `07_Submission_Checklist.md`.

---

## Build 1: Core Memory Math & Logic
*Objective: Transform the basic CRUD memory store into a dynamic, self-managing cognitive system.*

### 1.1 Ebbinghaus Decay & Stability Math
- **Task:** Implement the `decay_lambda` calculation in the PostgreSQL queries or FastAPI retrieval logic.
- **Details:** Memories should naturally decay in confidence over time if not reinforced. Reinforcements (e.g., the user repeating a fact) should increase the stability of the memory, slowing its future decay rate according to Ebbinghaus forgetting curve principles.

### 1.2 Self-Scored Importance
- **Task:** Update the Qwen extraction prompt.
- **Details:** When the LLM extracts a memory from a conversation, it must explicitly score its perceived importance (e.g., 1-10). This importance score will be used to initialize the `decay_lambda` (high importance = slower decay).

### 1.3 Background Consolidation Cycle
- **Task:** Implement a cron-like background task in FastAPI or as a separate worker.
- **Details:** Periodically scan the database for highly similar memories (using `pgvector` distance). If multiple memories assert the same fact, merge them into a single, highly stable memory to save token budget. If they contradict, flag them for the LLM to resolve during the next user interaction.

---

## Build 2: MCP Integration & Qwen Tool Calling
*Objective: Upgrade the architecture to industry-standard agent protocols and reduce token usage.*

### 2.1 Model Context Protocol (MCP) Server
- **Task:** Wrap the existing FastAPI memory endpoints into a fully compliant MCP Server.
- **Details:** Expose tools like `store_memory`, `retrieve_relevant_memory`, and `supersede_memory`. This makes the engine usable by any MCP-compliant client, drastically increasing the "Problem Value & Impact" score.

### 2.2 Native Qwen Tool Calling
- **Task:** Refactor the main chat endpoint.
- **Details:** Instead of using brute-force prompt injection (where we dump all retrieved memories into the system prompt), we will provide Qwen with the MCP tools. Qwen will intelligently decide *when* to search its memory and *what* to store at the end of the turn.

### 2.3 End-to-End Streaming
- **Task:** Implement Server-Sent Events (SSE) or WebSockets.
- **Details:** Stream the LLM response directly to the Next.js frontend to provide a snappy, premium user experience. The frontend UI must update the chat text in real-time.

---

## Build 3: Testing, Benchmarking & Reproducibility
*Objective: Provide the undeniable, measured proof required to win 1st place.*

### 3.1 One-Command Reproducibility
- **Task:** Create a `docker-compose.yml` and `Dockerfile`.
- **Details:** Package the FastAPI backend, the Next.js frontend, and a local PostgreSQL+pgvector instance so judges can run the entire stack locally with a single `docker-compose up -d`.

### 3.2 The Eval Harness
- **Task:** Build `backend/tests/eval_harness.py`.
- **Details:** A script that programmatically runs synthetic conversations through the engine and measures:
  - Token efficiency (Prompt Injection vs. MCP Tool Calling).
  - Retrieval accuracy (Did it fetch the right memory?).
  - Decay correctness (Did the irrelevant memory fade?).

### 3.3 Populate BENCHMARKS.md
- **Task:** Run the eval harness and document the results.
- **Details:** This provides the hard numbers that prove the architecture's efficiency, satisfying the "Technical Depth" requirement with evidence rather than claims.
