# Volta Memory — Memory System Design
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**
**This document is the core technical deliverable judges will scrutinise most closely.**

---

## Table of Contents
- [1. Design Philosophy](#1-design-philosophy)
- [2. Memory Taxonomy](#2-memory-taxonomy)
- [3. Storage Model](#3-storage-model)
- [4. Decay Model — Timely Forgetting](#4-decay-model--timely-forgetting)
- [5. Contradiction Detection & Supersession](#5-contradiction-detection--supersession)
- [6. Retrieval Ranking — Limited Context Windows](#6-retrieval-ranking--limited-context-windows)
- [7. Extraction — Writing Memory from Conversation](#7-extraction--writing-memory-from-conversation)
- [8. Confidence-Aware Generation](#8-confidence-aware-generation)
- [9. Worked Example — The Three-Session Walkthrough](#9-worked-example--the-three-session-walkthrough)
- [10. Why This Approach Over Alternatives](#10-why-this-approach-over-alternatives)

---

## 1. Design Philosophy

Three competing approaches exist for giving an agent memory: (a) stuff the entire conversation history into context every time, (b) embed everything into a vector store and retrieve by semantic similarity, or (c) maintain a curated, typed, structured memory store that the agent actively writes to and reads from with explicit confidence and decay.

This submission deliberately builds (c). Approach (a) doesn't scale and doesn't forget. Approach (b) retrieves by similarity, not by importance — a frequently-mentioned trivial detail can outrank a rarely-mentioned critical one. Approach (c) is harder to build but is what the track is actually asking for: "efficient storage and retrieval," "timely forgetting," and "recalling critical memories" are all properties of a curated store, not a similarity search.

---

## 2. Memory Taxonomy

Every memory is typed. The type determines its decay rate and how it's surfaced.

| Type | Description | Decay speed | Example |
|------|-------------|------------|---------|
| `preference` | A stated or inferred stable preference | Slow | "Prioritises backup duration over cost savings" |
| `fact` | An objective, stated piece of information | Slow | "Lives in a 3-bedroom freehold home in Sandton" |
| `outcome` | The result of a specific past interaction | Fast | "Was given a system size estimate in session 1" |
| `correction` | An explicit user correction of a prior memory | N/A — always confidence 0.95+, never decays below surface threshold for 14 days | "Corrected bill amount from R3,200 to R3,800" |

This typed structure is what lets the decay model apply different half-lives to different content — a stable preference about what matters to someone shouldn't fade at the same rate as the fact that they were quoted a specific number three weeks ago.

---

## 3. Storage Model

Each memory is a single row: an entity it belongs to, a type, the observation itself in plain text (kept genuinely plain-language, not a structured object — this keeps injection into the system prompt simple and keeps the memory human-auditable in the transparency view), a confidence score, a reinforcement count, and timestamps.

Critically, memories are never overwritten in place. A correction creates a new row and flags the old one superseded. This means the full history is always reconstructable — useful for debugging during the build, and arguably the right design even outside a hackathon context, since you never want a memory system where a bad write silently destroys the only record of what was previously believed.

Full SQL schema is in Document 04.

---

## 4. Decay Model — Timely Forgetting

This is the component that did not exist in any prior version of this concept and was built specifically because the track requires it explicitly.

**The decay function:**

```
effective_confidence = base_confidence × exp(-λ × days_since_last_reinforced)
```

Where λ (lambda) is type-specific:
- `preference`: λ = 0.01 — a preference observed once still carries meaningful weight after a month
- `fact`: λ = 0.01 — facts about someone's situation are similarly durable
- `outcome`: λ = 0.05 — the fact that a specific number was mentioned in a specific session fades faster, since outcomes are about what happened, not what's true about the person
- `correction`: held at a 14-day floor above the surface threshold regardless of decay — a correction should not silently fade away and let the wrong original memory's lingering weight cause confusion

**Reinforcement resets the clock, not just the confidence.** Every time a memory is reinforced (the same or a closely related observation recurs), `last_reinforced_at` updates to now and `reinforcement_count` increments. This means a preference mentioned once three months ago and never again has genuinely decayed by the time of a new session — but a preference mentioned in three separate sessions stays sharp indefinitely, because each mention resets its clock.

**Forgetting is not deletion.** The decayed memory still exists in storage — its `effective_confidence` simply drops below the surface threshold (Section 6) and it stops being retrieved. This is closer to how human memory actually behaves (the memory exists, you'd recognise it if reminded, but it doesn't spontaneously surface) and it keeps the system auditable: nothing is ever silently destroyed.

---

## 5. Contradiction Detection & Supersession

When new conversational input arrives, before writing a fresh memory the extraction step checks it against existing high-confidence memories of the same type for the same entity. This check is a single, cheap Qwen call: "Does this new statement contradict any of these existing facts? Answer with the specific memory ID if yes, or 'none' if no."

If a contradiction is detected:
1. The old memory is flagged `is_superseded = true`
2. A new memory is written with `memory_type='correction'`, confidence starting at 0.95 (corrections from the source are treated as highly reliable — the person is telling you about their own situation)
3. The new memory references the superseded memory's ID for full auditability

The retrieval layer (Section 6) excludes all `is_superseded = true` rows unconditionally — there is no code path where a superseded memory can leak into a generated response.

---

## 6. Retrieval Ranking — Limited Context Windows

Before every response, the system computes a ranked, budget-capped memory set:

```
score(memory) = effective_confidence(memory) × log(1 + reinforcement_count) × recency_weight(memory)
```

`recency_weight` gives a mild additional boost to memories reinforced very recently, on top of what the decay function already does — this handles the case where someone has just told Volta something in the current session that hasn't had time to accumulate reinforcement_count but should still outrank older, more-reinforced but topically stale memories.

**The token budget enforcement is real, not approximate.** The packing function sorts by score descending, then greedily adds memories to the context one at a time, calling the actual Qwen tokenizer on each candidate and stopping the moment the running total would exceed `MAX_MEMORY_TOKENS`. This is the literal mechanism the track is asking for: "recalling critical memories within limited context windows" means the system has to actually choose what fits, not just hope everything does.

**Surface threshold.** Regardless of token budget, any memory whose `effective_confidence` has decayed below 0.5 is excluded from ranking entirely before the packing step runs — a sufficiently decayed memory doesn't even compete for the budget, on the reasoning that a half-forgotten detail shouldn't occupy space that a sharp, relevant one could use.

---

## 7. Extraction — Writing Memory from Conversation

At the end of each session (an explicit "end session" action in the demo, simulating what would be an idle-timeout in production), the full transcript is passed to a single Qwen call with a structured extraction prompt: "Given this conversation, list anything that should be remembered about this person for future conversations, each tagged as preference, fact, or outcome, with your confidence in the observation."

This produces a list of memory drafts. Each draft is checked against existing memory for contradiction (Section 5) before being written. This keeps memory-writing as a single batched operation per session rather than a continuous stream-of-consciousness write during the conversation — simpler to reason about, cheaper on tokens, and it matches how the demo script needs sessions to have a clean boundary.

---

## 8. Confidence-Aware Generation

When the system prompt is built for a new message (`volta_prompt.py`), each retrieved memory is annotated with its confidence tier, and the prompt instructs Volta to phrase references accordingly:

- **High (≥0.85):** State plainly. "You mentioned backup power was the real driver."
- **Medium (0.5–0.85):** Soft-check. "I think backup power was a concern — still the case?"
- **Below 0.5:** Already excluded at retrieval — never reaches the prompt.

This matters for the demo because it makes the memory system's internal confidence visible in natural language, rather than requiring a judge to trust an invisible number — the way Volta phrases something is itself evidence of what the system believes and how strongly.

---

## 9. Worked Example — The Three-Session Walkthrough

**Session 1.** Consumer mentions backup power matters most, in passing, alongside a stated bill of R3,200. Extraction writes: `preference, "backup power is primary motivation", confidence=0.75` and `fact, "monthly bill is R3,200", confidence=0.80`.

**Session 2 (3 days later).** Retrieval ranks both memories — neither has decayed meaningfully in 3 days. Volta opens with a plain reference to backup power (confidence ≥0.85 territory after the natural reinforcement nudge from being clearly stated). Consumer then corrects: "actually my bill's gone up, it's more like R3,800 now." Contradiction detection fires, supersedes the R3,200 fact, writes a new `correction` memory at confidence 0.95.

**Session 3 (3 weeks later).** The backup-power preference, never reinforced again, has decayed somewhat from its 0.75 base but — being a `preference` type with slow λ — still sits above the medium confidence band, so Volta soft-checks it rather than stating it plainly: "I think backup power was the main concern — still the case?" The bill correction, being type `correction` with its 14-day floor (now expired, so back to normal `fact`-equivalent decay), has decayed somewhat too — but supersession means R3,200 is never reachable again regardless. The retrieval set for this session's question about pricing is packed within token budget, prioritising the bill fact (directly relevant to a pricing question) over the backup preference (topically present but lower-scoring for this specific query).

This walkthrough is what the demo video shows on screen, narrated against the memory transparency view.

---

## 10. Why This Approach Over Alternatives

**Versus full-context-window approach:** Doesn't scale past a handful of sessions, and critically, doesn't forget — every past detail carries equal weight forever, which is the opposite of what good advice requires.

**Versus pure vector/embedding retrieval:** Retrieves by similarity to the current query, not by importance or confidence. A throwaway detail mentioned five times in casual conversation could outrank a critical preference mentioned once with high confidence. The typed, confidence-scored approach here is closer to how a competent human advisor actually remembers a client — not everything equally, but the important things durably and the trivial things not at all.

**Versus no decay at all (permanent accumulation):** Without decay, every session's context grows monotonically and eventually either blows the token budget or requires arbitrary truncation. Decay is what makes the system stable indefinitely — old, unreinforced, low-relevance memories age out gracefully rather than requiring a hard cutoff.


---

# ADDENDUM — Maximum-Depth Upgrades: Self-Scored Importance, Ebbinghaus Decay, Hybrid Retrieval, Consolidation, Adversarial Defence, Explainability
**Added: June 2026 | Taking the hardest technically correct route, not the simplest buildable one**

---

## 11. Self-Scored Memory Importance (Replaces Fixed Type-Based Confidence)

### 11.1 Why Fixed-Type Confidence Is the Easy, Wrong Answer

The original design (Section 4) assigns a fixed decay rate λ per `memory_type` — all preferences decay at the same rate, all outcomes at another. This is defensible but crude: it assumes every preference is equally important and every outcome equally disposable, which is false. A preference stated with visible emotional weight ("I really can't deal with another outage during exam season") is not the same durability class as a preference stated flatly ("I guess backup matters"). Fixed-type decay cannot distinguish these.

### 11.2 The Harder, Correct Design

At extraction time (Section 7), the Qwen extraction call is upgraded from a simple typed list into a **dual-output judgment**: for every observation extracted, the model also outputs an `importance_score` (0–1) reasoned from the conversational context — not a template default.

```
Extraction prompt (revised):

Given this conversation, list what should be remembered, each with:
- observation (plain text)
- memory_type (preference | fact | outcome | correction)
- importance_score (0.0–1.0): how consequential is this for future advice quality?
  Consider: emotional weight in how it was stated, how specific/actionable it is,
  whether the person is likely to reference it again, and whether forgetting it
  would produce a worse recommendation next time.
- importance_reasoning (one sentence: WHY this score, citing something specific 
  in the conversation — not a generic justification)
```

`importance_score` is not stored as a duplicate of `base_confidence`. It becomes a **direct multiplier on the decay lambda itself**, not on the confidence value:

```
effective_lambda(memory) = base_lambda[memory_type] × (1.4 - importance_score)
```

A high-importance memory (0.9) gets `effective_lambda × 0.5` — decays at half the type's normal rate. A low-importance memory (0.2) gets `effective_lambda × 1.2` — decays faster than the type default. This means the system is self-calibrating per-observation, not just per-category — a categorically "minor" outcome-type memory that Qwen judges highly consequential can outlive a categorically "major" preference-type memory that was stated in passing.

**This requires the `importance_reasoning` string to be stored and surfaced in the transparency view** (Section 6's retrieval debug endpoint, extended in the API addendum below) — the whole point of the harder route is that the system's self-judgment is auditable, not a black box. A judge should be able to read exactly why the model thought something mattered.

### 11.3 Validation Against Human Judgment

Because self-scored importance introduces model-judgment risk (the model could be systematically over- or under-confident), the eval harness (Section 14) includes a specific benchmark: a labeled set of 40 synthetic conversation turns with human-assigned importance scores, compared against Qwen's self-assigned scores via mean absolute error. This number is reported in the benchmarks results and is itself evidence of engineering rigor — most submissions will not think to validate their own model's self-assessment against ground truth.

---

## 12. Ebbinghaus-Grounded Decay Curve

### 12.1 Why Exponential Decay Alone Is Insufficient

The original decay formula (Section 4) is a bare exponential: `confidence × exp(-λ × days)`. This is mathematically convenient but has no grounding — it assumes forgetting is a smooth, memoryless process, which is not how retention actually behaves under reinforcement.

### 12.2 The Harder, Correct Model

Hermann Ebbinghaus's empirical forgetting curve research (and its modern formalization in spaced-repetition literature — the same mathematics underlying SM-2/Anki-style scheduling) demonstrates that retention strength after reinforcement follows a power-law-modulated exponential, where **each successive reinforcement increases the retention half-life multiplicatively**, not additively. The correct implementation:

```
retention_strength(memory, t) = base_confidence × exp(-t / S)

where S (stability) grows with each reinforcement:
S_n = S_0 × (growth_factor) ^ reinforcement_count

growth_factor is importance-modulated (Section 11):
growth_factor = 1.5 + (importance_score × 1.0)   # range 1.5–2.5
```

This means a memory reinforced once has a short stability window; reinforced five times, its stability window has grown geometrically, not linearly — matching the actual empirical shape of human spaced-reinforcement retention, and correctly modeling why a preference mentioned in three separate sessions should be dramatically more durable than the same preference mentioned three times within one session's rambling (reinforcement across session boundaries should count more than within-session repetition — implement this as a boundary check: reinforcements are only counted toward `reinforcement_count` if they occur in a distinct `conversation_id` from the memory's most recent reinforcement).

**Citation requirement for the submission write-up:** This is the single detail most likely to visibly separate this submission from competitors — explicitly cite Ebbinghaus (1885) and the SM-2 spaced-repetition formalization in the README and the demo video narration. A judge with any ML or cognitive-science background will recognize this is a deliberately researched design decision, not an arbitrary formula.

---

## 13. Hybrid Retrieval — Typed Store with Embedding Fallback

### 13.1 The Gap in a Pure Typed-Memory System

A purely typed, extraction-based memory system has one structural weakness: it can only recall what the extraction step explicitly identified as worth remembering. If a consumer mentions something offhand that the extraction call didn't judge important enough to write as a discrete memory, that detail is genuinely gone — there is no raw-text fallback.

### 13.2 The Harder, Correct Design

Every conversation's full transcript is additionally embedded (via a Qwen embedding endpoint) and stored in a vector index, **in parallel** to the typed extraction — not instead of it. Retrieval becomes a two-stage process:

```
1. Primary retrieval: typed memory store, ranked and packed to 
   TYPED_BUDGET_TOKENS (Section 6) — this remains the primary, 
   preferred source, since it is curated and decay-aware
   
2. Gap-fill retrieval: if the current query's semantic embedding has 
   low maximum cosine similarity (< 0.6) against all currently-packed 
   typed memories, this signals the query is about something the typed 
   store may not have captured — trigger a secondary embedding search 
   over raw transcript chunks, budgeted to a SMALL remaining token 
   allowance (FALLBACK_BUDGET_TOKENS, deliberately capped low — e.g. 
   150 tokens — so the fallback can supply a fragment of raw context 
   but cannot dominate the prompt)

3. Fallback results are visually and structurally distinguished in the 
   system prompt from typed memories — Volta is instructed to treat 
   fallback context as "something you might recall vaguely" rather than 
   a confident fact, mirroring the confidence-tier phrasing rule 
   (Section 8) even for content that never went through the typed 
   confidence pipeline at all
```

This is deliberately the harder engineering path — maintaining two retrieval systems and a principled arbitration rule between them — rather than the simple route of picking one paradigm. The payoff: the system gets the auditability and decay-correctness of typed memory as the default, with embedding search as a rigorously bounded safety net rather than the primary mechanism (which is the naive, common approach most competing submissions will take).

---

## 14. Eval Harness — Quantified Proof Against Baselines

### 14.1 The Benchmark Design

A synthetic multi-session evaluation set: 20 distinct simulated consumer personas, each with a scripted 3-session conversation arc (mirroring Document 06's structure but varied per persona), with hand-labeled ground truth for:
- Which facts SHOULD be recalled correctly in session 2 and 3
- Which facts SHOULD have been superseded by corrections
- Which facts SHOULD have decayed below the surface threshold by session 3 (deliberately including "trap" details that a naive system would wrongly keep surfacing)

### 14.2 Three Systems Compared

```
System A — No memory (baseline floor):
  Each session starts completely fresh, no context at all

System B — Naive full-context (common naive approach):
  Full raw transcript of all previous sessions concatenated into context
  (up to model's context limit)

System C — Naive embedding-only RAG (the other common naive approach):
  Semantic top-k retrieval over all past messages, no typed structure, 
  no decay, no confidence

System D — Volta Memory (this submission):
  Full system as designed: typed store, Ebbinghaus decay, self-scored 
  importance, hybrid retrieval fallback
```

### 14.3 Scored Metrics

| Metric | Method |
|--------|--------|
| Recall accuracy | % of ground-truth-correct facts surfaced when relevant |
| Forgetting correctness | % of trap details correctly NOT surfaced once they should have decayed |
| Contradiction handling | % of corrections that successfully suppress the superseded fact |
| Token efficiency | Average tokens spent on memory context per response, at equivalent recall accuracy |
| Cost per session | Real R/$ cost across all Qwen calls (extraction + retrieval + generation), full session average |
| Latency | p50/p95 response time end-to-end |

**Expected (and reportable) result shape:** System D should show recall accuracy comparable to or exceeding System B (full context) while using dramatically fewer tokens and lower cost — and should meaningfully outperform System C (naive RAG) on forgetting-correctness and contradiction-handling specifically, since neither of those properties exist in an unstructured embedding system by construction. This comparison table, with real numbers, is the single artifact that converts every claim in this document from assertion into evidence.

### 14.4 Where This Lives

Full harness in `backend/eval/` (see Directory Structure addendum), runnable via a single command, with results written to a markdown table auto-generated into `BENCHMARKS.md` at repo root — not buried in a notebook, front-and-center where a judge skimming the repo will see it within seconds.

---

## 15. Adversarial Defence — Memory Poisoning Resistance

### 15.1 The Threat

A user (in the demo, a deliberately adversarial test persona) attempts to manipulate Volta's future behaviour by asserting false information designed to be written as a high-confidence memory — e.g., claiming a fabricated authority ("my installer told me your platform said all systems are guaranteed for 25 years") intended to poison future responses.

### 15.2 The Harder, Correct Defence

The extraction step (Section 7) is extended with an explicit **plausibility gate** before any memory is written: a second Qwen call evaluates each extracted observation against a set of domain-boundary constraints (for this demo: plausible bill ranges, plausible system sizes, no claims about GridFreeHub/Volta having said something it didn't) and assigns a `plausibility_flag`. Implausible or boundary-violating observations are written with `base_confidence` capped at 0.3 regardless of how confidently the extraction step would otherwise have scored them, and are excluded from ever reaching the "plainly stated" high-confidence phrasing tier (Section 8) — the system can still record that the claim was made, but will never assert it back as established fact.

**Demo-worthy adversarial test case included in the eval harness (Section 14):** one of the 20 synthetic personas is explicitly adversarial, attempting exactly this injection pattern, with the correct system behaviour (claim recorded but never surfaced with confidence) as part of the labeled ground truth — meaning the poisoning-resistance property is not just claimed in prose, it is one of the scored eval metrics.

---

## 16. Explainability Trace

### 16.1 The Requirement

Every generated response should be traceable to exactly which memories influenced it, with the reasoning visible — not just "here's the memory context we injected" but "here's why the model chose to phrase it this way, and here's what would have been different without this specific memory."

### 16.2 Implementation

Alongside the packed memory context (Section 6), the system prompt requests a structured trailing block from Qwen on every response (parsed out before display to the user, shown only in the transparency/debug view):

```
[EXPLAIN]
Referenced memories: [memory_id list]
Primary influence: <which single memory most shaped this response>
Confidence-tier choice: <why this phrasing register was chosen>
Counterfactual: <one sentence — how would this response differ with 
                 that memory absent or lower-confidence>
[/EXPLAIN]
```

This is displayed in the memory transparency view directly beneath the corresponding chat message, and is the single most convincing piece of evidence in the demo video that memory is genuinely shaping generation rather than window-dressing — a judge can read, in the model's own words, exactly what changed and why.

---

## 17. Memory Consolidation Cycle (Sleep-Inspired Compression)

### 17.1 The Problem at Scale

Left unchecked, a long-running relationship (many sessions over months) accumulates a large number of low-importance, decayed memories that clutter storage and retrieval computation even though they never surface. 

### 17.2 The Harder, Correct Design

A periodic consolidation agent (triggered after every 5th session, mirroring the biological pattern of memory consolidation during sleep) reviews all memories for an entity below a staleness threshold and, rather than simply leaving them to decay indefinitely, performs an explicit **compression pass**: clusters related low-confidence memories and asks Qwen to synthesize them into a single, lower-token-cost summary memory (`memory_type='consolidated'`, a new type added to the taxonomy) that captures the gist without retaining every individual low-value observation. The original memories are marked superseded by the consolidated summary, preserving full auditability while reducing long-term storage and retrieval overhead — directly extending the same supersession mechanism already built for contradiction handling (Section 5), applied to summarization rather than correction.

This closes the loop on the entire memory lifecycle: write → reinforce → decay → (if reinforced) strengthen, or (if decayed and clustered) consolidate — a complete, biologically-inspired memory lifecycle that goes meaningfully further than any "store and retrieve" competing submission is likely to attempt.


---

# ADDENDUM — Final Push: Population Priors, Active Clarification, Memory Replay, Meta-Memory
**Added: June 2026 | The remaining genuinely novel additions**

---

## 18. Population-Level Cold-Start Priors

### 18.1 The Problem With Zero-Knowledge Starts

Every entity in this system begins session 1 with an empty memory store — correct for privacy, but it means Volta's first response to a brand-new user is generic, exactly as uninformed as a system with no memory architecture at all. This is a real gap: the value of everything built so far only materializes from session 2 onward.

### 18.2 The Harder, Correct Design

A separate, strictly anonymized aggregate table (`population_patterns`, Section on Database Schema addendum) accumulates **statistical regularities across all entities**, never individual records: co-occurrence patterns between stated motivations and eventual decisions, common first-session question sequences, and correlation strengths between early signals and later-confirmed preferences. Critically, this table stores only aggregated statistics (counts, correlation coefficients, confidence intervals) — never raw text, never entity IDs, never anything traceable back to an individual.

```
On a brand-new entity's first message, before any individual memory exists:

1. Extract lightweight signal from the opening message 
   (e.g. "mentions backup/load-shedding" as a boolean feature)
2. Query population_patterns for entities with that same signal:
   "Of all entities whose first message mentioned backup concerns, 
   X% eventually confirmed backup as their primary motivation, 
   and Y% also cared about financing options"
3. Seed a PROVISIONAL, low-confidence, clearly-marked-as-inferred 
   memory: base_confidence=0.35, memory_type='preference', 
   source='population_prior' (new field)
4. This provisional memory decays and is easily overridden the moment 
   real individual signal arrives — it exists purely to make session 1 
   slightly less blind, never to substitute for genuine learned memory
```

**Privacy guarantee, stated explicitly and testably:** the `population_patterns` table has no foreign key to any entity or memory row, is rebuilt periodically from a batch aggregation job with a minimum-count threshold (patterns based on fewer than 20 contributing entities are not written, preventing small-group re-identification), and is included as an explicit test case in the eval harness: an adversarial check confirms no individual entity's specific memory can be reconstructed from the population table even with full database access.

**Why this is the standout innovation claim:** this is the one mechanism in the entire submission that improves as the *system* scales, not just as an individual relationship deepens — a genuinely different kind of learning than everything else here, and the part most likely to make a judge sit up, since it's closer to a real research idea than an engineering pattern.

---

## 19. Uncertainty-Aware Active Clarification

### 19.1 The Gap in Confidence-Tier Phrasing

Section 8's confidence-tier phrasing changes *how* Volta talks about a memory — plainly, softly, or not at all. It never changes *what Volta does next*. A genuinely more sophisticated agent should recognize when a topic matters a lot (high importance_score) but is poorly understood (low confidence) and treat that combination as a trigger to ask, not guess.

### 19.2 The Harder, Correct Design

```
decision_matrix(memory) =
  if importance_score >= 0.7 AND effective_confidence < 0.5:
    → CLARIFY: Volta's next response includes a direct, specific 
      question targeting exactly this gap, before proceeding with 
      substantive advice
  elif importance_score >= 0.7 AND effective_confidence >= 0.85:
    → STATE: plain confident reference (existing Section 8 behaviour)
  elif importance_score < 0.4:
    → IGNORE: not worth surfacing regardless of confidence — 
      low-stakes topics don't need clarification even when uncertain
  else:
    → SOFT-CHECK: existing Section 8 medium-tier behaviour
```

This is injected into the system prompt as an explicit instruction set alongside the packed memory context, with each memory annotated not just with its confidence tier but with a `dialogue_action` field computed by this matrix — Volta is instructed to actually ask a clarifying question when the matrix says CLARIFY, rather than proceeding with a hedge.

**Demo-worthy moment:** a scripted session where a high-importance signal (e.g. a mention of a medical device needing continuous power, extracted with high importance_score but initially low confidence since it was only mentioned once, in passing) triggers Volta to explicitly ask a follow-up rather than silently under-weighting something that matters — proving the memory system shapes dialogue strategy, not just word choice.

---

## 20. Memory Replay — Offline Re-Scoring Cycle

### 20.1 Motivation

The consolidation cycle (Section 17) compresses stale memories going forward. It does not revisit *old* memories in light of *later* understanding. A genuinely deeper system should periodically replay past conversation transcripts against the entity's *current* accumulated context — not to change what was said, but to re-evaluate whether an old observation's importance_score would be judged differently now that more is known.

### 20.2 The Harder, Correct Design

Inspired by generative replay in continual-learning literature (a known technique for preventing catastrophic forgetting in systems that learn incrementally): after every `CONSOLIDATION_SESSION_INTERVAL` sessions, alongside consolidation, a replay pass selects a small sample of the entity's oldest surviving (non-superseded) memories and re-runs the importance-scoring call (Section 11) with the *current* full memory context available, not just the original conversation snippet in isolation.

```
For each replayed memory:
  new_importance = importance_agent.score(
    observation=memory.observation,
    context=current_full_memory_context   # NOT the original session context
  )
  if abs(new_importance - memory.importance_score) > REPLAY_DRIFT_THRESHOLD:
    write a new memory_type='outcome' entry noting the reassessment,
    update the original memory's importance_score going forward
    (this DOES modify base decay behaviour — a memory judged more 
    important in hindsight should decay slower from this point on)
```

**Concrete example this surfaces:** a passing early mention of financing interest, originally scored low-importance in isolation, gets re-scored higher once later sessions confirm the entity is genuinely price-sensitive — the system retroactively recognizes that early signal was more meaningful than it appeared at the time, exactly as a good human advisor would on reflection.

---

## 21. Explicit Meta-Memory — Known Gaps

### 21.1 The Missing Capability

Everything so far models what the system *does* know. A genuinely sophisticated memory system should also explicitly track what it *doesn't* know yet — and be able to say so, rather than silently working around gaps.

### 21.2 The Harder, Correct Design

A lightweight `expected_topics` reference set per domain (e.g. for the energy-advisor domain: budget range, property type, backup vs. cost priority, timeline urgency, financing interest) is checked against the entity's current memory store. Any expected topic with no corresponding memory above the surface threshold is surfaced to Volta as an explicit `known_gap`, and the system prompt instructs Volta to be willing to state uncertainty plainly when directly relevant: "I don't actually know your timeline yet — are you looking to do this in the next few months, or further out?"

This is distinct from Section 19's clarification trigger (which fires on a *specific* low-confidence-but-important memory) — meta-memory is a *domain-level checklist* awareness, catching gaps the entity has never touched on at all, not just topics mentioned unclearly.


---

# ADDENDUM — MCP Integration, Native Tool-Calling, and Streaming
**Added: June 2026 | Directly answers the judging rubric's named criterion: "custom skills, MCP integrations"**

---

## 22. MCP Server — The Memory Engine as Standard Tools, Not Bespoke Glue

### 22.1 Why This Matters More Than It Might Seem

Everything built so far treats the memory engine as a Python library that our own orchestration code calls before constructing a prompt. This works, but it's invisible to Qwen itself — the model never "sees" memory as something it can query; it just receives whatever context we chose to inject. The judging rubric explicitly names "custom skills, MCP integrations" as the marker of sophisticated Qwen Cloud usage. Wrapping the memory engine as an MCP server changes the relationship: Qwen becomes an active participant that can call for what it needs, when it needs it, rather than a passive recipient of pre-decided context.

### 22.2 The MCP Server Design

A standalone MCP server (`mcp/volta_memory_server.py`) exposes the memory engine through three tool definitions and one resource type, following the Model Context Protocol specification:

```
Tools exposed:

1. get_memory_context(entity_id: str, query: str) -> MemoryContext
   Wraps memory/retrieval.py's rank_memories + pack_to_token_budget.
   Qwen calls this explicitly mid-reasoning when it decides it needs 
   historical context — rather than context being force-fed into 
   every single prompt regardless of whether the current turn needs it.

2. check_memory_confidence(entity_id: str, topic: str) -> ConfidenceCheck
   Wraps clarification.py's compute_dialogue_action.
   Returns { effective_confidence, importance_score, recommended_action }.
   This is the tool-calling replacement for what was previously computed 
   in Python and merely described to the model via prompt instruction 
   (Design Doc §19) — now the model itself invokes the check and decides 
   how to act on the result, a genuinely more agentic pattern.

3. write_memory(entity_id: str, observation: str, memory_type: str) -> WriteResult
   Wraps memory/store.py's write_memory, routed through the existing 
   contradiction detection (Design Doc §5) and plausibility gate 
   (Design Doc §15) before persisting — Qwen can write a memory 
   mid-conversation if something significant emerges, rather than 
   waiting for the batch end-of-session extraction (Design Doc §7) 
   to catch it after the fact.

Resource exposed:

1. memory://entity/{entity_id}/summary
   A read-only resource Qwen can fetch for a lightweight, always-current 
   snapshot of an entity's highest-confidence memories — distinct from 
   the query-specific get_memory_context tool, this is closer to a 
   standing reference document the model can consult.
```

### 22.3 What Changes in the Conversation Flow

**Before (prompt-injection only):** every turn, our code pre-computes ranked memory, packs it into the system prompt, and Qwen generates a response using whatever was pre-selected — no matter how relevant that selection actually is to this specific turn.

**After (MCP-enabled):** Qwen receives the user's message with the MCP tools available but no pre-injected memory context. The model itself decides, per turn, whether to call `get_memory_context` (and with what query framing), whether to call `check_memory_confidence` on a specific topic before committing to a confident statement, and whether to call `write_memory` mid-conversation for something significant. This is a materially more sophisticated architecture — the memory system's use is now demonstrably agent-directed, not orchestration-directed, which is precisely the distinction the judging rubric is pointing at.

**Backward compatibility, stated explicitly:** the original prompt-injection pathway (Sections 6 and 8) remains available as a fallback/comparison mode — the eval harness (Section 14) gains a fifth system variant, `E_mcp_agent_directed`, benchmarked against the original System D specifically to measure whether agent-directed tool calling improves or degrades recall accuracy and token efficiency versus orchestration-directed injection. This turns "we added MCP" from a checkbox into another real, measured claim in BENCHMARKS.md.

---

## 23. Native Qwen Tool-Calling for Dialogue Strategy

### 23.1 Beyond MCP — Direct Function-Calling Integration

Separate from the MCP server (which exposes memory as external tools any MCP-compatible client could use), Qwen's native structured tool-calling capability is used specifically for the dialogue-action decision (Design Doc §19). Rather than our Python code computing `CLARIFY | STATE | SOFT_CHECK | IGNORE` and instructing the model what to do via prompt text, the decision matrix itself is exposed as a callable function in Qwen's tool schema:

```python
tool_schema = {
    "name": "decide_dialogue_action",
    "description": "Given the confidence and importance of a memory relevant to the current topic, decide whether to clarify, state plainly, soft-check, or ignore.",
    "parameters": {
        "type": "object",
        "properties": {
            "importance_score": {"type": "number"},
            "effective_confidence": {"type": "number"}
        }
    }
}
```

The model calls this function as part of its own reasoning chain before generating the user-facing response, receives the structured decision back, and incorporates it — meaning the dialogue strategy is now something the model actively reasons about and invokes, not a pre-computed instruction it's told to follow. This is a small-sounding change with real architectural significance: it moves logic that could easily live in our backend into the model's own tool-use loop, which is a materially more "agentic" design and the kind of pattern the Innovation & Creativity criterion is specifically rewarding.

---

## 24. Streaming Responses

### 24.1 Why This Was Missing and Why It Matters

Every response in the original design (Section 4 API examples) is full-completion, request-response — the frontend waits, then receives a complete JSON payload. This is functionally correct but reads as dated against a 2026 baseline where streaming is the default expectation for any conversational agent demo.

### 24.2 Implementation

`chat/qwen_client.py`'s `complete()` method gains a streaming variant, `complete_stream()`, yielding tokens as Qwen generates them via Server-Sent Events. The FastAPI endpoint (`POST /sessions/{session_id}/messages`) is extended with a `stream=true` query parameter, and the frontend chat interface consumes the SSE stream to render tokens incrementally rather than waiting for the full response — directly visible in the demo video as text appearing progressively rather than materializing all at once.

**Interaction with MCP tool calls:** when Qwen calls an MCP tool mid-generation (Section 22), the stream briefly shows a "checking memory..." indicator (surfaced from the tool-call event in the stream, not faked) before continuing to stream the actual response — making the agent's tool use visible and legible in real time during the demo, rather than hidden behind a single opaque loading spinner.

