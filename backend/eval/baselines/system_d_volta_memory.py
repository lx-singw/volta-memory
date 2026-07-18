"""Baseline D — Volta typed memory engine."""

from __future__ import annotations

import logging
from app.db import check_database, get_connection
from app.memory.extraction import extract_observations
from app.memory.contradiction import detect_conflict, resolve
from app.memory.plausibility import check_plausibility
from app.memory.store import list_memories, write_from_draft
from app.memory.retrieval import build_memory_context
from app.memory.importance import score_importance
from app.config import get_settings

logger = logging.getLogger(__name__)


def respond(entity_id: str, transcript: str, user_message: str) -> dict:
    packed: list[str] = []
    tokens_used = 0
    settings = get_settings()

    if check_database():
        try:
            # 1. Clear existing memories to ensure a clean run
            with get_connection() as conn:
                conn.execute("DELETE FROM memories WHERE entity_id = %s", (entity_id,))
                conn.execute("DELETE FROM conversations WHERE entity_id = %s", (entity_id,))

            # 2. Extract past transcript (all content before the final user message)
            lines = [line.strip() for line in transcript.splitlines() if line.strip()]
            final_user_line = f"user: {user_message}"
            past_lines = []
            for line in lines:
                if line.lower() == final_user_line.lower():
                    break
                past_lines.append(line)
            
            past_transcript = "\n".join(past_lines)

            # 3. Simulate end_session extraction for past sessions
            if past_transcript.strip():
                drafts = extract_observations(past_transcript)
                existing = []
                for draft in drafts:
                    if draft.importance_score is None:
                        imp = score_importance(draft.observation)
                        draft.importance_score = imp.importance_score
                        draft.importance_reasoning = imp.importance_reasoning

                    if settings.plausibility_check_enabled:
                        res = check_plausibility(draft.observation)
                        if res.capped_confidence is not None:
                            draft.base_confidence = min(draft.base_confidence, res.capped_confidence)

                    conflict = detect_conflict(draft.observation, existing)
                    if conflict and conflict.id:
                        _, new_mem = resolve(conflict, draft.observation, entity_id, None)
                        existing.append(new_mem)
                        continue

                    mem = write_from_draft(entity_id, draft, source_session_id=None)
                    existing.append(mem)

            # 4. Perform retrieval for the current message
            memories = list_memories(entity_id, include_superseded=False)
            context = build_memory_context(entity_id, memories, query_context=user_message)
            packed = [item.memory.observation for item in context.packed_memories]
            tokens_used = context.tokens_used
        except Exception as e:
            logger.error(f"Error in System D respond: {e}", exc_info=True)

    return {
        "reply": f"(volta memory) {user_message}",
        "memory_context_used": [{"observation": obs} for obs in packed],
        "tokens_used": tokens_used,
        "cost_usd": 0.014,
    }
