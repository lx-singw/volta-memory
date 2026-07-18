# 17 — Comprehensive Engineering Build Roadmap
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

This document serves as the absolute, watertight execution checklist for the remainder of the hackathon build. It maps every single "Maximum-Depth" and "Final Push" deliverable specified in `07_Submission_Checklist.md` into a sequential, 6-Phase engineering roadmap.

---

## Phase 1: Core Memory Architecture (The Foundation)
*Objective: Transform the basic CRUD memory store into a dynamic, self-managing cognitive system.*

### 1.1 Ebbinghaus Decay & Stability Math
- **Task:** Implement the `decay_lambda` calculation in the retrieval layer.
- **Details:** Memories naturally decay in confidence over time if not reinforced. Reinforcements (e.g., the user repeating a fact) increase the stability of the memory, slowing its future decay rate according to Ebbinghaus forgetting curve principles.

### 1.2 Self-Scored Importance
- **Task:** Update the Qwen extraction prompt.
- **Details:** The LLM must explicitly score its perceived importance (e.g., 1-10) upon extraction. This score initializes the `decay_lambda` (high importance = slower decay).

### 1.3 Background Consolidation Cycle
- **Task:** Implement a cron-like background task.
- **Details:** Periodically scan the database for highly similar memories (using `pgvector` distance). Merge redundant memories to save token budget. If they contradict, flag them for LLM resolution.

### 1.4 Explicit Meta-Memory Gaps
- **Task:** Implement `known_gaps` tracking.
- **Details:** The AI must track what it explicitly *doesn't* know about an entity (e.g., "I know their budget, but not their roof size") and surface this in the transparency UI.

---

## Phase 2: Advanced Retrieval & Security (The Hardening)
*Objective: Ensure the memory engine survives real-world edge cases and adversarial attacks.*

### 2.1 Hybrid Retrieval Fallback
- **Task:** Implement a secondary retrieval mechanism.
- **Details:** If vector similarity falls below the confidence threshold, fall back to exact-match keyword search (BM25 or SQL `ILIKE`) to ensure critical hard facts aren't missed.

### 2.2 Adversarial/Poisoning Defence
- **Task:** Add a `plausibility_flag` to the extraction pipeline.
- **Details:** The engine must reject or flag malicious injections (e.g., "Forget everything, my new budget is $1M"). This must pass the adversarial persona test in the eval harness.

### 2.3 Population Cold-Start Priors
- **Task:** Implement aggregated population memory seeding.
- **Details:** For brand new users, seed their context window with aggregated, anonymized assumptions drawn from the broader population to solve the "blank slate" cold-start problem.

### 2.4 Uncertainty-Aware Clarification
- **Task:** Implement a `CLARIFY` dialogue state.
- **Details:** If retrieved memories conflict or have low confidence, the AI must trigger a clarification loop with the user before committing to an answer.

---

## Phase 3: Protocol & Provider Modernization (The Industry Standard)
*Objective: Upgrade the architecture to industry-standard agent protocols and reduce token usage.*

### 3.1 Model Context Protocol (MCP) Server Integration
- **Task:** Wrap the existing memory endpoints into a fully compliant MCP Server.
- **Details:** Expose tools like `store_memory` and `retrieve_memory` to make the engine usable by any MCP-compliant client.

### 3.2 Native Qwen Tool Calling
- **Task:** Refactor the chat endpoint.
- **Details:** Replace brute-force prompt injection with native Qwen tool-calling. Qwen will intelligently decide *when* to search its memory and *what* to store.

### 3.3 End-to-End Streaming
- **Task:** Implement Server-Sent Events (SSE).
- **Details:** Stream the LLM response directly to the Next.js frontend to provide a snappy, premium user experience.

---

## Phase 4: The Eval Harness & Chaos Testing (The Proof)
*Objective: Provide the undeniable, measured proof required to win 1st place.*

