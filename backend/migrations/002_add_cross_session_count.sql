-- Migration: Add cross_session_reinforcement_count to memories table

ALTER TABLE memories ADD COLUMN IF NOT EXISTS cross_session_reinforcement_count integer NOT NULL DEFAULT 1;
