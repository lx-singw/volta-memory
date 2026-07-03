-- Volta Memory initial schema (docs/04 + addendum)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,
  memory_type text NOT NULL CHECK (memory_type IN (
    'preference', 'fact', 'outcome', 'correction', 'consolidated'
  )),
  observation text NOT NULL,
  evidence jsonb,
  base_confidence decimal(3,2) NOT NULL DEFAULT 0.75
    CHECK (base_confidence BETWEEN 0 AND 1),
  reinforcement_count integer NOT NULL DEFAULT 1,
  first_observed_at timestamptz NOT NULL DEFAULT now(),
  last_reinforced_at timestamptz NOT NULL DEFAULT now(),
  is_superseded boolean NOT NULL DEFAULT false,
  superseded_by_id uuid REFERENCES memories(id),
  source_session_id uuid,
  importance_score decimal(3,2) DEFAULT 0.5
    CHECK (importance_score BETWEEN 0 AND 1),
  importance_reasoning text,
  stability_s0 decimal(6,2) DEFAULT 1.0,
  plausibility_flag text DEFAULT 'plausible'
    CHECK (plausibility_flag IN ('plausible', 'boundary_violation', 'unverifiable')),
  consolidation_source_ids uuid[],
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  extraction_completed boolean NOT NULL DEFAULT false
);

ALTER TABLE memories
  ADD CONSTRAINT fk_memories_source_session
  FOREIGN KEY (source_session_id) REFERENCES conversations(id)
  DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES conversations(id),
  role text NOT NULL CHECK (role IN ('user', 'assistant')),
  content text NOT NULL,
  memory_context_used jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS explain_traces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL REFERENCES messages(id),
  referenced_memory_ids uuid[] NOT NULL,
  primary_influence_memory_id uuid REFERENCES memories(id),
  confidence_tier_choice text,
  counterfactual text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eval_runs (
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

CREATE TABLE IF NOT EXISTS importance_validation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  observation_text text NOT NULL,
  human_importance_score decimal(3,2) NOT NULL,
  qwen_importance_score decimal(3,2) NOT NULL,
  absolute_error decimal(4,3) GENERATED ALWAYS AS
    (abs(human_importance_score - qwen_importance_score)) STORED,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consolidation_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,
  triggered_at_session_count integer NOT NULL,
  memories_consolidated integer NOT NULL,
  consolidated_memory_id uuid REFERENCES memories(id),
  token_savings_estimate integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memories_entity ON memories(entity_id)
  WHERE NOT is_superseded;

CREATE INDEX IF NOT EXISTS idx_memories_entity_type ON memories(entity_id, memory_type)
  WHERE NOT is_superseded;

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_conversations_entity ON conversations(entity_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_explain_message ON explain_traces(message_id);

CREATE INDEX IF NOT EXISTS idx_eval_variant ON eval_runs(system_variant, persona_id);
