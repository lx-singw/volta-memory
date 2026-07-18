# 17 — Comprehensive Engineering Build Roadmap
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

This document serves as the absolute, watertight execution checklist for the remainder of the hackathon build. It maps every single deliverable into a sequential, 8-Phase engineering roadmap.

> **Honest Status as of July 18, 2026:** The documentation suite (16 documents) is complete and strong. The codebase has a solid structure (13 memory modules, eval harness, 2 personas, frontend with voice/graph). However, 5 of the 6 core memory modules contain **scaffold/placeholder logic** instead of real Qwen LLM calls. The eval harness ran but Volta scored 0.0 recall because extraction doesn't actually use the LLM. Phase 0 exists to close this gap before anything else.

---

## Phase 0: Replace All Scaffolds with Real Qwen LLM Calls (THE SINGLE MOST IMPORTANT PHASE)
*Objective: Every "Scaffold — replace with Qwen call" comment in the codebase must be eliminated. Without this, the project fails the "Technical Depth" criterion regardless of everything else.*

### 0.1 Real Memory Extraction via Qwen (`extraction.py`)
- **Current state:** Hardcoded keyword matching (`if "backup" in lower`). The AI does NOT actually learn from conversations.
- **Task:** Replace with a real Qwen LLM call that receives the full conversation transcript and returns structured JSON with extracted memories (type, observation, confidence, importance score, reasoning).
- **Why this is #1:** If extraction doesn't work, nothing downstream works — decay, contradiction, consolidation all operate on memories that were never properly created.

### 0.2 Real Contradiction Detection via Qwen (`contradiction.py`)
- **Current state:** String-matching heuristic (`if "bill" in new_text`). Only catches bill-related contradictions.
- **Task:** Replace with a Qwen LLM call that compares a new observation against existing memories and determines semantic contradiction (not just keyword overlap).

### 0.3 Real Importance Scoring via Qwen (`importance.py`)
- **Current state:** `len(observation.split()) / 20.0` — literally measuring word count as a proxy for importance.
- **Task:** Replace with a Qwen LLM call that evaluates the observation in context and returns an importance score (1-10) with reasoning. This score must feed into the decay lambda calculation.

### 0.4 Real Plausibility Check via Qwen (`plausibility.py`)
- **Current state:** YAML pattern matching against a prohibited-terms list. No semantic understanding.
- **Task:** Replace with a Qwen LLM call that evaluates whether an extracted memory is plausible given the domain context (e.g., "monthly bill of R500,000" should be flagged as implausible).

### 0.5 Real Consolidation Summary via Qwen (`consolidation.py`)
- **Current state:** `"; ".join(item.observation for item in stale[:5])` — concatenates strings, doesn't semantically merge.
- **Task:** Replace with a Qwen LLM call that receives multiple stale memories and produces a single, coherent consolidated summary that preserves the essential information.

### 0.6 Wire Importance into Extraction Pipeline
- **Current state:** `importance.py` exists but `extraction.py` doesn't call it. `write_from_draft` doesn't pass importance scores.
- **Task:** After extraction, call `score_importance()` on each draft and pass the result through to `write_memory()`.

### 0.7 Fix the Eval Harness (Volta scores 0.0 recall)
- **Current state:** `BENCHMARKS.md` shows `D_volta_memory | 0.0` — the system that's supposed to win scores zero.
- **Task:** Debug why System D scores zero. Likely because scaffold extraction never creates the right memories. After fixing 0.1–0.6, re-run the eval and confirm Volta outperforms all baselines.

---

## Phase 1: Core Memory Architecture Hardening
*Objective: Make the math real and the decay model demonstrably correct.*

### 1.1 Ebbinghaus Decay Uses Importance-Adjusted Lambda
- **Current state:** `decay.py` calls `settings.lambda_for_memory_type()` but does NOT use `effective_lambda()` from `importance.py`.
- **Task:** Wire `effective_lambda()` into `apply_decay()` so importance actually modulates decay rate.

### 1.2 Stability Growth from Cross-Session Reinforcement
- **Current state:** `stability.py` exists and `retention_strength()` is called in `decay.py`, but reinforcement counting doesn't distinguish within-session vs cross-session.
- **Task:** Add a `cross_session_reinforcement_count` field. Only cross-session reinforcements increase stability (Ebbinghaus spacing effect).

### 1.3 Explicit Meta-Memory Gaps
- **Task:** Track `known_gaps` per entity — things the AI explicitly knows it doesn't know (e.g., "roof size never mentioned").
- **Details:** Surface this in the transparency UI and use it to drive proactive questions.

