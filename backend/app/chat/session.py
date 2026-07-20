"""Session lifecycle — start, message, end (triggers extraction)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.chat.qwen_client import get_qwen_client, qwen_invocation_budget
from app.chat.tokenizer import count_tokens
from app.chat.volta_prompt import build_system_prompt
from app.config import get_settings
from app.db import get_connection
from app.memory.contradiction import detect_conflict, resolve
from app.memory.explainability import parse_explain_block
from app.memory.extraction import ExtractionFailure, extract_observations
from app.memory.models import Memory, MemoryDraft, Session
from app.memory.provenance import persist_lifecycle_event, persist_provenance, persist_relation
from app.memory.plausibility import check_plausibility
from app.memory.store import list_memories, load_context, update_memory_reinforcement, write_from_draft
from app.personas.study_coach_prompt import STUDY_COACH_PROMPT
from app.personas.volta_prompt import VOLTA_PROMPT


logger = logging.getLogger(__name__)


def _persona_prompt(persona: str) -> str:
    if persona == "study_coach":
        return STUDY_COACH_PROMPT
    return VOLTA_PROMPT


def start_session(entity_id: str, persona: str = "volta") -> Session:
    session_id = uuid4()
    from app.utils.clock import get_now
    now = get_now()

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


def _build_excluded_memory_trace(entity_id: str, packed_memory_ids: set[str]) -> list[dict[str, str]]:
    """Describe only real retrieval exclusions for the current reply.

    A retained record is not automatically "not used" in every answer.  This
    function records a reason only when the storage/retrieval path actually
    excluded it from the prompt: supersession, confidence decay, or the token
    budget.  The API serializer later attaches the public memory DTO.
    """
    from app.memory.decay import apply_decay

    settings = get_settings()
    excluded: list[dict[str, str]] = []
    try:
        memories = list_memories(entity_id, include_superseded=True)
    except Exception:
        # An explainability enhancement must not make an otherwise successful
        # answer fail after it has already been generated.
        return excluded
    for memory in memories:
        if not memory.id or str(memory.id) in packed_memory_ids:
            continue
        if memory.is_superseded:
            reason = "Superseded by a newer confirmed memory; retained for audit."
        elif apply_decay(memory) < settings.confidence_surface_threshold:
            reason = "Below the confidence threshold; needs reconfirmation before advice."
        else:
            reason = "Not selected within the configured memory budget for this answer."
        excluded.append({"memory_id": str(memory.id), "reason": reason})
    return excluded


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

    memory_context = load_context(entity_id, query_context=user_message, persona=persona)
    system_prompt = build_system_prompt(memory_context, persona_template=_persona_prompt(persona))
    messages = _fetch_messages(session_id)

    raw_reply = get_qwen_client().complete_with_tools(system_prompt, messages, entity_id=entity_id)
    explain = parse_explain_block(raw_reply)
    reply = explain.user_facing_text

    context_snapshot = [
        {
            "memory_id": str(item.memory.id),
            "observation": item.memory.observation,
            "effective_confidence": round(item.effective_confidence, 4),
            "tier": item.tier.value,
            "evidence": item.memory.evidence,
        }
        for item in memory_context.packed_memories
        if item.memory.id
    ]
    packed_memory_ids = {item["memory_id"] for item in context_snapshot}
    referenced_memory_ids = [str(memory_id) for memory_id in explain.referenced_memory_ids]
    used_memory_ids = [memory_id for memory_id in referenced_memory_ids if memory_id in packed_memory_ids]
    available_memory_ids = [item["memory_id"] for item in context_snapshot if item["memory_id"] not in used_memory_ids]
    excluded_memories = _build_excluded_memory_trace(entity_id, packed_memory_ids)
    packed_uuid_by_id = {str(item.memory.id): item.memory.id for item in memory_context.packed_memories if item.memory.id}
    used_memory_uuids = [packed_uuid_by_id[memory_id] for memory_id in used_memory_ids]
    available_memory_uuids = [packed_uuid_by_id[memory_id] for memory_id in available_memory_ids]
    primary_memory_id = explain.primary_influence_memory_id if str(explain.primary_influence_memory_id) in used_memory_ids else None

    message_id = uuid4()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, memory_context_used)
            VALUES (%s, %s, 'assistant', %s, %s)
            """,
            (message_id, session_id, reply, json.dumps(context_snapshot)),
        )

        conn.execute(
            """
            INSERT INTO explain_traces (
                id, message_id, referenced_memory_ids,
                primary_influence_memory_id, confidence_tier_choice, counterfactual,
                available_memory_ids, exclusion_trace
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(),
                message_id,
                used_memory_uuids,
                primary_memory_id,
                explain.confidence_tier_choice,
                explain.counterfactual,
                available_memory_uuids,
                json.dumps(excluded_memories),
            ),
        )

    tokens_used = count_tokens(system_prompt) + count_tokens(reply)
    explain_trace = {
        "referenced_memory_ids": referenced_memory_ids,
        "primary_influence_memory_id": str(primary_memory_id) if primary_memory_id else None,
        "confidence_tier_choice": explain.confidence_tier_choice,
        "counterfactual": explain.counterfactual,
        "used_memory_ids": used_memory_ids,
        "available_memory_ids": available_memory_ids,
        "excluded_memories": excluded_memories,
    }
    exclusion_reason_counts: dict[str, int] = {}
    for item in excluded_memories:
        reason = item["reason"]
        exclusion_reason_counts[reason] = exclusion_reason_counts.get(reason, 0) + 1
    logger.info(
        "volta_event=%s",
        json.dumps(
            {
                "event": "message_retrieval",
                "session_id": str(session_id),
                "retrieval_count": len(context_snapshot),
                "used_memory_count": len(used_memory_ids),
                "available_memory_count": len(available_memory_ids),
                "exclusion_reason_counts": exclusion_reason_counts,
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
    )

    return {
        "reply": reply,
        "memory_context_used": context_snapshot,
        "tokens_used": tokens_used,
        "message_id": str(message_id),
        "known_gaps": memory_context.known_gaps,
        "explain_trace": explain_trace,
    }


def send_message_stream(session_id: UUID, user_message: str, persona: str = "volta"):
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

    memory_context = load_context(entity_id, query_context=user_message, persona=persona)
    system_prompt = build_system_prompt(memory_context, persona_template=_persona_prompt(persona))
    messages = _fetch_messages(session_id)

    full_response_content = []
    for chunk in get_qwen_client().complete_stream(system_prompt, messages):
        full_response_content.append(chunk)
        yield chunk

    reply = "".join(full_response_content)
    explain = parse_explain_block(reply)
    user_reply = explain.user_facing_text

    context_snapshot = [
        {
            "memory_id": str(item.memory.id),
            "observation": item.memory.observation,
            "effective_confidence": round(item.effective_confidence, 4),
            "tier": item.tier.value,
            "evidence": item.memory.evidence,
        }
        for item in memory_context.packed_memories
        if item.memory.id
    ]
    packed_memory_ids = {item["memory_id"] for item in context_snapshot}
    referenced_memory_ids = [str(memory_id) for memory_id in explain.referenced_memory_ids]
    used_memory_ids = [memory_id for memory_id in referenced_memory_ids if memory_id in packed_memory_ids]
    available_memory_ids = [item["memory_id"] for item in context_snapshot if item["memory_id"] not in used_memory_ids]
    excluded_memories = _build_excluded_memory_trace(entity_id, packed_memory_ids)
    packed_uuid_by_id = {str(item.memory.id): item.memory.id for item in memory_context.packed_memories if item.memory.id}
    used_memory_uuids = [packed_uuid_by_id[memory_id] for memory_id in used_memory_ids]
    available_memory_uuids = [packed_uuid_by_id[memory_id] for memory_id in available_memory_ids]
    primary_memory_id = explain.primary_influence_memory_id if str(explain.primary_influence_memory_id) in used_memory_ids else None

    message_id = uuid4()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, memory_context_used)
            VALUES (%s, %s, 'assistant', %s, %s)
            """,
            (message_id, session_id, user_reply, json.dumps(context_snapshot)),
        )

        conn.execute(
            """
            INSERT INTO explain_traces (
                id, message_id, referenced_memory_ids,
                primary_influence_memory_id, confidence_tier_choice, counterfactual,
                available_memory_ids, exclusion_trace
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(),
                message_id,
                used_memory_uuids,
                primary_memory_id,
                explain.confidence_tier_choice,
                explain.counterfactual,
                available_memory_uuids,
                json.dumps(excluded_memories),
            ),
        )


class SessionEndingInProgress(ValueError):
    """A concurrent end request already owns the immutable extraction result."""


class SessionExtractionUnavailable(ValueError):
    """The session stays open when memory extraction cannot be completed safely."""


def _decode_json(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return {}


def _memory_snapshot(memory: Memory) -> dict:
    """Small serializable snapshot used for receipts and event audit payloads."""
    return {
        "id": str(memory.id),
        "observation": memory.observation,
        "memory_type": memory.memory_type.value,
        "profile_slot": memory.profile_slot.value,
        "confidence": round(memory.base_confidence, 4),
    }


def _write_reinforcement_version(
    conn,
    *,
    target: Memory,
    draft: MemoryDraft,
    entity_id: str,
    session_id: UUID,
) -> Memory:
    """Persist a new evidence-backed version for a reconfirmed memory.

    Reinforcement is not an invented graph link: the prior version is retained
    for audit, the new confirmation owns the new verified quote, and the only
    active version is the latest one used for future advice.
    """
    from app.memory.decay import reinforce
    from app.memory.store import supersede

    updated = reinforce(target, session_id=session_id)
    version_draft = draft.model_copy(deep=True)
    version_draft.memory_type = target.memory_type
    version_draft.base_confidence = updated.base_confidence
    version_draft.importance_score = target.importance_score or draft.importance_score
    version_draft.importance_reasoning = target.importance_reasoning or draft.importance_reasoning
    version_draft.profile_slot = target.profile_slot

    new_memory = write_from_draft(
        entity_id,
        version_draft,
        source_session_id=session_id,
        conn=conn,
    )
    update_memory_reinforcement(
        memory_id=new_memory.id,
        reinforcement_count=updated.reinforcement_count,
        cross_session_count=updated.cross_session_reinforcement_count,
        base_confidence=updated.base_confidence,
        last_reinforced_at=updated.last_reinforced_at,
        conn=conn,
    )
    new_memory.reinforcement_count = updated.reinforcement_count
    new_memory.cross_session_reinforcement_count = updated.cross_session_reinforcement_count
    new_memory.last_reinforced_at = updated.last_reinforced_at
    supersede(target.id, new_memory, conn=conn)
    persist_provenance(conn, new_memory, session_id)
    persist_relation(conn, target.id, new_memory.id, "reinforces", session_id)
    return new_memory


def _persist_reinforcement_lifecycle_event(
    conn,
    *,
    entity_id: str,
    session_id: UUID,
    target: Memory,
    updated: Memory,
    change: dict,
) -> None:
    """Record the active replacement, never the retained predecessor."""
    persist_lifecycle_event(
        conn,
        entity_id=entity_id,
        session_id=session_id,
        action="reinforced",
        before_memory_id=target.id,
        after_memory_id=updated.id,
        display_payload=change,
    )


def _processing_lease_is_stale(result_row, now: datetime, lease_seconds: int) -> bool:
    """Return whether a processing lease can be safely taken over.

    Rows created before the lease migration have no expiry, so their
    ``updated_at`` acts as a backwards-compatible lease start time.
    """
    expires_at = result_row.get("lease_expires_at")
    reference_time = expires_at or result_row.get("updated_at")
    if reference_time is None:
        return True
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if expires_at is not None:
        return reference_time <= now
    return reference_time + timedelta(seconds=max(1, lease_seconds)) <= now


def _mark_extraction_failed(session_id: UUID, reason: str, processing_token: UUID) -> None:
    """Mark only the caller's active lease as failed.

    A timed-out Function Compute invocation may resume after a retry recovered
    the row.  The token condition prevents that stale worker from overwriting
    the retry's status or receipt.
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE session_extraction_results
            SET extraction_status = 'failed', error_details = %s, updated_at = now(),
                processing_token = NULL, lease_expires_at = NULL
            WHERE session_id = %s
              AND extraction_status = 'processing'
              AND processing_token = %s
            """,
            (reason[:500], session_id, processing_token),
        )


def end_session(session_id: UUID, idempotency_key: str | None = None) -> dict:
    """End a session without allowing all Qwen work to outlive the FC request."""
    settings = get_settings()
    with qwen_invocation_budget(settings.function_invocation_budget_seconds):
        return _end_session_impl(session_id, idempotency_key)


def _end_session_impl(session_id: UUID, idempotency_key: str | None = None) -> dict:
    """End a session with an idempotent, auditable memory write transaction.

    Extraction happens outside the database transaction, but all memory writes,
    provenance, relations, lifecycle events, and completed-session state commit
    together. A Qwen outage writes no user memory and leaves the chat recoverable.
    """
    settings = get_settings()
    from app.utils.clock import get_now

    idempotency_key = (idempotency_key or f"session:{session_id}").strip()[:200]
    processing_token = uuid4()
    lease_started_at = get_now()
    lease_expires_at = lease_started_at + timedelta(
        seconds=max(1, settings.session_extraction_lease_seconds)
    )
    with get_connection() as conn:
        session_row = conn.execute(
            "SELECT entity_id, ended_at FROM conversations WHERE id = %s",
            (session_id,),
        ).fetchone()
        if not session_row:
            raise ValueError("Session not found")

        entity_id = session_row["entity_id"]
        result_row = conn.execute(
            """
            SELECT extraction_status, lifecycle_result, error_details, updated_at,
                   processing_token, lease_expires_at
            FROM session_extraction_results
            WHERE session_id = %s
            FOR UPDATE
            """,
            (session_id,),
        ).fetchone()
        if result_row and result_row["extraction_status"] == "completed":
            return _decode_json(result_row["lifecycle_result"])
        if result_row and result_row["extraction_status"] == "processing":
            if not _processing_lease_is_stale(
                result_row, lease_started_at, settings.session_extraction_lease_seconds
            ):
                raise SessionEndingInProgress(
                    "Memory extraction is already in progress for this session."
                )

        if result_row:
            conn.execute(
                """
                UPDATE session_extraction_results
                SET extraction_status = 'processing', idempotency_key = %s,
                    processing_token = %s, lease_expires_at = %s,
                    error_details = NULL, updated_at = %s
                WHERE session_id = %s
                """,
                (
                    idempotency_key,
                    processing_token,
                    lease_expires_at,
                    lease_started_at,
                    session_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO session_extraction_results (
                    session_id, entity_id, idempotency_key, extraction_status,
                    processing_token, lease_expires_at, updated_at
                ) VALUES (%s, %s, %s, 'processing', %s, %s, %s)
                """,
                (
                    session_id,
                    entity_id,
                    idempotency_key,
                    processing_token,
                    lease_expires_at,
                    lease_started_at,
                ),
            )

        transcript_rows = conn.execute(
            """
            SELECT id, role, content, created_at FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()

    transcript = "\n".join(f"{row['role']}: {row['content']}" for row in transcript_rows)
    user_turns = [
        {"message_id": row["id"], "turn_index": index, "content": row["content"]}
        for index, row in enumerate(transcript_rows, start=1)
        if row["role"] == "user"
    ]

    try:
        drafts = extract_observations(
            transcript,
            user_turns=user_turns,
            raise_on_failure=True,
        )
    except ExtractionFailure as exc:
        _mark_extraction_failed(session_id, str(exc), processing_token)
        logger.warning(
            "volta_event=%s",
            json.dumps(
                {"event": "session_extraction_failed", "session_id": str(session_id), "failure_type": type(exc).__name__},
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        raise SessionExtractionUnavailable(str(exc)) from exc

    # Run expensive enrichment before acquiring the transaction that changes memory.
    for draft in drafts:
        if draft.importance_score is None:
            from app.memory.importance import score_importance

            importance = score_importance(draft.observation)
            draft.importance_score = importance.importance_score
            draft.importance_reasoning = importance.importance_reasoning

        if settings.plausibility_check_enabled:
            plausibility = check_plausibility(draft.observation)
            if plausibility.capped_confidence is not None:
                draft.base_confidence = min(draft.base_confidence, plausibility.capped_confidence)

    now = get_now()
    written: list[Memory] = []
    memory_changes: list[dict] = []
    try:
        with get_connection() as conn:
            session_row = conn.execute(
                "SELECT entity_id, ended_at FROM conversations WHERE id = %s FOR UPDATE",
                (session_id,),
            ).fetchone()
            if not session_row:
                raise ValueError("Session not found")

            result_row = conn.execute(
                """
                SELECT extraction_status, lifecycle_result, processing_token
                FROM session_extraction_results WHERE session_id = %s FOR UPDATE
                """,
                (session_id,),
            ).fetchone()
            if result_row and result_row["extraction_status"] == "completed":
                return _decode_json(result_row["lifecycle_result"])
            if (
                not result_row
                or result_row["extraction_status"] != "processing"
                or result_row["processing_token"] != processing_token
            ):
                raise SessionEndingInProgress("The extraction transaction is no longer active.")

            existing = list_memories(entity_id, include_superseded=False, conn=conn)
            for draft in drafts:
                from app.memory.contradiction import classify_relationship

                relationship = classify_relationship(
                    draft.observation,
                    existing,
                    new_memory_type=draft.memory_type,
                )
                relation_type = relationship.get("relationship")
                target = relationship.get("target_memory")

                if relation_type == "contradicts" and target and target.id:
                    old_memory, new_memory = resolve(
                        target,
                        draft,
                        entity_id,
                        session_id,
                        conn=conn,
                    )
                    persist_provenance(conn, new_memory, session_id)
                    persist_relation(conn, old_memory.id, new_memory.id, "supersedes", session_id)
                    change = {
                        "operation": "corrected",
                        "before": _memory_snapshot(old_memory),
                        "after": _memory_snapshot(new_memory),
                    }
                    persist_lifecycle_event(
                        conn,
                        entity_id=entity_id,
                        session_id=session_id,
                        action="corrected",
                        before_memory_id=old_memory.id,
                        after_memory_id=new_memory.id,
                        display_payload=change,
                    )
                    written.append(new_memory)
                    existing = [memory for memory in existing if memory.id != old_memory.id]
                    existing.append(new_memory)
                    memory_changes.append(change)
                    continue

                if relation_type == "reinforces" and target and target.id:
                    updated = _write_reinforcement_version(
                        conn,
                        target=target,
                        draft=draft,
                        entity_id=entity_id,
                        session_id=session_id,
                    )
                    change = {
                        "operation": "reinforced",
                        "before": _memory_snapshot(target),
                        "after": _memory_snapshot(updated),
                    }
                    _persist_reinforcement_lifecycle_event(
                        conn,
                        entity_id=entity_id,
                        session_id=session_id,
                        target=target,
                        updated=updated,
                        change=change,
                    )
                    written.append(updated)
                    existing = [updated if memory.id == target.id else memory for memory in existing]
                    memory_changes.append(change)
                    continue

                memory = write_from_draft(entity_id, draft, source_session_id=session_id, conn=conn)
                persist_provenance(conn, memory, session_id)
                change = {"operation": "created", "before": None, "after": _memory_snapshot(memory)}
                persist_lifecycle_event(
                    conn,
                    entity_id=entity_id,
                    session_id=session_id,
                    action="created",
                    before_memory_id=None,
                    after_memory_id=memory.id,
                    display_payload=change,
                )
                written.append(memory)
                existing.append(memory)
                memory_changes.append(change)

            result = {
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
                "memory_changes": memory_changes,
                "extraction_status": "completed",
            }
            conn.execute(
                """
                UPDATE conversations
                SET ended_at = %s, extraction_completed = true
                WHERE id = %s
                """,
                (now, session_id),
            )
            completion = conn.execute(
                """
                UPDATE session_extraction_results
                SET extraction_status = 'completed', lifecycle_result = %s,
                    completed_at = %s, updated_at = %s, error_details = NULL,
                    processing_token = NULL, lease_expires_at = NULL
                WHERE session_id = %s
                  AND extraction_status = 'processing'
                  AND processing_token = %s
                """,
                (json.dumps(result), now, now, session_id, processing_token),
            )
            if completion.rowcount != 1:
                raise SessionEndingInProgress(
                    "The extraction lease was recovered before this receipt could be saved."
                )
    except (ValueError, SessionEndingInProgress):
        raise
    except Exception as exc:  # write failure must never be presented as a receipt
        _mark_extraction_failed(session_id, str(exc), processing_token)
        logger.error(
            "volta_event=%s",
            json.dumps(
                {"event": "session_persistence_failed", "session_id": str(session_id), "failure_type": type(exc).__name__},
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        raise SessionExtractionUnavailable("Volta could not safely save this session. Please retry.") from exc

    # Transcript chunks are retrieval enrichment, not a prerequisite for a durable receipt.
    try:
        from app.memory.embeddings import store_transcript_chunk

        for row in transcript_rows:
            store_transcript_chunk(entity_id, session_id, f"{row['role']}: {row['content']}")
    except Exception:
        # The durable memory transaction is already committed; log through the embedding module on next use.
        pass

    logger.info(
        "volta_event=%s",
        json.dumps(
            {
                "event": "session_memory_lifecycle_completed",
                "session_id": str(session_id),
                "memory_change_count": len(memory_changes),
                "operations": [change.get("operation") for change in memory_changes],
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
    )

    return result
