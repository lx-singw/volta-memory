"""Baseline C — embedding-only naive RAG."""

from __future__ import annotations


def respond(_entity_id: str, transcript: str, user_message: str) -> dict:
    chunks = [line for line in transcript.splitlines() if line.strip()][-5:]
    return {
        "reply": f"(naive rag) {user_message}",
        "memory_context_used": [{"observation": chunk} for chunk in chunks],
        "tokens_used": sum(len(c.split()) for c in chunks),
        "cost_usd": 0.012,
    }
