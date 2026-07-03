"""Baseline A — no memory across sessions."""

from __future__ import annotations


def respond(_entity_id: str, _transcript: str, user_message: str) -> dict:
    return {
        "reply": f"(no memory) {user_message}",
        "memory_context_used": [],
        "tokens_used": len(user_message.split()) * 2,
        "cost_usd": 0.005,
    }
