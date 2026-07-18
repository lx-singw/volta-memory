# Volta Memory — Database Schema
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

---

## Table of Contents
- [1. Schema Overview](#1-schema-overview)
- [2. memories](#2-memories)
- [3. conversations](#3-conversations)
- [4. messages](#4-messages)
- [5. Indexes](#5-indexes)
- [6. Seed Data](#6-seed-data)

---

## 1. Schema Overview

Three tables, deliberately minimal. Postgres (Alibaba RDS in production deployment, local Postgres for development). No multi-tenant complexity — a single `entity_id` column identifies the demo consumer throughout, since this submission doesn't need user account infrastructure.

---

## 2. memories

The core table — everything in Document 03's design lives here.

```sql
CREATE TABLE memories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,                  -- demo consumer identifier

  memory_type text NOT NULL CHECK (memory_type IN (
    'preference', 'fact', 'outcome', 'correction'
  )),

  observation text NOT NULL,                 -- plain-language statement
  evidence jsonb,                             -- optional: source message snippet

  base_confidence decimal(3,2) NOT NULL DEFAULT 0.75
    CHECK (base_confidence BETWEEN 0 AND 1),
  reinforcement_count integer NOT NULL DEFAULT 1,

  first_observed_at timestamptz NOT NULL DEFAULT now(),
  last_reinforced_at timestamptz NOT NULL DEFAULT now(),

  is_superseded boolean NOT NULL DEFAULT false,
  superseded_by_id uuid REFERENCES memories(id),

  source_session_id uuid,                     -- references conversations.id

  created_at timestamptz NOT NULL DEFAULT now()
);
```

**Note on `base_confidence` vs effective confidence:** the table stores the base value as last set at write/reinforcement time. The decayed `effective_confidence` used in retrieval (Document 03, Section 4) is computed at query time from `base_confidence` and `last_reinforced_at` — it is never stored, since storing it would require a background job to keep it current. Computing it on read keeps the system always-correct with zero staleness.

---

## 3. conversations

```sql
CREATE TABLE conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,                        -- null while session is active
  extraction_completed boolean NOT NULL DEFAULT false
                                                 -- true once end-of-session 
                                                 -- memory extraction has run
);
```

---

## 4. messages

```sql
CREATE TABLE messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES conversations(id),
  role text NOT NULL CHECK (role IN ('user', 'assistant')),
  content text NOT NULL,
  memory_context_used jsonb,                   -- snapshot of which memory IDs 
                                                  -- and scores were injected for 
                                                  -- this specific assistant 
                                                  -- response — critical for the 
                                                  -- transparency view and for 
                                                  -- proving the mechanism isn't 
                                                  -- simulated
  created_at timestamptz NOT NULL DEFAULT now()
);
```

---

## 5. Indexes

```sql
CREATE INDEX idx_memories_entity ON memories(entity_id)
  WHERE NOT is_superseded;

CREATE INDEX idx_memories_entity_type ON memories(entity_id, memory_type)
  WHERE NOT is_superseded;

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);

CREATE INDEX idx_conversations_entity ON conversations(entity_id, started_at DESC);
```

---

## 6. Seed Data

None required. The entire point of the demo is that the memory store starts empty and visibly accumulates across the three scripted sessions — seeding it would undermine the proof.


---

# ADDENDUM — Schema for Maximum-Depth Upgrades
**Added: June 2026**

---

## 7. memories (Revised)

The core table gains new columns to support self-scored importance, stability-based decay, and the consolidated memory type.

```sql
ALTER TABLE memories
  ADD COLUMN importance_score decimal(3,2) DEFAULT 0.5
    CHECK (importance_score BETWEEN 0 AND 1),
  ADD COLUMN importance_reasoning text,
  ADD COLUMN stability_s0 decimal(6,2) DEFAULT 1.0,
  ADD COLUMN plausibility_flag text DEFAULT 'plausible'
    CHECK (plausibility_flag IN ('plausible', 'boundary_violation', 'unverifiable')),
  ADD COLUMN consolidation_source_ids uuid[];  -- populated only for 
                                                 -- memory_type='consolidated'

ALTER TABLE memories DROP CONSTRAINT memories_memory_type_check;
ALTER TABLE memories ADD CONSTRAINT memories_memory_type_check
  CHECK (memory_type IN ('preference', 'fact', 'outcome', 'correction', 'consolidated'));
```

---

## 8. explain_traces (New)

```sql
CREATE TABLE explain_traces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL REFERENCES messages(id),
  referenced_memory_ids uuid[] NOT NULL,
  primary_influence_memory_id uuid REFERENCES memories(id),
  confidence_tier_choice text,
  counterfactual text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_explain_message ON explain_traces(message_id);
```

---

## 9. eval_runs (New)

```sql
CREATE TABLE eval_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_at timestamptz NOT NULL DEFAULT now(),
  system_variant text NOT NULL CHECK (system_variant IN (
    'A_no_memory', 'B_full_context', 'C_naive_rag', 'D_volta_memory'
  )),
  persona_id text NOT NULL,
  recall_accuracy decimal(5,4),
  forgetting_correctness decimal(5,4),
  contradiction_handling_rate decimal(5,4),
  avg_tokens_per_response integer,
  cost_usd decimal(10,6),
  latency_p50_ms integer,
  latency_p95_ms integer,
  raw_transcript jsonb
);

CREATE INDEX idx_eval_variant ON eval_runs(system_variant, persona_id);
```

---

## 10. importance_validation (New)

```sql
CREATE TABLE importance_validation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  observation_text text NOT NULL,
  human_importance_score decimal(3,2) NOT NULL,
  qwen_importance_score decimal(3,2) NOT NULL,
  absolute_error decimal(4,3) GENERATED ALWAYS AS 
    (abs(human_importance_score - qwen_importance_score)) STORED,
  created_at timestamptz NOT NULL DEFAULT now()
);
```

---

## 11. consolidation_log (New)

```sql
CREATE TABLE consolidation_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,
  triggered_at_session_count integer NOT NULL,
  memories_consolidated integer NOT NULL,
  consolidated_memory_id uuid REFERENCES memories(id),
  token_savings_estimate integer,
  created_at timestamptz NOT NULL DEFAULT now()
);
```


---

# ADDENDUM — Schema for Final Push Features
**Added: June 2026**

```sql
-- Population-level cold-start priors (Design Doc §18)
-- No foreign keys to individual entities — strictly aggregate
CREATE TABLE population_patterns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_feature text NOT NULL,          -- e.g. 'mentions_backup_loadshedding'
  correlated_outcome text NOT NULL,       -- e.g. 'confirmed_backup_primary'
  correlation_strength decimal(4,3) NOT NULL,
  contributing_entity_count integer NOT NULL CHECK (contributing_entity_count >= 20),
  computed_at timestamptz NOT NULL DEFAULT now()
);

-- Meta-memory known gaps (Design Doc §21)
CREATE TABLE meta_memory_gaps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,
  domain text NOT NULL,
  expected_topic text NOT NULL,
  gap_still_open boolean NOT NULL DEFAULT true,
  closed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Memory replay log (Design Doc §20)
CREATE TABLE replay_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id uuid NOT NULL REFERENCES memories(id),
  old_importance_score decimal(3,2) NOT NULL,
  new_importance_score decimal(3,2) NOT NULL,
  drift decimal(4,3) GENERATED ALWAYS AS 
    (abs(new_importance_score - old_importance_score)) STORED,
  replayed_at timestamptz NOT NULL DEFAULT now()
);

-- Add dialogue_action tracking to messages (Design Doc §19)
ALTER TABLE messages
  ADD COLUMN dialogue_action text
    CHECK (dialogue_action IN ('clarify', 'state', 'soft_check', 'ignore', NULL));

-- Self-tuning meta-optimization results
CREATE TABLE constant_search_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  param_set jsonb NOT NULL,               -- the tested lambda/growth-factor combo
  recall_accuracy decimal(5,4),
  forgetting_correctness decimal(5,4),
  joint_score decimal(5,4),                -- combined objective
  is_selected_best boolean DEFAULT false,
  run_at timestamptz NOT NULL DEFAULT now()
);
```

