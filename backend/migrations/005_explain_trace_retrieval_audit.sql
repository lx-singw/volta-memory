-- Persist the exact retrieval decision for every answer so an explanation can
-- be replayed after the response is no longer in the browser.
ALTER TABLE explain_traces
  ADD COLUMN IF NOT EXISTS available_memory_ids uuid[] NOT NULL DEFAULT '{}';

ALTER TABLE explain_traces
  ADD COLUMN IF NOT EXISTS exclusion_trace jsonb NOT NULL DEFAULT '[]'::jsonb;
