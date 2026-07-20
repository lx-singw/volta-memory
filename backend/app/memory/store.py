"""Core read/write protocol for typed memories."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import logging
from app.db import get_connection

logger = logging.getLogger(__name__)
from app.memory.models import Memory, MemoryContext, MemoryDraft, MemoryType, ProfileSlot
from app.memory.retrieval import build_memory_context


def _row_to_memory(row: dict[str, Any]) -> Memory:
    return Memory(
        id=row["id"],
        entity_id=row["entity_id"],
        memory_type=MemoryType(row["memory_type"]),
        observation=row["observation"],
        evidence=row.get("evidence"),
        base_confidence=float(row["base_confidence"]),
        reinforcement_count=row["reinforcement_count"],
        cross_session_reinforcement_count=row["cross_session_reinforcement_count"],
        first_observed_at=row.get("first_observed_at"),
        last_reinforced_at=row.get("last_reinforced_at"),
        is_superseded=row["is_superseded"],
        superseded_by_id=row.get("superseded_by_id"),
        source_session_id=row.get("source_session_id"),
        importance_score=float(row["importance_score"]) if row.get("importance_score") is not None else None,
        importance_reasoning=row.get("importance_reasoning"),
        stability_s0=float(row["stability_s0"]) if row.get("stability_s0") is not None else None,
        plausibility_flag=row.get("plausibility_flag") or "plausible",
        consolidation_source_ids=row.get("consolidation_source_ids"),
        source=row.get("source") or "individual",
        profile_slot=ProfileSlot(row.get("profile_slot") or "none"),
    )


def list_memories(
    entity_id: str,
    include_superseded: bool = True,
    conn: Any | None = None,
) -> list[Memory]:
    query = """
        SELECT * FROM memories
        WHERE entity_id = %s
    """
    params: list[Any] = [entity_id]
    if not include_superseded:
        query += " AND NOT is_superseded"
    query += " ORDER BY last_reinforced_at DESC NULLS LAST"

    if conn is None:
        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
    else:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_memory(dict(row)) for row in rows]


def load_context(entity_id: str, query_context: str = "", persona: str = "volta") -> MemoryContext:
    try:
        memories = list_memories(entity_id, include_superseded=False)
    except Exception as e:
        logger.error(f"Failed to load memories due to database error: {e}")
        memories = []
    return build_memory_context(entity_id, memories, query_context=query_context, persona=persona)


def write_memory(
    entity_id: str,
    memory_type: MemoryType,
    observation: str,
    confidence: float,
    evidence: dict[str, Any] | None = None,
    source_session_id: UUID | None = None,
    importance_score: float | None = None,
    importance_reasoning: str | None = None,
    plausibility_flag: str = "plausible",
    source: str = "individual",
    profile_slot: ProfileSlot | str = ProfileSlot.NONE,
    timestamp: datetime | None = None,
    conn: Any | None = None,
) -> Memory:
    memory_id = uuid4()
    from app.utils.clock import get_now
    now = timestamp or get_now()

    profile_slot_value = (
        profile_slot.value if isinstance(profile_slot, ProfileSlot) else str(profile_slot or "none")
    )

    def _insert(connection: Any):
        return connection.execute(
            """
            INSERT INTO memories (
                id, entity_id, memory_type, observation, evidence,
                base_confidence, reinforcement_count, cross_session_reinforcement_count,
                first_observed_at, last_reinforced_at,
                source_session_id, importance_score, importance_reasoning,
                plausibility_flag, source, profile_slot, created_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, 1, 1,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            )
            RETURNING *
            """,
            (
                memory_id,
                entity_id,
                memory_type.value,
                observation,
                json.dumps(evidence) if evidence else None,
                confidence,
                now,
                now,
                source_session_id,
                importance_score,
                importance_reasoning,
                plausibility_flag,
                source,
                profile_slot_value,
                now,
            ),
        ).fetchone()

    if conn is None:
        with get_connection() as connection:
            row = _insert(connection)
    else:
        row = _insert(conn)

    return _row_to_memory(dict(row))


def write_from_draft(
    entity_id: str,
    draft: MemoryDraft,
    source_session_id: UUID | None = None,
    timestamp: datetime | None = None,
    conn: Any | None = None,
) -> Memory:
    return write_memory(
        entity_id=entity_id,
        memory_type=draft.memory_type,
        observation=draft.observation,
        confidence=draft.base_confidence,
        evidence=draft.evidence,
        source_session_id=source_session_id,
        importance_score=draft.importance_score,
        importance_reasoning=draft.importance_reasoning,
        source=draft.source,
        profile_slot=draft.profile_slot,
        timestamp=timestamp,
        conn=conn,
    )


def update_memory_reinforcement(
    memory_id: UUID,
    reinforcement_count: int,
    cross_session_count: int,
    base_confidence: float,
    last_reinforced_at: datetime,
    conn: Any | None = None,
) -> None:
    def _update(connection: Any) -> None:
        connection.execute(
            """
            UPDATE memories
            SET reinforcement_count = %s,
                cross_session_reinforcement_count = %s,
                base_confidence = %s,
                last_reinforced_at = %s
            WHERE id = %s
            """,
            (
                reinforcement_count,
                cross_session_count,
                base_confidence,
                last_reinforced_at,
                memory_id,
            ),
        )

    if conn is None:
        with get_connection() as connection:
            _update(connection)
    else:
        _update(conn)


def supersede(old_memory_id: UUID, new_memory: Memory, conn: Any | None = None) -> None:
    def _supersede(connection: Any) -> None:
        connection.execute(
            """
            UPDATE memories
            SET is_superseded = true, superseded_by_id = %s
            WHERE id = %s
            """,
            (new_memory.id, old_memory_id),
        )

    if conn is None:
        with get_connection() as connection:
            _supersede(connection)
    else:
        _supersede(conn)
