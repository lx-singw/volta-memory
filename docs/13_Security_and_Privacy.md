# Volta Memory — Security & Privacy
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**
**Consolidates security-relevant design decisions scattered across other documents into a single reviewable posture**

---

## Table of Contents
- [1. Why This Consolidation Exists](#1-why-this-consolidation-exists)
- [2. Threat Model](#2-threat-model)
- [3. Memory Poisoning Defence](#3-memory-poisoning-defence)
- [4. Population Prior Privacy Guarantees](#4-population-prior-privacy-guarantees)
- [5. Credential and Secrets Handling](#5-credential-and-secrets-handling)
- [6. Public Live Demo Exposure](#6-public-live-demo-exposure)
- [7. Data Retention and Deletion](#7-data-retention-and-deletion)
- [8. MCP Server Attack Surface](#8-mcp-server-attack-surface)
- [9. Known Limitations, Stated Honestly](#9-known-limitations-stated-honestly)

---

## 1. Why This Consolidation Exists

Security-relevant decisions are already made throughout Documents 03 and 09 — the plausibility gate, the population-prior anonymization floor, secrets redaction in logging. Scattering them means no single reviewer (a judge, a contributor, a future GridFreeHub engineer per Document 10) can assess the whole posture at once. This document exists purely to gather what's already true elsewhere into one place, and to be honest about what's deliberately out of scope for a hackathon-timeline project.

---

## 2. Threat Model

| Actor | Motivation | Relevant surface |
|-------|-----------|------------------|
| Adversarial demo user | Inject false memory to manipulate future responses | Memory extraction pipeline (Design Doc §7, §15) |
| Public live-demo visitor | Exhaust the function-held Qwen budget / cost abuse | API Gateway and Function Compute edge |
| Curious contributor with DB access | Attempt to re-identify an individual from population priors | `population_patterns` table (Design Doc §18) |
| Careless maintainer | Accidentally commit or log a real API key during repeated demo recording | Any file, any log line |
| MCP client (malicious or buggy) | Call memory-write tools with malformed or excessive data | `mcp/volta_memory_server.py` (Design Doc §22) |

---

## 3. Memory Poisoning Defence

Fully specified in Design Doc §15 — restated here for consolidated review: every extracted observation passes a plausibility gate (a second Qwen call checking domain-boundary constraints) before being written with normal confidence. Observations flagged `boundary_violation` are capped at `PLAUSIBILITY_CONFIDENCE_CAP` (default 0.3, Document 09 §8) regardless of how confidently extraction would otherwise have scored them, and are excluded from the high-confidence "state plainly" phrasing tier (Design Doc §8) entirely. The adversarial persona in the eval harness (Design Doc §14, persona 20) exists specifically to score this defence quantitatively, not just assert it works.

**Extended by the MCP addition (Design Doc §22):** the `write_memory` MCP tool routes through the identical plausibility gate as the batch extraction pathway — a memory written mid-conversation via tool call is not a bypass of this defence, it uses the same `memory/plausibility.py` module.

---

## 4. Population Prior Privacy Guarantees

Fully specified in Design Doc §18.2 — restated here: the `population_patterns` table has no foreign key to any individual entity or memory row, is rebuilt from a batch job with a hard minimum-contributor-count floor (`POPULATION_MIN_CONTRIBUTOR_COUNT`, default 20, Document 09) before any pattern is written, and the eval harness includes an explicit adversarial re-identification test confirming no individual entity's specific memory can be reconstructed from the aggregate table even with full database access.

**What this does not guarantee:** this is a practical, tested privacy floor appropriate for a hackathon-scale demo dataset, not a formal differential-privacy guarantee with a proven epsilon bound. Stated honestly per Section 9 below — a production deployment at real scale (per Document 12's Phase 3) would warrant a more rigorous formal privacy analysis before this mechanism handles real user populations at volume.

---

## 5. Credential and Secrets Handling

Fully specified in Document 09 §18 — restated here: `.env` is git-ignored, `.env.example` ships placeholder values only, `LOG_REDACT_API_KEYS=true` is enforced in every environment including local development, and cloud credentials are scoped to minimum required permissions rather than account-wide access. The specific risk named in Document 09 — that this project's submission strategy involves repeated screen recordings, making an accidentally-visible key a real and not theoretical risk — is repeated here because it is the single most likely security incident for a project like this, not a generic disclaimer.

---

## 6. Public Live Demo Exposure

The public product runs behind API Gateway, which applies route-level throttling and concurrency limits before Function Compute can invoke Qwen. Qwen credentials remain in the Function Compute secret boundary; the browser receives only a public API origin. A first visit receives an isolated anonymous workspace, `/try` creates a separate sandbox, and `/showcase` is read-only. There is no shared mutable demo account, public reset route, or browser-facing reseed/evaluation action.

---

## 7. Data Retention and Deletion

Not previously specified elsewhere — a genuine gap this document closes. For the hackathon demo scope:

- Anonymous visitor workspaces are isolated by an opaque HttpOnly session cookie. A visitor can upgrade with passwordless email, export their workspace, or permanently delete it through the tenant-scoped API. Showcase data is immutable and excluded from deletion.
- The named human evaluation study participants (Document 08 §9) — their raw conversation data and ratings should be deletable on request, and the study protocol (referenced in Document 02's `docs/human-eval-study/` addition) should state this explicitly to participants at recruitment, not as an afterthought
- The public benchmark dataset (Document 08 §10) is synthetic — no real user data, so standard dataset-retention concerns do not apply, which is itself a reason the synthetic-persona approach was the right choice for a public release rather than anonymized real conversation logs

---

## 8. MCP Server Attack Surface

The MCP server (Design Doc §22) is new attack surface introduced by this round of additions and deserves explicit treatment, not just a feature description.

- **Tool input validation:** `write_memory`'s `observation` and `memory_type` parameters must be validated against the same schema constraints as the internal `store.py` write path — the MCP layer must not allow bypassing constraints (e.g. an arbitrary `memory_type` string not in the allowed enum) just because it arrived via a different entry point
- **Entity ID scoping:** any MCP client should only be able to act on the `entity_id` associated with its own active session — the conformance test suite (`mcp/conformance_tests.py`, Document 02) should include an explicit test attempting cross-entity access and confirming it's rejected
- **Rate limiting:** the MCP server should inherit the same per-IP or per-session rate limiting as the main chat endpoint (Section 6), since it is an additional pathway to trigger Qwen API calls and therefore additional cost-exposure surface

---

## 9. Known Limitations, Stated Honestly

This section exists because overstating security maturity is itself a credibility risk with a technically literate judge panel.

- The population-prior privacy floor (Section 4) is a tested practical mitigation, not a formally proven differential-privacy guarantee
- No penetration testing, formal or informal, has been conducted against this submission — it has not been adversarially tested by anyone outside the build team beyond the scripted adversarial eval persona
- The plausibility gate (Section 3) is itself an LLM call, and is therefore subject to the same class of reliability limitations as any other LLM-based check — it reduces but does not eliminate the risk of a sufficiently sophisticated poisoning attempt succeeding
- This is a hackathon-timeline project. The security posture here is appropriate and honestly reasoned for that context, and explicitly not represented as production-hardened at the standard a real multi-tenant commercial system (like GridFreeHub, per Document 10) would require before handling real user data at scale
