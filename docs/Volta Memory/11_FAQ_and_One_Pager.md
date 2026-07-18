# Volta Memory — FAQ & One-Page Pitch Summary
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

---

## Table of Contents
- [1. One-Page Pitch Summary](#1-one-page-pitch-summary)
- [2. Preemptive Judge FAQ](#2-preemptive-judge-faq)

---

## 1. One-Page Pitch Summary

**For a judge skimming 50+ submissions — read this in 90 seconds, everything else in this repo backs it up.**

> **What it is:** A conversational energy advisor with genuine persistent memory — not a longer context window, not plain vector search, but a typed, confidence-scored, decaying memory store that gets measurably better across sessions and gracefully forgets what no longer matters.
>
> **The three track requirements, answered concretely:**
> - *Efficient storage/retrieval:* typed memory store, token-budgeted retrieval ranking, hybrid embedding fallback only when the typed store has a genuine gap.
> - *Timely forgetting:* an Ebbinghaus-grounded decay model where reinforcement across sessions (not within one) multiplicatively extends memory stability — cited, cognitive-science-grounded, not an arbitrary formula.
> - *Recalling critical memories in limited context:* self-scored importance (the model judges its own memory's consequence, not a fixed per-category default) directly modulates what survives and what's prioritized under a hard token cap.
>
> **What makes this different from "just memory":** benchmarked against three baselines (no memory, full-context, naive RAG) with real measured numbers in `BENCHMARKS.md` — not asserted, proven. Defended against adversarial memory injection with a scored test case. Explainable — every response traces to exactly which memory shaped it and why, verified with real counterfactuals. Generalizes — the identical engine powers a second, unrelated persona and a third example on a completely different LLM provider, proving this is infrastructure, not a script.
>
> **Real-world impact beyond the demo:** the memory architecture here is being absorbed into the design of GridFreeHub, a real production platform in active development (see Document 10 for the precise, honest scope of that commitment). The core engine is published as a standalone, installable package with a public benchmark dataset release, inviting community adoption beyond this hackathon.
>
> **Try it yourself:** [live demo URL] — you don't have to take our word for any of this.

---

## 2. Preemptive Judge FAQ

**"Isn't this just RAG with extra steps?"**
No — and this is the most important distinction in the whole submission. Pure RAG retrieves by semantic similarity to the current query, with no concept of importance, decay, or confidence. A trivial detail mentioned five times can outrank a critical fact mentioned once. This system retrieves by a typed, confidence-weighted, decay-aware score — and uses embedding search only as a bounded fallback when the curated store has a genuine gap, not as the primary mechanism. `BENCHMARKS.md` specifically measures forgetting-correctness and contradiction-handling against a naive-RAG baseline (System C) to make this difference concrete rather than asserted.

**"How do we know the decay/forgetting is real and not just a demo trick?"**
The eval harness includes trap details deliberately designed to test whether the system correctly stops surfacing information that should have decayed by a given session — this is a scored metric (`forgetting_correctness`) against labeled ground truth, not a single scripted moment in a video. The memory transparency view also lets anyone inspect a memory's `effective_confidence` directly, computed live from the decay formula, not stored as a static value that could be faked.

**"Why Qwen specifically, and does this only work with Qwen?"**
Qwen powers the required demo per the hackathon's rules. The `LLMBackend` protocol (Document 08 §2) is provider-agnostic by construction, proven with a third reference example running on a different provider entirely — the memory architecture is not coupled to any specific model.

**"Is the human evaluation study statistically rigorous?"**
No, and we say so explicitly (Document 08 §9) — it's a small, honestly-labeled informal study, not a peer-reviewed trial. We report it as exactly what it is, including real participant quotes, because an honestly-scoped small study is more credible than an inflated claim of rigor it doesn't have.

**"What stops the population cold-start priors from leaking individual user data?"**
The aggregation table has no foreign key to any individual entity or memory, enforces a minimum-contributor-count threshold before writing any pattern, and the eval harness includes an explicit adversarial test confirming no individual memory can be reconstructed from the aggregate table even with full database access (Memory Design Doc §18.2).

**"Is this actually going to be used anywhere, or is GridFreeHub just a story for the hackathon?"**
Document 10 states the honest, specific version of this: GridFreeHub's own memory system design will be revised based on what was validated here — the decay model, contradiction handling, and retrieval ranking specifically — implemented natively in GridFreeHub's own codebase. It is not a claim that this code gets imported wholesale, and we've deliberately documented exactly what does and doesn't transfer, because overstating this relationship would be dishonest and a specific, bounded claim is more credible than a vague one.

**"Why should we believe the benchmark numbers weren't cherry-picked?"**
The full eval harness, all 20 synthetic personas, the baseline implementations, and the raw per-persona results are in the public repository — anyone, including judges, can re-run `eval/run_eval.py` themselves and reproduce the numbers in `BENCHMARKS.md` independently.

