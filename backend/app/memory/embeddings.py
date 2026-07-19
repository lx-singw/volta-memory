"""Hybrid retrieval fallback via pgvector embeddings."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.config import get_settings
from app.chat.qwen_client import get_qwen_client
from app.chat.tokenizer import count_tokens
from app.db import get_connection

logger = logging.getLogger(__name__)


class TranscriptChunk:
    def __init__(self, text: str, entity_id: str, tokens: int):
        self.text = text
        self.entity_id = entity_id
        self.tokens = tokens


def embed_transcript_chunk(text: str) -> list[float]:
    """Call Qwen Cloud embedding API to embed the given text."""
    settings = get_settings()
    if not settings.qwen_api_key:
        seed = sum(ord(c) for c in text) % 997
        return [(seed + i) / settings.embedding_dimension for i in range(settings.embedding_dimension)]

    import os
    is_eval = os.environ.get("EVAL_MODE") == "true"
    if is_eval:
        client = get_qwen_client()
        return client.embed(text, text_type="document")

    try:
        client = get_qwen_client()
        return client.embed(text, text_type="document")
    except Exception as e:
        logger.warning(f"Qwen embedding API call failed: {e}. Falling back to mock embedding.")
        seed = sum(ord(c) for c in text) % 997
        return [(seed + i) / settings.embedding_dimension for i in range(settings.embedding_dimension)]


def store_transcript_chunk(entity_id: str, conversation_id: UUID, text: str) -> None:
    """Embed and store a raw conversation transcript chunk in pgvector."""
    tokens = count_tokens(text)
    if tokens < 5:
        return # Skip very short/empty transcript chunks

    settings = get_settings()
    if settings.qwen_api_key:
        embedding = embed_transcript_chunk(text)
        vector_str = f"[{','.join(map(str, embedding))}]"
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO transcript_chunks (entity_id, conversation_id, text, embedding)
                VALUES (%s, %s, %s, %s::vector)
                """,
                (entity_id, conversation_id, text, vector_str),
            )
    else:
        try:
            embedding = embed_transcript_chunk(text)
            vector_str = f"[{','.join(map(str, embedding))}]"
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO transcript_chunks (entity_id, conversation_id, text, embedding)
                    VALUES (%s, %s, %s, %s::vector)
                    """,
                    (entity_id, conversation_id, text, vector_str),
                )
        except Exception as e:
            logger.error(f"Failed to store transcript chunk in database: {e}")


def search_fallback(
    query_embedding: list[float],
    entity_id: str,
    budget_tokens: int,
) -> list[str]:
    """Retrieve raw transcript chunks within token budget if typed similarity is low."""
    vector_str = f"[{','.join(map(str, query_embedding))}]"
    
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT text FROM transcript_chunks
                WHERE entity_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT 10
                """,
                (entity_id, vector_str),
            ).fetchall()
    except Exception as e:
        logger.error(f"Error querying pgvector fallback: {e}")
        return []

    fallback_texts: list[str] = []
    used_tokens = 0
    for row in rows:
        chunk_text = row["text"]
        tokens = count_tokens(chunk_text)
        if used_tokens + tokens > budget_tokens:
            continue
        fallback_texts.append(chunk_text)
        used_tokens += tokens
        
    return fallback_texts
