-- Migration: Add transcript_chunks and population_patterns tables

ALTER TABLE memories ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'individual';

CREATE TABLE IF NOT EXISTS transcript_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  text text NOT NULL,
  embedding vector(1536) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS population_patterns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_keyword text NOT NULL UNIQUE,
  inferred_observation text NOT NULL,
  inferred_type text NOT NULL,
  probability decimal(3,2) NOT NULL DEFAULT 0.5,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Seed cold-start priors for Volta
INSERT INTO population_patterns (signal_keyword, inferred_observation, inferred_type, probability)
VALUES 
  ('backup', 'Prioritizes load-shedding backup duration over cost savings', 'preference', 0.65)
ON CONFLICT (signal_keyword) DO NOTHING;

INSERT INTO population_patterns (signal_keyword, inferred_observation, inferred_type, probability)
VALUES 
  ('loadshedding', 'Prioritizes load-shedding backup duration over cost savings', 'preference', 0.65)
ON CONFLICT (signal_keyword) DO NOTHING;

INSERT INTO population_patterns (signal_keyword, inferred_observation, inferred_type, probability)
VALUES 
  ('bill', 'Main driver is reducing monthly electricity bill and achieving cost savings', 'preference', 0.60)
ON CONFLICT (signal_keyword) DO NOTHING;

INSERT INTO population_patterns (signal_keyword, inferred_observation, inferred_type, probability)
VALUES 
  ('cost', 'Main driver is reducing monthly electricity bill and achieving cost savings', 'preference', 0.60)
ON CONFLICT (signal_keyword) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_chunks_entity ON transcript_chunks(entity_id);