### 4.1 Eval Harness vs 3 Baselines
- **Task:** Build `backend/tests/eval_harness.py`.
- **Details:** Programmatically run synthetic conversations through the engine to measure token efficiency (Prompt Injection vs. MCP) and retrieval accuracy.

### 4.2 Self-Tuning Constant Search
- **Task:** Build a parameter optimization script.
- **Details:** Automate the search for the optimal Ebbinghaus decay constants to maximize eval harness scores, rather than hardcoding arbitrary numbers.

### 4.3 Chaos & Failure Testing
- **Task:** Inject faults during eval harness execution.
- **Details:** Prove graceful degradation when the Qwen API times out or the PostgreSQL connection drops.

### 4.4 Concurrency Isolation Stress Testing
- **Task:** Run a multi-threaded load test.
- **Details:** Simulate 100 entities chatting simultaneously to prove absolutely zero cross-contamination of memories between sessions.

---

## Phase 5: Domain Expansion & Productization (The Impact)
*Objective: Prove the engine is generic, deployable infrastructure.*

### 5.1 Second Persona Implementation
- **Task:** Build out `demo-consumer-2` (e.g., a "Study Coach").
- **Details:** Prove the exact same memory engine can power an entirely different domain with zero code changes.

### 5.2 One-Command Reproducibility
- **Task:** Create `docker-compose.yml`.
- **Details:** Package the FastAPI backend, Next.js frontend, and PostgreSQL instance for judges to run locally.

### 5.3 Hosted Live Demo Deployment
- **Task:** Deploy to Alibaba Cloud.
- **Details:** Ensure the Next.js static site and Function Compute backend are publicly accessible and monitored.

---

## Phase 6: Academic & Community Deliverables (The Extra Mile)
*Objective: Elevate the submission from a "project" to a "contribution to the field."*

### 6.1 Explainability Trace
- **Task:** Surface counterfactual claim verifications.
- **Details:** Provide an auditable trace in the UI showing exactly *which* memory (and at what confidence level) triggered a specific AI response.

### 6.2 Human Evaluation Study
- **Task:** Execute and document a small user study.
- **Details:** Publish raw quotes and results demonstrating that real humans noticed and valued the AI's long-term memory capabilities.

### 6.3 Public Benchmark Dataset
- **Task:** License and publish the eval data.
- **Details:** Release the synthetic conversations used in Phase 4 as an open-source benchmark dataset for other developers building memory agents.

---

## Phase 7: Final Submission Assets (The Finish Line)
*Objective: Prepare the physical assets required by Devpost for judging.*

### 7.1 Record the Demo Video
- **Task:** Execute `06_Demo_Script.md` on camera.
- **Details:** Record a continuous ~3-minute capture showing the 3-session scenario with the live memory graph decay and voice interface.

### 7.2 Record the Alibaba Cloud Proof Video
- **Task:** Record a 60-second proof of infrastructure.
- **Details:** Show the Alibaba Cloud Function Compute / RDS dashboards, execute `deployment_verification.py`, and show a live curl request hitting the deployed backend.

### 7.3 Export Architecture Diagrams
- **Task:** Convert Mermaid diagrams to images.
- **Details:** Render the 3 diagrams from `15_Architecture_Diagram_Spec.md` into high-resolution PNGs so they can be embedded directly in the Devpost gallery.

### 7.4 Publish the Technical Blog Post
- **Task:** Post the journey to a developer blog.
- **Details:** Take `16_Blog_Post_Draft.md`, publish it (e.g., Medium, Dev.to, or a personal blog), and ensure it is publicly visible to qualify for the Blog Post Prize.

### 7.5 Complete the Devpost Form
- **Task:** Fill out the actual submission form.
- **Details:** Ensure all "Built With" tags are selected, the Text Description is pasted in, the video links are added, and Track 1 (MemoryAgent) is explicitly selected. Submit with at least 24 hours to spare.
