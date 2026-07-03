# Volta Memory — Submission Checklist
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**
**Every hackathon requirement mapped to a concrete deliverable in this repo**

---

## Table of Contents
- [1. Repository Requirements](#1-repository-requirements)
- [2. Proof of Alibaba Cloud Deployment](#2-proof-of-alibaba-cloud-deployment)
- [3. Architecture Diagram](#3-architecture-diagram)
- [4. Demo Video](#4-demo-video)
- [5. Text Description](#5-text-description)
- [6. Track Identification](#6-track-identification)
- [7. Optional — Blog Post](#7-optional--blog-post)
- [8. Judging Criteria Self-Check](#8-judging-criteria-self-check)

---

## 1. Repository Requirements

| Requirement | Deliverable | Status |
|-------------|-------------|--------|
| Public code repository | `volta-memory` repo, public from day one | Required before submission |
| All source code, assets, instructions for functionality | Full backend + frontend per Document 02; README with setup steps | Required |
| Open source license, detectable in About section | `LICENSE` file (MIT), repo About section configured to surface it | Required — verify GitHub/GitLab renders the license badge correctly before submitting |

**Action item:** After pushing the repo, check the repository's About section on the hosting platform renders the license automatically (GitHub does this from a correctly named `LICENSE` file at root — verify, don't assume).

---

## 2. Proof of Alibaba Cloud Deployment

| Requirement | Deliverable |
|-------------|-------------|
| Short recording (separate from main demo) proving backend runs on Alibaba Cloud | A 30–60 second screen recording showing: SSH or console access to the live Alibaba ECS instance (or Function Compute dashboard), the running backend process, and a live curl/request hitting the deployed URL with a real response |
| Link to a code file demonstrating use of Alibaba Cloud services/APIs | `deployment/proof/deployment_verification.py` (Document 02, Section 6) — must actually call an Alibaba Cloud SDK method and print a real response, not a mocked one |

**Action item:** Run `deployment_verification.py` on camera during the proof recording so the API call and its real response are visible together — don't just show the file's source code.

---

## 3. Architecture Diagram

**Requirement:** Clear visual representation showing how Qwen Cloud connects to backend, database, and frontend.

**What the diagram must show, minimum:**
- Frontend (chat UI + memory transparency view) → Backend (FastAPI)
- Backend → Qwen Cloud (all inference calls — chat completion, extraction, contradiction detection)
- Backend → Postgres/Alibaba RDS (memory store, conversations, messages)
- Backend deployment target: Alibaba ECS or Function Compute
- The memory pipeline specifically: retrieval ranking → token-budget packing → prompt injection → Qwen call → response → extraction → write-back

**Source material:** Mine the box-and-arrow structure from Document 02's directory layout and Document 03's pipeline description — this diagram should visually be the same shape as the dependency graph already built for the 11-day plan, simplified to the final as-built architecture rather than the build sequence.

---

## 4. Demo Video

| Requirement | Deliverable |
|-------------|-------------|
| ~3 minutes | Document 06 script, timed at 3:00 |
| Demonstrates the submission functioning | Live screen recording, not slides — real chat interactions, real memory table updates |
| Uploaded to YouTube, Vimeo, or Facebook Video, public | Upload after final recording, confirm public visibility before linking in submission |

**Action item:** Record in one take if possible — a video assembled from many cuts risks looking staged, and the entire value of this submission is proving the mechanism is real. A single continuous capture (with the skip-ahead time jumps clearly labelled via on-screen text, per Document 06) is more convincing than a heavily edited version.

---

## 5. Text Description

**Requirement:** Explain the features and functionality of the project.

**Draft structure** (expand from Document 01's PRD Section 1 and Document 03's Section 1):

> Volta Memory is a conversational energy advisory agent built on Qwen Cloud with a genuine persistent memory system. Unlike approaches that either replay full conversation history or retrieve by semantic similarity, Volta Memory maintains a typed, confidence-scored memory store with three explicit mechanisms: a decay model that lets unreinforced memories fade gracefully over time, contradiction detection that supersedes outdated facts without destroying the audit trail, and token-budgeted retrieval ranking that ensures only the highest-value memories are ever injected into a response — never the whole history, always the right slice of it.
>
> Across three demonstrated sessions spanning a simulated three-week period, Volta visibly recalls prior context unprompted, correctly handles a user-issued correction by superseding rather than duplicating the outdated fact, and demonstrably speaks with reduced certainty about a preference that has decayed without reinforcement — proving the decay model affects not just retrieval but generation.
>
> All inference — chat completion, end-of-session memory extraction, and contradiction detection — runs on Qwen Cloud. The backend is deployed on Alibaba Cloud infrastructure, with the memory store persisted in Postgres so that history survives restarts and genuinely spans sessions, not just browser tabs.

---

## 6. Track Identification

**Submitting to:** Track 1 — MemoryAgent

**Explicit mapping to track requirements** (for the submission form's track justification, if requested):
- "Efficient memory storage and retrieval" → Document 03, Sections 3 and 6
- "Timely forgetting of outdated information" → Document 03, Section 4
- "Recalling critical memories within limited context windows" → Document 03, Section 6, token budget enforcement

---

## 7. Optional — Blog Post

**Requirement for Blog Post Prize eligibility:** Published blog or social post showing the build journey.

**Suggested angle:** Write specifically about the decay model design decision (Document 03, Section 4) — this is the most technically interesting and least obvious part of the build, since most memory-agent demos skip forgetting entirely and only show accumulation. A short post titled something like "Why your memory agent needs to forget on purpose" focused on the λ-tuned decay formula and the worked three-session example (Document 03, Section 9) would stand out from posts that only cover storage and retrieval.

---

## 8. Judging Criteria Self-Check

| Criterion | Weight | Self-assessment against this build |
|-----------|--------|-------------------------------------|
| Technical Depth & Engineering | 30% | Real decay math, real token-budget enforcement, real contradiction detection via dedicated Qwen call — not simulated. Verify before submission: every PRD acceptance criterion (Document 01, Section 4) has a corresponding passing test in `backend/tests/` |
| Innovation & AI Creativity | 30% | The decay-affects-generation-language link (Section 8 of Document 03) is the most novel piece — confidence tier visibly changes Volta's phrasing, not just an internal score. Make sure this is legible in the demo video, not just in the code |
| Problem Value & Impact | 25% | Real-world relevance: any consumer-facing advisory agent that talks to the same person more than once has this exact problem. Scalability: the typed-memory approach generalises beyond energy advice to any long-relationship agent use case — worth one sentence in the text description |
| Presentation & Documentation | 15% | This document suite plus the architecture diagram plus the worked example in Document 03 Section 9 — confirm the README links to all of it clearly, since judges reviewing quickly should never have to hunt for the core design rationale |

**Final pre-submission gate:** Every row in this table should be answerable with "yes, and here's where" before the repo is made public and the form is submitted.


---

# ADDENDUM — Maximum-Depth Deliverables Checklist
**Added: June 2026 | The hardest route, mapped to concrete gates**

---

## 9. Maximum-Depth Technical Deliverables

| Deliverable | Where specified | Gate before submission |
|-------------|-----------------|------------------------|
| Self-scored importance | Memory Design Doc §11, PRD §8.1 | Transparency view shows differentiated decay for same-type memories |
| Ebbinghaus-grounded stability | Memory Design Doc §12, PRD §8.2 | Cross-session vs within-session reinforcement produces measurably different stability |
| Hybrid retrieval fallback | Memory Design Doc §13, PRD §8.3 | Fallback correctly triggers only below similarity threshold, respects FALLBACK_BUDGET_TOKENS |
| Adversarial/poisoning defence | Memory Design Doc §15, PRD §8.4 | Adversarial persona in eval harness passes; plausibility_flag correctly suppresses confident phrasing |
| Explainability trace | Memory Design Doc §16, PRD §8.5 | Counterfactual claim in at least one demo response is verified true, not asserted |
| Consolidation cycle | Memory Design Doc §17, PRD §8.6 | Real consolidation event with token savings logged and auditable |
| Eval harness vs 3 baselines | Memory Design Doc §14, PRD §8.7 | BENCHMARKS.md has real measured numbers, not placeholders |
| Second persona, shared engine | Directory Structure §10, PRD §8.8 | Zero-diff verification across `backend/app/memory/` between personas |
| Hosted live demo | Directory Structure §11, PRD §8.9 | URL live and tested within 24 hours of judging deadline |

---

## 10. Revised Judging Criteria Self-Check (Maximum-Depth Version)

| Criterion | Weight | What now backs this score |
|-----------|--------|---------------------------|
| Technical Depth & Engineering | 30% | Eval harness with real baseline comparisons, adversarial defence with a scored test case, hybrid retrieval with a principled arbitration rule, importance-validation benchmark with measured MAE |
| Innovation & AI Creativity | 30% | Self-scored importance modulating decay lambda per-observation (not per-category), Ebbinghaus-cited stability growth with cross-session-only reinforcement counting, explainability trace with verified counterfactuals |
| Problem Value & Impact | 25% | Second persona proving the engine is reusable infrastructure, benchmarked token-efficiency and cost numbers proving production viability, consolidation cycle proving the design scales beyond a 3-session demo |
| Presentation & Documentation | 15% | BENCHMARKS.md front-and-center, supplementary deep-dive video, hosted live demo judges can test directly, full citation of Ebbinghaus/spaced-repetition grounding |

**Final pre-submission gate, maximum-depth version:** every row in Section 9's deliverables table must show real, run, measured evidence — not a designed-but-unexecuted feature. The entire strategy of this route is that competing submissions will describe intentions; this one shows numbers.


---

# ADDENDUM — Problem Value & Impact Deliverables
**Added: June 2026 | Maps Document 08 to concrete submission gates**

---

## 11. Problem Value & Impact Deliverables

| Deliverable | Where specified | Gate before submission |
|-------------|-----------------|------------------------|
| Standalone installable package | Doc 08 §2 | `pip install` works from a clean environment; zero Volta/solar-specific code in the core package |
| Third example on a different LLM provider | Doc 08 §2 | `examples/openai_customer_support/` runs end-to-end, proving `llm_backend.py` abstraction is real, not aspirational |
| Domain applicability table | Doc 08 §3 | Included in standalone README, not just this internal doc |
| Honest competitive comparison (Mem0/LangChain/MemGPT) | Doc 08 §4 | Included in standalone README — a judge who knows these frameworks should see you know them too |
| GridFreeHub production commitment | Doc 08 §6 | Stated explicitly in text description and demo video narration — this is the single strongest impact claim available and must not be buried in an internal doc only |
| CONTRIBUTING.md with 3 scoped contribution shapes | Doc 08 §7 | Present at repo root, not just described here |
| 20-line reference integration | Doc 08 §8 | Actually runs; included verbatim in standalone README as the first thing after installation instructions |

**Revised Problem Value & Impact self-assessment:** with Document 08's additions — a real installable package, proof of provider-agnosticism via a third example, an honest competitive landscape comparison, and a named real-world production adopter — this criterion now has the same standard of evidence as Technical Depth & Engineering, closing the gap identified in the original 17–19/25 estimate.

