# Volta Memory — Roadmap
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

---

## Table of Contents
- [1. Roadmap Philosophy](#1-roadmap-philosophy)
- [2. Phase 0 — Hackathon Submission (Now)](#2-phase-0--hackathon-submission-now)
- [3. Phase 1 — Post-Submission Hardening (Weeks 1–4)](#3-phase-1--post-submission-hardening-weeks-1-4)
- [4. Phase 2 — Community Package Launch (Months 2–3)](#4-phase-2--community-package-launch-months-2-3)
- [5. Phase 3 — Domain Expansion (Months 3–6)](#5-phase-3--domain-expansion-months-3-6)
- [6. Phase 4 — GridFreeHub Design Transfer (Months 4–8)](#6-phase-4--gridfreehub-design-transfer-months-4-8)
- [7. Deferred Ideas — Explicitly Not on the Roadmap](#7-deferred-ideas--explicitly-not-on-the-roadmap)

---

## 1. Roadmap Philosophy

This roadmap covers two distinct timelines that must not be conflated: the **hackathon submission scope** (everything needed for judging, complete by the Jul 20 deadline) and the **life of the project afterward**, if it continues as an open-source package regardless of placement. A project that only exists for judging day is a weaker impact claim than one with a credible plan for what happens next — this document exists to make that plan concrete rather than implied.

---

## 2. Phase 0 — Hackathon Submission (Now)

Everything specified across Documents 01–11: the memory engine with decay, contradiction handling, self-scored importance, hybrid retrieval, MCP integration, native tool-calling, streaming, the eval harness with five system variants, adversarial defence, consolidation, population priors, active clarification, memory replay, the standalone package extraction, the human evaluation study, the public benchmark dataset, and full Devpost compliance.

**Definition of done for Phase 0:** every gate in Document 07's checklists passes, the repo is public with a visible license, the demo videos are recorded and uploaded, and the submission form is complete on Devpost with at least 24 hours of buffer before the deadline.

---

## 3. Phase 1 — Post-Submission Hardening (Weeks 1–4)

Regardless of competition outcome, the submission as built during the hackathon window carries the usual pressure-tested-under-deadline risks: edge cases not fully covered, the self-tuning search possibly run at reduced scope if token budget was tight (Document 09 §20), and documentation written faster than it was reviewed.

**Concrete Phase 1 items:**
- Re-run the full eval harness (all five system variants, all 20 personas) at full scope if it was reduced during the hackathon for budget reasons, and update BENCHMARKS.md with final, non-budget-constrained numbers
- Address any judge feedback received, whether the project places or not — feedback from the "Top 10 Honorable Mention" review process or direct Discord community feedback is valuable regardless of prize outcome
- Expand unit test coverage in any area that was stubbed or lightly tested under time pressure, and publish the coverage report referenced in Document 02's addendum
- Fix any issues discovered by external users who try the live demo or clone the repo — the live demo link (Document 09 §13) should stay monitored and maintained past the judging window, not abandoned the day after submission

---

## 4. Phase 2 — Community Package Launch (Months 2–3)

This phase executes the adoption pathway already specified in Document 08 §5, on a real timeline rather than as an abstract plan.

- Publish `volta-memory` to PyPI properly, with semantic versioning starting at a genuine `0.1.0`, not a hackathon-hacked version string
- Publish the technical blog post (Document 08 §5, "we built a memory library, not a chatbot") to relevant community spaces, explicitly separate from whatever blog post is submitted for the hackathon's own Blog Post Prize (Document 16 in this suite is the hackathon-specific draft; the Month-2 post can be a more technical, less pitch-oriented follow-up written with the benefit of real community feedback from Phase 1)
- Open the repository for external contributions per the governance model in Document 08 §7 — respond to the first few issues/PRs personally and quickly, since early contributor experience disproportionately determines whether a project gets a second contribution or none

---

## 5. Phase 3 — Domain Expansion (Months 3–6)

- Build a genuine third full domain example beyond the energy advisor and study coach (the customer-support or elder-care scenarios from Document 08 §3's applicability table are the strongest candidates, given how concretely their decay/importance requirements were already reasoned through)
- Revisit the population-level cold-start priors mechanism (Design Doc §18) with real usage data accumulated from Phase 2's community adoption — the mechanism's value is inherently data-dependent, and this is the point where enough real (anonymized, aggregated) usage should exist to evaluate whether it's actually improving cold-start quality in practice, not just in the synthetic eval harness
- Revisit the self-tuning constant search (Design Doc's directory addendum) against real usage patterns rather than synthetic personas — the original hackathon-era search only had synthetic ground truth to optimize against; real usage data changes what "optimal" decay constants actually look like

---

## 6. Phase 4 — GridFreeHub Design Transfer (Months 4–8)

Executes Document 10's stated relationship concretely, once GridFreeHub's own engineering timeline reaches its memory-layer implementation phase.

- Revise GridFreeHub's `agent_memory` specification (in that project's own Agentic System Design documentation) incorporating the decay model, contradiction-handling pattern, and retrieval-ranking approach validated here — implemented natively in GridFreeHub's own codebase and schema conventions, per Document 10 §2's explicit "taken directly" list
- Evaluate, with real GridFreeHub installer/consumer data by this point, whether the "taken with judgment" items (self-scored importance, hybrid retrieval, consolidation) are warranted yet, or whether GridFreeHub's actual data volume still favors the simpler fixed-decay version
- Explicitly do **not** import any VoltaMemory code directly into GridFreeHub's repository — this phase is a design-transfer exercise, re-implemented natively, consistent with Document 10 §1's core distinction

---

## 7. Deferred Ideas — Explicitly Not on the Roadmap

Stated plainly, so no one mistakes silence for a hidden future promise:

- **Multi-modal memory** (voice, image) — mentioned only in passing during design discussion, never scoped, and not planned. If pursued at all, it would be a genuinely new project, not an extension of this one.
- **A hosted, commercial SaaS version** of the memory engine — this roadmap is explicitly about open-source community infrastructure, not a monetized product. Revisiting this is possible in principle but is not part of any committed plan here.
- **EdgeAgent-track-style on-device deployment** — the memory engine's Postgres dependency and cloud-model reliance make this a substantial redesign, not a natural next phase, and it is not planned.
