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
    user_reply = ""
    latency_ms = 0
    cost_usd = 0.0

    if check_database():
        try:
            # 1. Clear existing memories to ensure a clean run
            with get_connection() as conn:
                conn.execute("DELETE FROM memories WHERE entity_id = %s", (entity_id,))
                conn.execute("DELETE FROM conversations WHERE entity_id = %s", (entity_id,))
                conn.execute("DELETE FROM transcript_chunks WHERE entity_id = %s", (entity_id,))

            from uuid import uuid4
            from datetime import datetime, timezone, timedelta
            dummy_session_id = uuid4()
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO conversations (id, entity_id, started_at) VALUES (%s, %s, %s)",
                    (dummy_session_id, entity_id, datetime.now(timezone.utc) - timedelta(days=4))
                )

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
                # We can simulate different sessions by splitting on session boundary indicator if present,
                # or just extract observations from the past transcript block.
                # To simulate time offsets, we can set them to have been created 3 days ago.
                simulated_time = datetime.now(timezone.utc) - timedelta(days=3)
                
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
                        _, new_mem = resolve(conflict, draft, entity_id, dummy_session_id)
                        existing.append(new_mem)
                        continue

                    mem = write_from_draft(entity_id, draft, source_session_id=dummy_session_id, timestamp=simulated_time)
                    existing.append(mem)
                    
                    # Store as transcript chunk for fallback comparison
                    from app.memory.embeddings import store_transcript_chunk
                    store_transcript_chunk(entity_id, dummy_session_id, draft.observation)

            # 4. Perform retrieval for the current message
            import time
            from app.chat.volta_prompt import build_system_prompt
            from app.chat.qwen_client import get_qwen_client
            from app.chat.tokenizer import count_tokens
            
            memories = list_memories(entity_id, include_superseded=False)
            context = build_memory_context(entity_id, memories, query_context=user_message)
            packed = [item.memory.observation for item in context.packed_memories]
            
            system_prompt = build_system_prompt(context)
            messages = [{"role": "user", "content": user_message}]
            
            t0 = time.monotonic()
            reply_raw = get_qwen_client().complete_with_tools(system_prompt, messages, entity_id=entity_id)
            latency_ms = int((time.monotonic() - t0) * 1000)
            
            from app.memory.explainability import parse_explain_block
            explain = parse_explain_block(reply_raw)
            user_reply = explain.user_facing_text
            
            tokens_used = count_tokens(system_prompt) + count_tokens(user_reply)
            cost_usd = (tokens_used / 1000.0) * 0.002
            
        except Exception as e:
            logger.error(f"Error in System D respond: {e}", exc_info=True)
            user_reply = f"Error in respond: {e}"

    return {
        "reply": user_reply,
        "memory_context_used": [{"observation": obs} for obs in packed],
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "latency_ms": latency_ms
    }