### 1.4 Confidence Tier Affects Generation Language
- **Current state:** `confidence_tier()` returns "high"/"medium"/"below_surface" but the system prompt doesn't use these tiers to modulate Volta's phrasing.
- **Task:** Update `volta_prompt.py` to instruct Qwen to speak with certainty for high-tier memories and hedging language for medium-tier.

---

## Phase 2: Advanced Retrieval & Security
*Objective: Handle edge cases and adversarial attacks.*

### 2.1 Hybrid Retrieval Fallback (BM25/keyword)
- **Current state:** Retrieval is vector-only (sort by decay-adjusted score). No fallback if pgvector similarity is low.
- **Task:** Add keyword-based fallback search when vector similarity is below threshold.

### 2.2 Uncertainty-Aware Clarification (`CLARIFY` dialogue state)
- **Task:** If retrieved memories conflict or have low confidence, trigger a clarification question instead of guessing.

### 2.3 Population Cold-Start Priors
- **Task:** For brand-new users, seed context with aggregated, anonymized assumptions from prior users.

---

## Phase 3: MCP Integration & Streaming
*Objective: Satisfy the judging criteria's explicit mention of "MCP integrations."*

### 3.1 MCP Server Implementation
- **Task:** Wrap the memory engine as an MCP-compliant server exposing `store_memory`, `retrieve_memory`, `supersede_memory` as tools.

### 3.2 Native Qwen Tool Calling
- **Task:** Refactor the chat endpoint to use Qwen's tool-calling API instead of prompt injection. Qwen decides when to read/write memory.

### 3.3 End-to-End Streaming (SSE)
- **Task:** Stream LLM responses to the frontend in real-time instead of waiting for the full response.

---

## Phase 4: Eval Harness & Chaos Testing
*Objective: Prove everything with measured numbers.*

### 4.1 System E: MCP Agent-Directed Baseline
- **Task:** Add a 5th eval variant that uses the MCP tool-calling path, benchmarked against the prompt-injection approach.

### 4.2 Self-Tuning Constant Search
- **Task:** Automate parameter sweep to find optimal decay constants.

### 4.3 Chaos & Failure Testing
- **Task:** Inject Qwen API timeouts, DB connection drops, and network failures. Prove graceful degradation.

### 4.4 Concurrency Isolation Stress Test
- **Task:** 100 entities chatting simultaneously with zero memory cross-contamination.

---

## Phase 5: Domain Expansion & Productization
*Objective: Prove the engine is generic infrastructure, not a solar chatbot.*

### 5.1 Second Persona End-to-End
- **Current state:** `study_coach_prompt.py` exists but extraction/contradiction logic is hardcoded to solar domain keywords.
- **Task:** After Phase 0 (real Qwen extraction), the study coach persona should work automatically. Verify and demo it.

### 5.2 Docker One-Command Reproducibility
- **Current state:** `docker-compose.yml` and `Dockerfile` exist but haven't been verified end-to-end.
- **Task:** Test `docker-compose up` from a clean environment.

### 5.3 CONTRIBUTING.md at Repo Root
- **Task:** Extract from `14_Contributing_and_Governance.md` into a proper `CONTRIBUTING.md` file.

### 5.4 Hosted Live Demo
- **Task:** Deploy to Alibaba Cloud and keep it monitored through judging.

---

## Phase 6: Academic & Community Deliverables
*Objective: Elevate from "project" to "contribution."*

### 6.1 Explainability Trace in UI
- **Current state:** `explainability.py` and `explain_traces` table exist. The backend writes traces.
- **Task:** Surface the trace in the frontend UI (show which memory influenced each response).

### 6.2 Human Evaluation Study
- **Task:** Small user study with real quotes and raw results.

### 6.3 Public Benchmark Dataset
- **Task:** License and publish the eval personas as an open benchmark.

---

## Phase 7: Final Submission Assets
*Objective: Prepare everything Devpost needs.*

### 7.1 Record the Demo Video
- **Task:** Execute `06_Demo_Script.md` on camera (~3 minutes, continuous capture).

### 7.2 Record the Alibaba Cloud Proof Video
- **Task:** 60-second screen recording showing FC3.0 dashboard + live curl request.

### 7.3 Export Architecture Diagrams
- **Task:** Render Mermaid diagrams from `15_Architecture_Diagram_Spec.md` to PNG.

### 7.4 Publish the Blog Post
- **Task:** Publish `16_Blog_Post_Draft.md` on Medium/Dev.to.

### 7.5 Complete the Devpost Form
- **Task:** All "Built With" tags, text description, video links, Track 1 selected. Submit 24+ hours early.
