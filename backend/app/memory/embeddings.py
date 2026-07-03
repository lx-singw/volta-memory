"""Hybrid retrieval fallback via pgvector embeddings."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.config import get_settings


class TranscriptChunk:
    def __init__(self, text: str, entity_id: str, tokens: int):
        self.text = text
        self.entity_id = entity_id
        self.tokens = tokens


def embed_transcript_chunk(text: str) -> list[float]:
    """Placeholder — production path calls QWEN_MODEL_EMBEDDING."""
    settings = get_settings()
    seed = sum(ord(c) for c in text) % 997
    return [(seed + i) / settings.embedding_dimension for i in range(settings.embedding_dimension)]


def search_fallback(
    query_embedding: list[float],
    entity_id: str,
    budget_tokens: int,
) -> list[TranscriptChunk]:
    """Only invoked when typed retrieval similarity is below threshold."""
    _ = query_embedding
    _ = entity_id
    _ = budget_tokens
    return []
