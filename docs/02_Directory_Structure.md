# Volta Memory — Directory Structure
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

---

## Table of Contents
- [1. Repository Overview](#1-repository-overview)
- [2. Root Structure](#2-root-structure)
- [3. Backend — Memory Core](#3-backend--memory-core)
- [4. Backend — Chat & Qwen Integration](#4-backend--chat--qwen-integration)
- [5. Frontend — Chat Interface](#5-frontend--chat-interface)
- [6. Deployment — Alibaba Cloud](#6-deployment--alibaba-cloud)
- [7. Environment Variables](#7-environment-variables)

---

## 1. Repository Overview

Single repository, public, OSS-licensed. Python FastAPI backend (chosen for clean, readable memory-logic code that judges can review quickly) with a minimal Next.js frontend for the chat interface and memory transparency view.

```
volta-memory/
├── LICENSE                     # MIT — visible in repo About section
├── README.md                   # Setup, architecture summary, demo link
├── ARCHITECTURE.md              # Points to submitted architecture diagram
├── .env.example
├── backend/                     # See Sections 3–4
├── frontend/                    # See Section 5
├── deployment/                  # See Section 6
└── docs/
    └── memory-design.md         # Mirrors Document 03 of this suite
```

---

## 2. Root Structure

```
volta-memory/
├── docker-compose.yml           # Local dev: postgres + backend + frontend
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # Env var loading, MAX_MEMORY_TOKENS constant
│   │   ├── db.py                # Postgres connection (Alibaba RDS in prod)
│   │   ├── memory/               # Section 3
│   │   ├── chat/                 # Section 4
│   │   └── api/
│   │       ├── routes_chat.py
│   │       └── routes_memory_debug.py
│   └── tests/
│       ├── test_memory_decay.py
│       ├── test_memory_retrieval.py
│       └── test_contradiction_handling.py
└── frontend/
    ├── package.json
    └── app/
        ├── page.tsx              # Chat interface
        └── memory/
            └── page.tsx          # Memory transparency view (debug/demo aid)
```

---

## 3. Backend — Memory Core

This is the directory that matters most for judging. Every file here maps directly to a PRD acceptance criterion.

```
backend/app/memory/
├── __init__.py
├── models.py                    # Pydantic models: Memory, MemoryType, ConfidenceTier
│
├── store.py                     # Core read/write protocol
│   # load_context(entity_id) -> MemoryContext
│   # write_memory(entity_id, memory_type, observation, confidence, evidence) -> Memory
│   # supersede(old_memory_id, new_memory) -> None
│
├── decay.py                     # Confidence decay model
│   # apply_decay(memory) -> float
│   #   Formula: confidence * exp(-lambda * days_since_last_reinforced)
│   #   lambda tuned per memory_type (preferences decay slower than 
│   #   transient outcomes)
│   # reinforce(memory_id, new_evidence) -> Memory
│   #   Resets decay clock, increments reinforcement_count, 
│   #   nudges confidence upward (capped at 0.98)
│
├── retrieval.py                  # Token-budgeted ranking — the core deliverable
│   # rank_memories(entity_id, query_context) -> list[ScoredMemory]
│   #   score = confidence * log(1 + reinforcement_count) * recency_weight
│   # pack_to_token_budget(ranked_memories, max_tokens) -> list[Memory]
│   #   Greedily fills budget by score, using real tokenizer count 
│   #   (not row count) — see Section 4 tokenizer.py
│
├── contradiction.py              # Detects and resolves conflicting observations
│   # detect_conflict(new_observation, existing_memories) -> Memory | None
│   #   Uses a lightweight Qwen call: "does this new statement 
│   #   contradict any of these existing facts?"
│   # resolve(old_memory, new_observation) -> tuple[Memory, Memory]
│   #   Marks old as superseded, creates new with fresh confidence
│
└── extraction.py                  # Post-conversation memory writing
    # extract_observations(conversation_transcript) -> list[MemoryDraft]
    #   Single Qwen call at end of session: "what should be remembered 
    #   from this conversation, typed as preference/fact/outcome?"
```

---

## 4. Backend — Chat & Qwen Integration

```
backend/app/chat/
├── __init__.py
├── qwen_client.py                # Thin wrapper around Qwen Cloud API
│   # complete(system_prompt, messages, max_tokens) -> str
│   # All model calls in the entire codebase route through this one file —
│   # the single point of contact with Qwen Cloud, isolating provider logic
│
├── tokenizer.py                   # Real token counting for budget enforcement
│   # count_tokens(text) -> int
│   # Used by memory/retrieval.py — never approximate by character count
│
├── volta_prompt.py                # The Volta system prompt
│   # build_system_prompt(memory_context: MemoryContext) -> str
│   #   Injects ranked, budgeted memories into the system prompt as 
│   #   structured context, with confidence-tier phrasing guidance 
│   #   (see PRD 4.2) so Volta's language matches certainty level
│
└── session.py                     # Session lifecycle
    # start_session(entity_id) -> Session
    # send_message(session_id, user_message) -> str
    # end_session(session_id) -> None
    #   Triggers memory/extraction.py on session end
```

---

## 5. Frontend — Chat Interface

```
frontend/app/
├── page.tsx                       # Main chat UI
│   # Minimal: message list, input box, "end session" button 
│   # (explicit, since session boundaries matter for the demo)
│
├── memory/
│   └── page.tsx                   # Memory transparency view
│       # Read-only table: observation, type, confidence, 
│       # reinforcement_count, is_superseded, last_reinforced_at
│       # This is the screen shown in the demo video to prove 
│       # the mechanism (PRD 4.6)
│
└── components/
    ├── ChatMessage.tsx
    ├── SessionControls.tsx
    └── MemoryTable.tsx
```

---

## 6. Deployment — Alibaba Cloud

```
deployment/
├── alibaba/
│   ├── production-operations.md   # OSS/CDN -> API Gateway -> FC release runbook
│   ├── edge-policies.example.json # Gateway CORS/throttling/security checklist
│   ├── function-compute.yaml      # Pointer to root FC 3.0 Serverless Devs config
│   ├── rds-postgres-setup.md      # Alibaba RDS Postgres provisioning
│   └── ecs-setup.md               # Explicitly legacy; not submission topology
│
└── proof/
    └── deployment_verification.py  # Standalone script proving Alibaba Cloud 
                                     # API usage — this is the file linked in 
                                     # the submission's "Proof of Alibaba Cloud 
                                     # Deployment" requirement
                                     # Verifies Function Compute and gateway health
```

---

## 7. Environment Variables

```bash
# Qwen Cloud
QWEN_API_KEY=
QWEN_MODEL=qwen-max              # or qwen-plus depending on cost/quality tradeoff

# Database (Alibaba RDS in production, local Postgres in dev)
DATABASE_URL=postgresql://...

# Alibaba Cloud (for deployment proof script)
ALIBABA_ACCESS_KEY_ID=
ALIBABA_ACCESS_KEY_SECRET=
ALIBABA_REGION=

# Memory tuning
MAX_MEMORY_TOKENS=800              # Hard cap enforced in retrieval.py
DECAY_LAMBDA_PREFERENCE=0.01        # Slow decay for stable preferences
DECAY_LAMBDA_OUTCOME=0.05            # Faster decay for transient outcomes
CONFIDENCE_SURFACE_THRESHOLD=0.5     # Below this, memory never surfaces
```


---

# ADDENDUM — Directory Additions for Maximum-Depth Build
**Added: June 2026 | Files required by the hardest-route technical upgrades**

---

## 8. Backend — Advanced Memory Extensions

```
backend/app/memory/
├── importance.py                  # Self-scored importance (Design doc Section 11)
│   # score_importance(observation, conversation_context) -> ImportanceResult
│   #   Single Qwen call, returns importance_score + importance_reasoning
│   # effective_lambda(memory) -> float
│   #   Applies importance multiplier to base_lambda per memory_type
│
├── stability.py                   # Ebbinghaus-grounded decay (Design doc Section 12)
│   # compute_stability(memory) -> float
│   #   S_n = S_0 * growth_factor^reinforcement_count
│   # retention_strength(memory, now) -> float
│   #   Replaces the bare exponential in decay.py with the stability-modulated form
│   # is_cross_session_reinforcement(memory, new_conversation_id) -> bool
│   #   Boundary check — only cross-session reinforcements count toward 
│   #   reinforcement_count growth
│
├── embeddings.py                   # Hybrid retrieval fallback (Design doc Section 13)
│   # embed_transcript_chunk(text) -> vector
│   # search_fallback(query_embedding, entity_id, budget_tokens) -> list[Chunk]
│   #   Only invoked when typed retrieval's max cosine similarity < threshold
│
├── plausibility.py                 # Adversarial defence (Design doc Section 15)
│   # check_plausibility(observation, domain_constraints) -> PlausibilityResult
│   #   Second Qwen call, caps base_confidence for boundary-violating claims
│
├── explainability.py                # Explainability trace (Design doc Section 16)
│   # parse_explain_block(raw_response) -> ExplainTrace
│   #   Extracts the [EXPLAIN]...[/EXPLAIN] block, strips it from user-facing 
│   #   text, stores structured trace linked to the message row
│
└── consolidation.py                 # Consolidation cycle (Design doc Section 17)
    # should_consolidate(entity_id) -> bool
    #   True every 5th completed session
    # run_consolidation(entity_id) -> ConsolidationResult
    #   Clusters stale low-confidence memories, synthesizes consolidated 
    #   summary via Qwen, supersedes originals
```

---

## 9. Backend — Evaluation Harness

```
backend/eval/
├── __init__.py
├── personas/
│   ├── persona_01_backup_priority.yaml     # Scripted 3-session arcs, 
│   ├── persona_02_cost_priority.yaml        # one file per synthetic persona,
│   ├── ...                                  # 20 total including the adversarial one
│   └── persona_20_adversarial.yaml          # Memory poisoning attempt case
│
├── ground_truth.py                # Labeled expected outcomes per persona:
│                                   # facts that should recall, decay, or supersede
│
├── baselines/
│   ├── system_a_no_memory.py       # Baseline: fresh context every session
│   ├── system_b_full_context.py     # Baseline: naive full transcript concat
│   └── system_c_naive_rag.py         # Baseline: embedding-only, no typed structure
│
├── metrics.py                       # Recall accuracy, forgetting correctness,
│                                    # contradiction handling %, token efficiency,
│                                    # cost per session, p50/p95 latency
│
├── run_eval.py                      # Single entrypoint: runs all 20 personas 
│                                    # against all 4 systems (A/B/C/D), 
│                                    # writes results
│
└── importance_validation.py          # 40-item human-labeled importance benchmark 
                                      # (Design doc Section 11.3), MAE against 
                                      # Qwen's self-scored importance
```

**Root-level output:**
```
BENCHMARKS.md                        # Auto-generated by run_eval.py — 
                                     # the results table judges see first
```

---

## 10. Second Persona — Generalizability Proof

```
backend/app/personas/
├── volta_prompt.py                 # Existing — energy advisor (Section 4, 
│                                   # original directory doc)
└── study_coach_prompt.py            # NEW — a study/exam coaching persona, 
                                     # sharing the identical memory engine, 
                                     # different domain entirely
                                     # Proves the memory core (importance, 
                                     # decay, hybrid retrieval, consolidation) 
                                     # is genuinely reusable infrastructure, 
                                     # not domain-coupled logic
```

Both personas share every file in `backend/app/memory/` untouched — only the system prompt template and domain-specific extraction guidance differ, demonstrated explicitly in the demo video's closing segment.

---

## 11. Deployment — Hosted Live Demo

```
deployment/
├── alibaba/                        # Existing (original directory doc Section 6)
└── live-demo/
    ├── public-url.md                # Durable hosted URL, kept live through 
    │                                # the full judging period
    └── rate-limiting.py              # Basic abuse protection for the public 
                                      # demo instance (judges and public both 
                                      # have access — must not be trivially 
                                      # breakable or cost-exhausting)
```


---

# ADDENDUM — Directory Additions for Final Push Features
**Added: June 2026**

```
backend/app/memory/
├── population_priors.py            # Design Doc §18
│   # get_cold_start_prior(signal_features) -> ProvisionalMemory | None
│   # rebuild_population_patterns()  -> None   (batch job, min-count enforced)
│
├── clarification.py                 # Design Doc §19
│   # compute_dialogue_action(memory) -> DialogueAction
│   #   Returns CLARIFY | STATE | SOFT_CHECK | IGNORE per the decision matrix
│
├── replay.py                        # Design Doc §20
│   # run_replay_cycle(entity_id) -> ReplayResult
│   #   Re-scores a sample of old memories against current full context
│
└── meta_memory.py                   # Design Doc §21
    # expected_topics_by_domain: dict[str, list[str]]
    # compute_known_gaps(entity_id, domain) -> list[str]

backend/eval/
├── self_tuning.py                    # Meta-optimization over decay/stability constants
│   # search_optimal_constants(param_grid) -> BestConstants
│   #   Runs the eval harness across a grid of lambda/growth-factor 
│   #   combinations, reports which constants maximize recall_accuracy 
│   #   + forgetting_correctness jointly
│
├── chaos/
│   ├── qwen_failure_injection.py     # Simulates API timeouts/errors mid-session
│   ├── db_failure_injection.py        # Simulates connection drops during writes
│   └── network_partition_test.py      # Simulates partial connectivity loss
│
└── concurrency/
    └── isolation_stress_test.py       # Many simultaneous entities, asserts 
                                       # zero cross-contamination of memory 
                                       # or retrieved context between entities

backend/tests/
└── coverage_report.py                 # Generates and publishes test coverage %
                                       # alongside mypy --strict static 
                                       # analysis results, both surfaced in 
                                       # the README as an engineering-maturity 
                                       # signal

benchmark-dataset/                     # Separate, citable public release 
├── personas/                          # (Productization Doc §10)
├── importance_validation_labels.json
├── LICENSE                            # Separate license for the dataset 
│                                      # itself (e.g. CC-BY), distinct from 
│                                      # the code's MIT license
├── CITATION.cff
└── README.md                          # Labeling methodology, intended use

docs/
├── human-eval-study/
│   ├── protocol.md                    # Study design (Productization Doc §9)
│   ├── raw-results.csv
│   └── participant-quotes.md
├── FAQ.md                             # Mirrors Document 11 §2
└── ONE_PAGER.md                       # Mirrors Document 11 §1
```


---

# ADDENDUM — MCP Server, Tool-Calling, Streaming, and Reproducibility
**Added: June 2026**

```
backend/
├── mcp/
│   ├── volta_memory_server.py       # Design Doc §22 — MCP server exposing 
│   │                                # get_memory_context, check_memory_confidence, 
│   │                                # write_memory as tools + the summary resource
│   ├── tool_schemas.py               # JSON schemas for all exposed tools/resources
│   └── conformance_tests.py           # Verifies the MCP server correctly implements 
│                                     # the protocol spec — run against any 
│                                     # MCP-compatible client, not just Qwen
│
├── app/chat/
│   ├── qwen_client.py                 # UPDATED: adds complete_stream() alongside 
│   │                                 # existing complete(), plus native tool-calling 
│   │                                 # support (Design Doc §23)
│   ├── dialogue_tools.py               # NEW — decide_dialogue_action tool schema 
│   │                                  # and handler (Design Doc §23)
│   └── streaming.py                    # NEW — SSE stream construction, tool-call 
│                                      # event surfacing mid-stream (Design Doc §24)
│
└── eval/
    └── mcp_vs_injection_benchmark.py    # NEW — the fifth system variant 
                                        # (E_mcp_agent_directed) comparison run, 
                                        # Design Doc §22.3

frontend/app/
└── components/
    └── StreamingMessage.tsx              # NEW — renders SSE token stream 
                                          # incrementally, shows tool-call 
                                          # indicators ("checking memory...") 
                                          # inline during generation

# Root-level reproducibility (elevated from nice-to-have to required)
docker-compose.yml                         # One-command full stack: postgres, 
                                           # backend, frontend, MCP server — 
                                           # `docker-compose up` and the demo 
                                           # is running, no manual setup steps
Makefile                                    # `make demo` — runs docker-compose up 
                                           # AND seeds nothing (memory starts 
                                           # empty by design) AND opens the 
                                           # frontend URL
```
