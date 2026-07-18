import pytest
from unittest.mock import patch
import httpx
import psycopg

from app.memory.store import load_context
from app.memory.embeddings import embed_transcript_chunk


def test_db_connection_drop_chaos():
    # Mock get_connection to simulate database connection pool failure
    with patch("app.memory.store.get_connection") as mock_conn:
        mock_conn.side_effect = psycopg.OperationalError("Connection pool exhausted / DB timeout")
        
        # Calling load_context should degrade gracefully and not raise an exception
        context = load_context("test-chaos-entity", query_context="solar preferences")
        
        assert context.entity_id == "test-chaos-entity"
        assert len(context.packed_memories) == 0
        assert context.tokens_used == 0


def test_qwen_api_timeout_chaos():
    # Mock httpx Client.post to raise timeout error
    with patch("httpx.Client.post") as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Qwen Cloud API timeout")
        
        # Calling embed_transcript_chunk should fall back to mock embedding instead of raising
        emb = embed_transcript_chunk("Duplex house Durban solar sizing request")
        
        assert len(emb) == 1536  # Returns mock vector of embedding dimension
        assert any(x != 0.0 for x in emb)
