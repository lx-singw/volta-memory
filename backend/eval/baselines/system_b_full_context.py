"""Baseline B — naive full transcript concatenation."""

from __future__ import annotations


def respond(entity_id: str, transcript: str, user_message: str) -> dict:
    context = transcript[-4000:]
    return {
        "reply": f"(full context) entity={entity_id} latest={user_message}",
        "memory_context_used": [{"observation": context[:200]}],
        "tokens_used": len(context.split()) + len(user_message.split()),
        "cost_usd": 0.02,
    }
