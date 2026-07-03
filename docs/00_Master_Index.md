# Volta Memory — Master Index
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent | June 2026**

---

## Table of Contents
- [Quick Reference](#quick-reference)
- [What This Project Is](#what-this-project-is)
- [Document Suite](#document-suite)
- [Scope Boundary](#scope-boundary)

---

## Quick Reference

| I need to... | Go to |
|-------------|-------|
| Understand the product and feature scope | [01 — PRD](#) |
| Navigate the codebase | [02 — Directory Structure](#) |
| Understand the memory architecture in depth | [03 — Memory System Design](#) |
| See the database schema | [04 — Database Schema](#) |
| Review API endpoints | [05 — API Reference](#) |
| Read the three-session demo script | [06 — Demo Script](#) |
| Prepare submission artifacts | [07 — Submission Checklist](#) |

---

## What This Project Is

**Volta Memory** is a standalone agent built for the Qwen Cloud Global AI Hackathon, Track 1 (MemoryAgent). It is an extraction and rebuild of a single component — the Volta energy advisor persona — originally designed as part of a larger project (GridFreeHub, a South African solar marketplace platform). This submission is **not** a GridFreeHub demo. It is a focused, standalone agent that happens to use Volta's persona as its narrative texture, built fresh on Qwen Cloud and Alibaba Cloud infrastructure, with a real persistent memory system that did not exist in the original design.

**The track's three explicit requirements, and how this project answers each:**

1. **Efficient memory storage and retrieval** — an entity-keyed, typed, confidence-scored memory store with a ranked retrieval function tuned for limited context windows.
2. **Timely forgetting of outdated information** — a confidence decay model and explicit supersession logic, built fresh for this submission (the source material never specified this).
3. **Recalling critical memories within limited context windows** — token-budgeted retrieval ranking by confidence × reinforcement × recency, with a hard enforced cap.

**What makes the demo legible to a judge in three minutes:** a single consumer persona returns across three separate chat sessions. Each session, Volta visibly recalls, applies, and refines what it learned previously — without being told the conversation history. That visible compounding intelligence is the entire submission.

---

## Document Suite

| # | Document | Purpose |
|---|----------|---------|
| 01 | PRD | Feature scope, user flows, what's in and out |
| 02 | Directory Structure | Full repo layout, every file explained |
| 03 | Memory System Design | The core track deliverable — schema, decay, retrieval ranking |
| 04 | Database Schema | Full SQL schema for memory store and conversations |
| 05 | API Reference | All endpoints, request/response examples |
| 06 | Demo Script | Word-for-word three-session scenario for the video |
| 07 | Submission Checklist | Every hackathon requirement mapped to a deliverable |

---

## Scope Boundary

**In scope:** Volta persona, persistent memory (storage, decay, retrieval), a simple chat interface, Qwen Cloud integration, Alibaba Cloud deployment.

**Explicitly out of scope:** Everything else from the source material — SSEG compliance, installer portal, admin dashboard, FinID, payments, the other 25 agents, the multi-agent message bus, GridFreeHub branding and business model. None of it serves a MemoryAgent track submission, and including any of it would dilute the judged criteria rather than strengthen them.


---

# ADDENDUM — Document 08 Added
**Added: June 2026**

| # | Document | Purpose |
|---|----------|---------|
| 08 | Productization & Community Impact | Standalone package extraction, quantified domain applicability, competitive landscape vs Mem0/LangChain/MemGPT, adoption pathway, GridFreeHub production commitment, community governance, 20-line reference integration |

**Directly targets:** Problem Value & Impact (25% weight) — this was the lowest-scoring criterion in self-assessment prior to this document; it now has the same evidentiary rigor as the Technical Depth section.


---

# ADDENDUM — Document 09 Added
**Added: June 2026**

| # | Document | Purpose |
|---|----------|---------|
| 09 | Environment Variables | Complete reference for every variable across Qwen Cloud, Alibaba Cloud, database, memory tuning, hybrid retrieval, plausibility, consolidation, eval harness, explainability, app/server, hosted demo, frontend, package publishing, and observability — plus a full copy-pasteable `.env.example` and a per-environment matrix |

