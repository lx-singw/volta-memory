-- Volta Memory product foundation: tenant isolation, auditable lifecycle, and verified provenance.
-- The migration is deliberately additive so existing entity_id-based integrations remain valid.

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz
);

CREATE TABLE IF NOT EXISTS entities (
  id text PRIMARY KEY,
  owner_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  entity_type text NOT NULL DEFAULT 'anonymous'
    CHECK (entity_type IN ('showcase', 'anonymous', 'user')),
  is_read_only boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Preserve every existing tenant before new authenticated routes begin using entities.
INSERT INTO entities (id, entity_type, is_read_only)
SELECT DISTINCT source.entity_id,
  CASE WHEN source.entity_id IN ('demo-consumer-1', 'showcase') THEN 'showcase' ELSE 'anonymous' END,
  source.entity_id IN ('demo-consumer-1', 'showcase')
FROM (
  SELECT entity_id FROM memories
  UNION
  SELECT entity_id FROM conversations
  UNION
  SELECT entity_id FROM transcript_chunks
) AS source
WHERE source.entity_id IS NOT NULL
ON CONFLICT (id) DO NOTHING;

ALTER TABLE memories
  ADD COLUMN IF NOT EXISTS profile_slot text NOT NULL DEFAULT 'none'
  CHECK (profile_slot IN ('monthly_bill', 'backup_priority', 'roof_home', 'budget', 'tariff', 'none'));

-- Best-effort metadata backfill; source data remains authoritative and can be revised later.
UPDATE memories
SET profile_slot = CASE
  WHEN evidence->>'profile_slot' IN ('monthly_bill', 'backup_priority', 'roof_home', 'budget', 'tariff', 'none')
    THEN evidence->>'profile_slot'
  WHEN observation ~* '(monthly )?bill|electricity bill' THEN 'monthly_bill'
  WHEN observation ~* 'backup|load.shedding|lights on' THEN 'backup_priority'
  WHEN observation ~* 'roof|home|house|flat|duplex' THEN 'roof_home'
  WHEN observation ~* 'budget|afford|spend' THEN 'budget'
  WHEN observation ~* 'tariff|rate|time.of.use' THEN 'tariff'
  ELSE 'none'
END
WHERE profile_slot = 'none';

CREATE TABLE IF NOT EXISTS auth_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_hash text NOT NULL UNIQUE,
  csrf_token_hash text NOT NULL,
  entity_id text NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_active_token
  ON auth_sessions(token_hash, expires_at) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS auth_login_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_hash text NOT NULL UNIQUE,
  email text NOT NULL,
  entity_id text REFERENCES entities(id) ON DELETE SET NULL,
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_provenance (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id uuid NOT NULL UNIQUE REFERENCES memories(id) ON DELETE CASCADE,
  original_user_message_id uuid REFERENCES messages(id) ON DELETE SET NULL,
  source_session_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
  source_turn_index integer,
  source_quote text,
  source_verified boolean NOT NULL DEFAULT false,
  is_constraint boolean,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (source_turn_index IS NULL OR source_turn_index > 0)
);

CREATE INDEX IF NOT EXISTS idx_memory_provenance_memory ON memory_provenance(memory_id);

CREATE TABLE IF NOT EXISTS memory_relations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_memory_id uuid NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  target_memory_id uuid NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  relation_type text NOT NULL CHECK (relation_type IN ('supersedes', 'reinforces', 'consolidates')),
  source_session_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_memory_id, target_memory_id, relation_type),
  CHECK (source_memory_id <> target_memory_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_relations_source ON memory_relations(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_relations_target ON memory_relations(target_memory_id);

CREATE TABLE IF NOT EXISTS memory_lifecycle_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id text NOT NULL,
  session_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
  action text NOT NULL CHECK (action IN ('created', 'reinforced', 'corrected', 'excluded', 'reconfirmed')),
  before_memory_id uuid REFERENCES memories(id) ON DELETE SET NULL,
  after_memory_id uuid REFERENCES memories(id) ON DELETE SET NULL,
  display_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_lifecycle_entity ON memory_lifecycle_events(entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_lifecycle_session ON memory_lifecycle_events(session_id);

CREATE TABLE IF NOT EXISTS session_extraction_results (
  session_id uuid PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
  entity_id text NOT NULL,
  idempotency_key text NOT NULL,
  extraction_status text NOT NULL CHECK (extraction_status IN ('processing', 'completed', 'failed')),
  lifecycle_result jsonb,
  error_details text,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (entity_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_session_extraction_status ON session_extraction_results(extraction_status, updated_at);

-- Backfill only quotes that can be demonstrated to come from a user message.
INSERT INTO memory_provenance (
  memory_id, original_user_message_id, source_session_id, source_turn_index,
  source_quote, source_verified, is_constraint
)
SELECT
  m.id,
  verified.message_id,
  m.source_session_id,
  CASE WHEN verified.message_id IS NOT NULL THEN claimed.source_turn_index ELSE NULL END,
  CASE WHEN verified.message_id IS NOT NULL THEN claimed.source_quote ELSE NULL END,
  verified.message_id IS NOT NULL,
  claimed.is_constraint
FROM memories m
LEFT JOIN LATERAL (
  -- Older correction records used both top-level evidence and nested
  -- correction/source objects.  Normalize those known formats without ever
  -- treating their raw JSON as client-facing proof.
  SELECT
    NULLIF(COALESCE(
      m.evidence->>'source_quote',
      m.evidence #>> '{source,quote}',
      m.evidence #>> '{provenance,source_quote}',
      m.evidence #>> '{correction,source_quote}',
      m.evidence #>> '{supersedes,source_quote}',
      m.evidence #>> '{previous,source_quote}'
    ), '') AS source_quote,
    CASE
      WHEN COALESCE(
        m.evidence->>'source_turn_index',
        m.evidence #>> '{source,turn_index}',
        m.evidence #>> '{provenance,source_turn_index}',
        m.evidence #>> '{correction,source_turn_index}',
        m.evidence #>> '{supersedes,source_turn_index}',
        m.evidence #>> '{previous,source_turn_index}'
      ) ~ '^[0-9]+$'
        THEN COALESCE(
          m.evidence->>'source_turn_index',
          m.evidence #>> '{source,turn_index}',
          m.evidence #>> '{provenance,source_turn_index}',
          m.evidence #>> '{correction,source_turn_index}',
          m.evidence #>> '{supersedes,source_turn_index}',
          m.evidence #>> '{previous,source_turn_index}'
        )::integer
      ELSE NULL
    END AS source_turn_index,
    CASE
      WHEN lower(COALESCE(
        m.evidence->>'is_constraint',
        m.evidence #>> '{source,is_constraint}',
        m.evidence #>> '{provenance,is_constraint}'
      )) IN ('true', 'false')
        THEN COALESCE(
          m.evidence->>'is_constraint',
          m.evidence #>> '{source,is_constraint}',
          m.evidence #>> '{provenance,is_constraint}'
        )::boolean
      ELSE NULL
    END AS is_constraint
) AS claimed ON true
LEFT JOIN LATERAL (
  SELECT msg.id AS message_id
  FROM (
    SELECT id, role, content,
      row_number() OVER (ORDER BY created_at ASC, id ASC) AS turn_index
    FROM messages
    WHERE conversation_id = m.source_session_id
  ) AS msg
  WHERE msg.role = 'user'
    AND claimed.source_quote IS NOT NULL
    AND position(claimed.source_quote IN msg.content) > 0
    AND (claimed.source_turn_index IS NULL OR msg.turn_index = claimed.source_turn_index)
  ORDER BY msg.turn_index ASC
  LIMIT 1
) AS verified ON true
ON CONFLICT (memory_id) DO NOTHING;

INSERT INTO memory_relations (source_memory_id, target_memory_id, relation_type, source_session_id)
SELECT id, superseded_by_id, 'supersedes', source_session_id
FROM memories
WHERE superseded_by_id IS NOT NULL
ON CONFLICT (source_memory_id, target_memory_id, relation_type) DO NOTHING;

INSERT INTO memory_lifecycle_events (entity_id, session_id, action, before_memory_id, after_memory_id, display_payload)
SELECT
  old.entity_id,
  replacement.source_session_id,
  'corrected',
  old.id,
  replacement.id,
  jsonb_build_object('backfilled', true)
FROM memories old
JOIN memories replacement ON replacement.id = old.superseded_by_id
WHERE old.superseded_by_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM memory_lifecycle_events event
    WHERE event.before_memory_id = old.id
      AND event.after_memory_id = replacement.id
      AND event.action = 'corrected'
  );
