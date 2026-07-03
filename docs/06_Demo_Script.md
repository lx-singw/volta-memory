# Volta Memory — Three-Session Demo Script
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**
**For the 3-minute submission video**

---

## Table of Contents
- [1. Video Structure](#1-video-structure)
- [2. Session 1 — First Contact](#2-session-1--first-contact)
- [3. Session 2 — Proactive Recall + Correction](#3-session-2--proactive-recall--correction)
- [4. Session 3 — Decay in Action](#4-session-3--decay-in-action)
- [5. Closing — Architecture Recap](#5-closing--architecture-recap)

---

## 1. Video Structure

| Time | Segment |
|------|---------|
| 0:00–0:20 | Cold open: state the problem in one sentence, show the empty memory table |
| 0:20–1:00 | Session 1 |
| 1:00–1:50 | Session 2 (skip-ahead framing: "three days later, new session") |
| 1:50–2:40 | Session 3 (skip-ahead framing: "three weeks later") |
| 2:40–3:00 | Closing — architecture diagram, repo link, track identification |

---

## 2. Session 1 — First Contact

**On screen:** Chat interface, empty memory transparency view side-by-side.

**Narration:** "This is Volta — a memory agent with zero history on this consumer. Watch what it remembers, and what it eventually forgets."

**Consumer types:**
> "I want to understand solar for my house, load-shedding is killing me"

**Volta replies:**
> "Totally understand — load-shedding is exhausting to plan around. Before I recommend anything: is your main concern getting your bill down, having backup power during outages, or both?"

**Consumer types:**
> "Backup mostly, my bill's about R3,200 but honestly I just want the lights to stay on"

**Volta replies:**
> "Got it — backup is the priority. For your bill range, I'd be thinking a system sized around 8kW with a battery that gets you through a 4-hour outage comfortably. We can get more specific once you're ready."

**On screen:** Click "End session." Memory transparency view updates live — two new rows appear: a `preference` (backup power is primary motivation) and a `fact` (monthly bill is R3,200), each with a confidence score visible.

**Narration over the table:** "Two structured memories, typed and confidence-scored — not a saved transcript."

---

## 3. Session 2 — Proactive Recall + Correction

**On screen:** New session started. Text overlay: "Three days later. New session. No conversation history passed in."

**Volta opens, unprompted:**
> "Hey — last time you mentioned backup power was the real driver. Still the case? Happy to get more specific on system sizing if so."

**Narration:** "Volta opened with that on its own — nothing in this message was hardcoded, it came from the memory store."

**Consumer types:**
> "Yeah still the priority. Actually my bill's gone up though, it's more like R3,800 now"

**Volta replies:**
> "Noted — R3,800 it is, that actually changes the maths a bit in your favour for payback time. I'll use that going forward."

**On screen:** End session. Memory table updates: the R3,200 row now shows `is_superseded: true`, greyed out, with an arrow to a new `correction` row showing R3,800 at confidence 0.95.

**Narration:** "The old number isn't deleted — it's marked superseded and kept for audit. Nothing downstream can accidentally use it again."

---

## 4. Session 3 — Decay in Action

**On screen:** New session. Text overlay: "Three weeks later."

**Consumer types:**
> "What would a system cost me now?"

**On screen, before showing Volta's reply:** cut briefly to the `/active-context` debug endpoint response — show the packed memory set for this exact query, token count visible, confirming the R3,800 correction is included and ranked highest for a pricing question.

**Volta replies:**
> "Based on R3,800 a month, I think backup power's still the main thing for you — though it's been a few weeks, let me know if priorities have shifted. At that bill level, you'd be looking at..."

**Narration:** "Notice the phrasing — 'I think... let me know if priorities have shifted.' That's not a scripted hedge. The backup-power preference has decayed from where it started, so Volta is less certain and says so. The bill correction hasn't decayed the same way because corrections get extra durability. Same memory system, different confidence, different language — automatically."

---

## 5. Closing — Architecture Recap

**On screen:** Architecture diagram (Document 07's specification).

**Narration:** "Every inference call here runs on Qwen Cloud. The backend's deployed on Alibaba Cloud — that's verified separately in our deployment proof recording, linked in the submission. The full memory design — decay model, contradiction handling, token-budgeted retrieval — is documented in the repo. This is Volta Memory, submitted to Track 1: MemoryAgent."

**On screen, final card:** Repo URL, license badge, track name.


---

# ADDENDUM — Extended Demo Segments for Maximum-Depth Proof
**Added: June 2026 | Extends the 3-minute core script with an optional deeper-proof cut**

---

## 6. Two Video Strategy

Given the depth added, produce **two videos**: the original 3-minute submission video (Sections 2–5, unchanged — this is what's required for the core submission), and a **supplementary 5–6 minute technical deep-dive** linked in the README and text description as "additional technical evidence" (not a submission requirement, but a differentiator few competing teams will bother producing).

---

## 7. Supplementary Deep-Dive Script

### Segment A — Explainability Trace (0:00–1:00)

**On screen:** Replay the session 3 exchange from the core video, but this time show the `/messages/{id}/explain` response alongside Volta's reply as it streams in.

**Narration:** "Every response Volta gives comes with a trace of exactly why. Here — the primary influence was the bill correction memory, and the model tells us in its own words what would have been different without it."

### Segment B — Benchmarks (1:00–2:30)

**On screen:** `BENCHMARKS.md` rendered, walking through the results table.

**Narration:** "We didn't just build this and hope it works — we benchmarked it against three baselines. No memory at all. Naive full-context replay. Naive embedding search. Our system matches full-context recall accuracy at a fraction of the token cost, and dramatically outperforms naive RAG specifically on forgetting correctness and contradiction handling — the two properties that don't exist in an unstructured system by construction."

**On screen:** Highlight the adversarial persona row specifically.

**Narration:** "One of our twenty test personas is deliberately adversarial — attempting to inject a false memory. The system correctly recorded the claim but never surfaced it with confidence. That's not an accident — it's the plausibility gate working as designed."

### Segment C — Ebbinghaus Grounding (2:30–3:15)

**On screen:** A rendered graph of the stability-modulated decay curve for a single memory across multiple reinforcements, showing the half-life visibly stretching with each reinforcement.

**Narration:** "The decay model isn't an arbitrary exponential. It's grounded in Ebbinghaus's forgetting curve research and the same spaced-repetition mathematics behind tools like Anki. Each reinforcement doesn't just add a little durability — it multiplies the memory's stability window. That's why a preference mentioned across three separate sessions is dramatically stickier than the same preference repeated three times in one rambling conversation — and we specifically only count cross-session reinforcement toward that growth."

### Segment D — Generalizability (3:15–4:15)

**On screen:** Split screen — Volta (energy advisor) on the left, the study-coach persona on the right, both mid-conversation.

**Narration:** "Same memory engine, zero code changes to importance scoring, decay, hybrid retrieval, or consolidation — only the system prompt differs. This is infrastructure, not a script glued to one chatbot."

### Segment E — Live Demo Invitation (4:15–4:45)

**On screen:** The hosted public URL, typed into a browser live.

**Narration:** "You don't have to take our word for any of this — try it yourself, right now, at this link."

**Closing card:** Repo URL, BENCHMARKS.md direct link, live demo URL, license badge.

