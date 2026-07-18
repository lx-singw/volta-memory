"""Session lifecycle — start, message, end (triggers extraction)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.chat.qwen_client import get_qwen_client
from app.chat.tokenizer import count_tokens
from app.chat.volta_prompt import build_system_prompt
from app.config import get_settings
from app.db import get_connection
from app.memory.contradiction import detect_conflict, resolve
from app.memory.explainability import parse_explain_block
from app.memory.extraction import extract_observations
from app.memory.models import MemoryDraft, Session
from app.memory.plausibility import check_plausibility
from app.memory.store import list_memories, load_context, write_from_draft
from app.personas.study_coach_prompt import STUDY_COACH_PROMPT
from app.personas.volta_prompt import VOLTA_PROMPT


def _persona_prompt(persona: str) -> str:
    if persona == "study_coach":
        return STUDY_COACH_PROMPT
    return VOLTA_PROMPT


def start_session(entity_id: str, persona: str = "volta") -> Session:
    session_id = uuid4()
    now = datetime.now(timezone.utc)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations (id, entity_id, started_at)
            VALUES (%s, %s, %s)
            """,
            (session_id, entity_id, now),
        )

    return Session(id=session_id, entity_id=entity_id, persona=persona, started_at=now)


def _fetch_messages(conversation_id: UUID) -> list[dict[str, str]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def send_message(session_id: UUID, user_message: str, persona: str = "volta") -> dict:
    with get_connection() as conn:
        session_row = conn.execute(
            "SELECT entity_id FROM conversations WHERE id = %s AND ended_at IS NULL",
            (session_id,),
        ).fetchone()
        if not session_row:
            raise ValueError("Session not found or already ended")

        entity_id = session_row["entity_id"]
        conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (%s, %s, 'user', %s)
            """,
            (uuid4(), session_id, user_message),
        )

    memory_context = load_context(entity_id, query_context=user_message)
    system_prompt = build_system_prompt(memory_context, persona_template=_persona_prompt(persona))
    messages = _fetch_messages(session_id)

    raw_reply = get_qwen_client().complete(system_prompt, messages)
    explain = parse_explain_block(raw_reply)
    reply = explain.user_facing_text

    context_snapshot = [
        {
            "memory_id": str(item.memory.id),
            "observation": item.memory.observation,
            "effective_confidence": round(item.effective_confidence, 4),
            "tier": item.tier.value,
        }
        for item in memory_context.packed_memories
        if item.memory.id
    ]

    message_id = uuid4()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, memory_context_used)
            VALUES (%s, %s, 'assistant', %s, %s)
            """,
            (message_id, session_id, reply, json.dumps(context_snapshot)),
        )

        if explain.referenced_memory_ids:
            conn.execute(
                """
                INSERT INTO explain_traces (
                    id, message_id, referenced_memory_ids,
                    primary_influence_memory_id, confidence_tier_choice, counterfactual
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    message_id,
                    explain.referenced_memory_ids,
                    explain.primary_influence_memory_id,
                    explain.confidence_tier_choice,
                    explain.counterfactual,
                ),
            )

    tokens_used = count_tokens(system_prompt) + count_tokens(reply)
    return {
        "reply": reply,
        "memory_context_used": context_snapshot,
        "tokens_used": tokens_used,
        "message_id": str(message_id),
    }


def end_session(session_id: UUID) -> dict:
    settings = get_settings()
    now = datetime.now(timezone.utc)

    with get_connection() as conn:
        session_row = conn.execute(
            "SELECT entity_id FROM conversations WHERE id = %s",
            (session_id,),
        ).fetchone()
        if not session_row:
            raise ValueError("Session not found")

        entity_id = session_row["entity_id"]
        transcript_rows = conn.execute(
            """
            SELECT role, content FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()

    transcript = "\n".join(f"{row['role']}: {row['content']}" for row in transcript_rows)
    drafts = extract_observations(transcript)
    existing = list_memories(entity_id, include_superseded=False)
    written = []

    for draft in drafts:
        if draft.importance_score is None:
            from app.memory.importance import score_importance
            imp = score_importance(draft.observation)
            draft.importance_score = imp.importance_score
            draft.importance_reasoning = imp.importance_reasoning

        if settings.plausibility_check_enabled:
            result = check_plausibility(draft.observation)
            if result.capped_confidence is not None:
                draft.base_confidence = min(draft.base_confidence, result.capped_confidence)

        conflict = detect_conflict(draft.observation, existing)
        if conflict and conflict.id:
            _, new_memory = resolve(conflict, draft.observation, entity_id, session_id)
            written.append(new_memory)
            continue

        memory = write_from_draft(entity_id, draft, source_session_id=session_id)
        written.append(memory)

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE conversations
            SET ended_at = %s, extraction_completed = true
            WHERE id = %s
            """,
            (now, session_id),
        )

    return {
        "session_id": str(session_id),
        "ended_at": now.isoformat(),
        "memories_written": [
            {
                "memory_type": memory.memory_type.value,
                "observation": memory.observation,
                "confidence": memory.base_confidence,
            }
            for memory in written
        ],
    }
