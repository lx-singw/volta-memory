"""Baseline D — Volta typed memory engine."""

from __future__ import annotations

from app.db import check_database
from app.memory.retrieval import build_memory_context
from app.memory.store import list_memories


def respond(entity_id: str, _transcript: str, user_message: str) -> dict:
    packed: list[str] = []
    tokens_used = 0

    if check_database():
        try:
            memories = list_memories(entity_id, include_superseded=False)
            context = build_memory_context(entity_id, memories, query_context=user_message)
            packed = [item.memory.observation for item in context.packed_memories]
            tokens_used = context.tokens_used
        except Exception:
            pass

    return {
        "reply": f"(volta memory) {user_message}",
        "memory_context_used": [{"observation": obs} for obs in packed],
        "tokens_used": tokens_used,
        "cost_usd": 0.014,
    }
