"""Core read/write protocol for typed memories."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.db import get_connection
from app.memory.models import Memory, MemoryContext, MemoryDraft, MemoryType
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
    )


def list_memories(entity_id: str, include_superseded: bool = True) -> list[Memory]:
    query = """
        SELECT * FROM memories
        WHERE entity_id = %s
    """
    params: list[Any] = [entity_id]
    if not include_superseded:
        query += " AND NOT is_superseded"
    query += " ORDER BY last_reinforced_at DESC NULLS LAST"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_memory(dict(row)) for row in rows]


def load_context(entity_id: str, query_context: str = "", persona: str = "volta") -> MemoryContext:
    memories = list_memories(entity_id, include_superseded=False)
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
) -> Memory:
    memory_id = uuid4()
    now = datetime.now(timezone.utc)

    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO memories (
                id, entity_id, memory_type, observation, evidence,
                base_confidence, reinforcement_count, cross_session_reinforcement_count,
                first_observed_at, last_reinforced_at,
                source_session_id, importance_score, importance_reasoning,
                plausibility_flag, source
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, 1, 1,
                %s, %s,
                %s, %s, %s,
                %s, %s
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
            ),
        ).fetchone()

    return _row_to_memory(dict(row))


def write_from_draft(
    entity_id: str,
    draft: MemoryDraft,
    source_session_id: UUID | None = None,
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
    )


def update_memory_reinforcement(
    memory_id: UUID,
    reinforcement_count: int,
    cross_session_count: int,
    base_confidence: float,
    last_reinforced_at: datetime,
) -> None:
    with get_connection() as conn:
        conn.execute(
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


def supersede(old_memory_id: UUID, new_memory: Memory) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE memories
            SET is_superseded = true, superseded_by_id = %s
            WHERE id = %s
            """,
            (new_memory.id, old_memory_id),
        )
