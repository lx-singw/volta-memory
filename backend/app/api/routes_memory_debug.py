"""Memory transparency and debug HTTP routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings
from app.db import get_connection
from app.memory.consolidation import run_consolidation
from app.memory.decay import apply_decay, confidence_tier
from app.memory.retrieval import build_memory_context
from app.memory.store import list_memories

router = APIRouter(tags=["memory"])


class MemoryItem(BaseModel):
    id: str
    memory_type: str
    observation: str
    base_confidence: float
    effective_confidence: float
    reinforcement_count: int
    is_superseded: bool
    superseded_by_id: str | None = None
    last_reinforced_at: str | None = None
    importance_score: float | None = None
    plausibility_flag: str | None = None


@router.get("/entities/{entity_id}/memories")
def get_memories(entity_id: str) -> dict:
    memories = list_memories(entity_id, include_superseded=True)
    payload = []
    for memory in memories:
        effective = apply_decay(memory)
        payload.append(
            MemoryItem(
                id=str(memory.id),
                memory_type=memory.memory_type.value,
                observation=memory.observation,
                base_confidence=memory.base_confidence,
                effective_confidence=round(effective, 4),
                reinforcement_count=memory.reinforcement_count,
                is_superseded=memory.is_superseded,
                superseded_by_id=str(memory.superseded_by_id) if memory.superseded_by_id else None,
                last_reinforced_at=memory.last_reinforced_at.isoformat() if memory.last_reinforced_at else None,
                importance_score=memory.importance_score,
                plausibility_flag=memory.plausibility_flag,
            ).model_dump()
        )
    return {"entity_id": entity_id, "memories": payload}


@router.get("/entities/{entity_id}/memories/active-context")
def get_active_context(entity_id: str, query: str = Query(default="")) -> dict:
    settings = get_settings()
    memories = list_memories(entity_id, include_superseded=False)
    context = build_memory_context(entity_id, memories, query_context=query)

    ranked_all = build_memory_context(entity_id, memories, query_context=query, max_tokens=10_000)
    excluded_below = len(ranked_all.packed_memories) - len(context.packed_memories)

    return {
        "query": query,
        "max_tokens_budget": settings.max_memory_tokens,
        "tokens_used": context.tokens_used,
        "packed_memories": [
            {"observation": item.memory.observation, "score": round(item.score, 4)}
            for item in context.packed_memories
        ],
        "excluded_below_threshold": max(excluded_below, 0),
        "excluded_over_budget": 0,
    }


@router.get("/messages/{message_id}/explain")
def get_explain_trace(message_id: UUID) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT et.*, m.content
            FROM explain_traces et
            JOIN messages m ON m.id = et.message_id
            WHERE et.message_id = %s
            """,
            (message_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Explain trace not found")

    referenced_ids = row.get("referenced_memory_ids") or []
    memories = []
    for mem_id in referenced_ids:
        mem_row = None
        with get_connection() as conn:
            mem_row = conn.execute("SELECT id, observation, importance_score FROM memories WHERE id = %s", (mem_id,)).fetchone()
        if mem_row:
            memories.append(
                {
                    "id": str(mem_row["id"]),
                    "observation": mem_row["observation"],
                    "importance_score": float(mem_row["importance_score"]) if mem_row["importance_score"] is not None else None,
                }
            )

    return {
        "message_id": str(message_id),
        "referenced_memories": memories,
        "primary_influence_memory_id": str(row["primary_influence_memory_id"])
        if row.get("primary_influence_memory_id")
        else None,
        "confidence_tier_choice": row.get("confidence_tier_choice"),
        "counterfactual": row.get("counterfactual"),
    }


@router.get("/entities/{entity_id}/consolidation-log")
def get_consolidation_log(entity_id: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT triggered_at_session_count, memories_consolidated,
                   consolidated_memory_id, token_savings_estimate, created_at
            FROM consolidation_log
            WHERE entity_id = %s
            ORDER BY created_at DESC
            """,
            (entity_id,),
        ).fetchall()

    consolidations = []
    for row in rows:
        observation = None
        if row["consolidated_memory_id"]:
            with get_connection() as conn:
                mem = conn.execute(
                    "SELECT observation FROM memories WHERE id = %s",
                    (row["consolidated_memory_id"],),
                ).fetchone()
            if mem:
                observation = mem["observation"]

        consolidations.append(
            {
                "triggered_at_session_count": row["triggered_at_session_count"],
                "memories_consolidated": row["memories_consolidated"],
                "consolidated_observation": observation,
                "token_savings_estimate": row["token_savings_estimate"],
            }
        )

    return {"entity_id": entity_id, "consolidations": consolidations}


@router.post("/entities/{entity_id}/consolidation/run")
def trigger_consolidation(entity_id: str) -> dict:
    result = run_consolidation(entity_id)
    return result.model_dump()
