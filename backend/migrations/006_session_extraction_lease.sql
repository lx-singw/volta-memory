-- A Function Compute request can be terminated before Python's exception path
-- runs.  Lease ownership lets a later retry recover that interrupted session
-- without allowing the stale invocation to write a duplicate receipt.
ALTER TABLE session_extraction_results
  ADD COLUMN IF NOT EXISTS processing_token uuid,
  ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_session_extraction_processing_lease
  ON session_extraction_results (lease_expires_at)
  WHERE extraction_status = 'processing';
