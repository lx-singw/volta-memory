# Volta Memory — Product Requirements Document
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

---

## Table of Contents
- [1. Product Vision](#1-product-vision)
- [2. The Persona](#2-the-persona)
- [3. Core User Flow](#3-core-user-flow)
- [4. Feature Spec — Memory-Driven Behaviours](#4-feature-spec--memory-driven-behaviours)
- [5. Non-Goals](#5-non-goals)
- [6. Success Criteria](#6-success-criteria)
- [7. Technical Constraints](#7-technical-constraints)

---

## 1. Product Vision

Volta Memory demonstrates that a conversational agent can accumulate genuine, structured, decaying memory across sessions — not a long context window, not a vector-search-everything approach, but a curated, typed, confidence-weighted memory store that a small model can reason over efficiently.

The product is intentionally narrow: one persona, one domain (home solar energy advice), one demonstrable capability (cross-session intelligence that visibly improves). Narrowness is the design choice that makes the submission finishable and legible to judges in a three-minute video.

---

## 2. The Persona

**Volta** is an AI energy advisor for South African homeowners considering solar power. Volta is warm, direct, and plain-spoken — never jargon-heavy, never vague. Volta's domain knowledge covers solar system sizing, load-shedding backup planning, and basic SA electricity tariff context.

For this submission, Volta's role is narrowed specifically: Volta does not need to generate quotes, connect to installers, or handle compliance. Volta's only job is to **have an ongoing relationship with one consumer across multiple conversations** and demonstrably get better at advising them each time.

---

## 3. Core User Flow

### Session 1 — First contact
1. Consumer opens chat, no prior history exists
2. Consumer describes their situation in free text (e.g. "I want to understand solar for my house, load-shedding is killing me")
3. Volta asks 2–3 clarifying questions naturally within conversation (not a form)
4. Volta gives an initial recommendation
5. On session end, memory agent extracts and writes structured observations: stated motivations, mentioned numbers, expressed preferences

### Session 2 — Days later, new session, no shared frontend state
1. Consumer returns, starts a new conversation
2. Volta's first message proactively references what it remembers — without the consumer re-explaining anything
3. Consumer asks a follow-up or a new question
4. Volta's answer integrates old memory with new input
5. If the consumer's new statement contradicts a prior memory, the old memory is superseded, not duplicated

### Session 3 — Further later, refinement
1. Consumer asks a pricing or sizing question
2. Volta answers using the accumulated, decayed, ranked memory context — demonstrating that low-relevance old details have faded while reinforced, high-confidence details remain sharp
3. Demo concludes here

---

## 4. Feature Spec — Memory-Driven Behaviours

### 4.1 Proactive recall (not just reactive lookup)

Volta does not wait to be asked "what did we discuss before?" Every session-opening message is generated with the consumer's current memory context already injected — Volta references it unprompted, the way a good advisor would.

**Acceptance criterion:** In session 2, Volta's first message contains a specific, correct reference to information only available in session 1 — without the consumer having restated it.

### 4.2 Confidence-aware language

When Volta references a memory, the confidence score of that memory shapes how it's phrased. A confidence ≥ 0.85 memory is stated plainly ("you mentioned backup power was the real driver"). A confidence between 0.5–0.85 is phrased as a soft check ("I think backup power was a concern — still the case?"). Below 0.5, the memory is not surfaced at all.

**Acceptance criterion:** Demo includes at least one example of each confidence tier's phrasing style.

### 4.3 Contradiction handling (the forgetting requirement)

When new input contradicts an existing memory, the system does not simply append a new row and let both exist. It marks the old memory `is_superseded`, writes the new one with a fresh confidence score, and Volta's next reference uses only the corrected version.

**Acceptance criterion:** Demo includes a deliberate contradiction (e.g. consumer corrects a previously stated bill amount) and shows Volta using only the corrected figure afterward.

### 4.4 Decay of unreinforced memory

A memory observed once and never reinforced loses retrieval priority over time relative to memories that have been reinforced multiple times or are recent. This is a mathematical property of the retrieval ranking (see Document 03), not a deletion — old memories aren't destroyed, they simply stop surfacing once their relevance score drops below the retrieval threshold.

**Acceptance criterion:** A memory from session 1 that was never reinforced and is topically irrelevant to session 3's question does not appear in Volta's session 3 context — verifiable via the debug/admin view (Section 4.6).

### 4.5 Token-budgeted retrieval

Before generating any response, the system retrieves only the highest-ranked memories that fit within a defined token budget (not all memories, not a fixed row count). This is the literal "recalling critical memories within limited context windows" requirement.

**Acceptance criterion:** A configurable `MAX_MEMORY_TOKENS` constant is enforced and demonstrable — feeding the system an artificially large memory set and confirming retrieval still respects the cap.

### 4.6 Memory transparency view (debug/demo aid)

A simple read-only view (not consumer-facing in the demo, but valuable for the judging video) showing exactly what memories exist for a given consumer, their confidence scores, reinforcement counts, and superseded status. This lets the demo video visually prove the memory mechanics rather than just asserting them.

**Acceptance criterion:** This view is shown on screen at least once during the demo video, directly after a memory-driven response, to prove the mechanism isn't simulated.

---

## 5. Non-Goals

Explicitly not building for this submission:
- Multi-agent collaboration or negotiation (that's Track 3)
- Lead generation, quotes, installer matching, payments
- WhatsApp or any channel beyond a simple web chat
- Voice input
- Any UI polish beyond functional clarity
- Authentication beyond a single demo consumer identifier
- Production-scale concurrency or multi-tenant isolation

---

## 6. Success Criteria

| Criterion | Target |
|-----------|--------|
| Cross-session recall demonstrated | ✓ visible in demo video |
| Decay/forgetting demonstrated | ✓ visible via memory transparency view |
| Contradiction/supersession demonstrated | ✓ explicit scripted moment |
| Token budget enforcement | ✓ demonstrable, not just claimed |
| Runs on Qwen Cloud | ✓ all inference calls |
| Deployed on Alibaba Cloud | ✓ proof recording + linked code |
| Public repo with OSS license | ✓ visible in About section |
| Architecture diagram | ✓ included in submission |
| 3-minute demo video | ✓ scripted per Document 06 |

---

## 7. Technical Constraints

- All LLM inference calls go through Qwen Cloud — no other model provider in the critical path
- Backend must run on Alibaba Cloud infrastructure (ECS or Function Compute) — not merely deployed to a generic host
- Memory store must use a real database (Postgres via Alibaba RDS, or equivalent) — not an in-memory dict that resets on restart, since persistence across sessions is the entire point
- Token budget enforcement must use actual token counting, not a row-count proxy


---

# ADDENDUM — Maximum-Depth Feature Requirements
**Added: June 2026 | Extends Section 4's acceptance criteria with the hardest-route additions**

---

## 8. Additional Feature Spec — Maximum-Depth Behaviours

### 8.1 Self-scored importance drives decay, not fixed type defaults
**Acceptance criterion:** Two memories of the same `memory_type` demonstrably decay at different rates in the demo, with the difference attributable to different `importance_score` values and visible `importance_reasoning` text in the transparency view.

### 8.2 Ebbinghaus-grounded stability growth
**Acceptance criterion:** A memory reinforced across 3+ distinct sessions shows a measurably slower decay rate in the transparency view than a memory reinforced 3 times within a single session — proving the cross-session boundary check (Design Doc Section 12) is functioning, not just present in code.

### 8.3 Hybrid retrieval fallback fires correctly
**Acceptance criterion:** A demo query deliberately about something never explicitly extracted as a typed memory still receives a relevant (if lower-confidence, vaguely-phrased) response, with the transparency view showing the fallback embedding search was triggered and correctly bounded to its token cap.

### 8.4 Adversarial input is defended, not just handled gracefully
**Acceptance criterion:** A deliberate false-memory injection attempt in the demo (or the eval harness's adversarial persona) results in the claim being recorded but never surfaced with confident phrasing — demonstrated via the `plausibility_flag` in the transparency view.

### 8.5 Explainability trace is real, not decorative
**Acceptance criterion:** For at least one response in the demo, the `[EXPLAIN]` block's `counterfactual` field is shown to actually be true — by demonstrating the same query without that memory present and showing the response genuinely differs as predicted.

### 8.6 Consolidation cycle executes and is auditable
**Acceptance criterion:** After 5+ sessions (extendable in a longer eval run beyond the 3-session demo), the consolidation log shows a real consolidation event with token savings estimated and the original memories correctly marked superseded by the consolidated summary.

### 8.7 Benchmarked against baselines with real numbers
**Acceptance criterion:** `BENCHMARKS.md` exists at repo root, auto-generated by the eval harness, showing System D (this submission) against Systems A/B/C with real measured recall accuracy, forgetting correctness, contradiction handling rate, token efficiency, cost, and latency — not illustrative or placeholder figures.

### 8.8 Generalizes to a second persona with zero core-engine changes
**Acceptance criterion:** The study-coach persona runs against the identical `backend/app/memory/` codebase with no modifications beyond the system prompt — verified by a diff showing zero changes to any file in that directory between the two persona demos.

### 8.9 Hosted live demo remains accessible through judging
**Acceptance criterion:** Public URL live and rate-limited appropriately, verified accessible at submission time and re-verified in the days immediately before the judging deadline.

