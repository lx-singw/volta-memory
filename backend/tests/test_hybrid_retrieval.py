from uuid import uuid4
from app.memory.embeddings import store_transcript_chunk, search_fallback, embed_transcript_chunk
from app.memory.retrieval import build_memory_context


def test_hybrid_retrieval_fallback():
    entity_id = f"test-hybrid-{uuid4()}"
    session_id = uuid4()

    from app.db import get_connection
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (id, entity_id) VALUES (%s, %s)",
            (session_id, entity_id)
        )

    # 1. Store a chunk of conversation transcript
    store_transcript_chunk(entity_id, session_id, "User said they reside in a duplex house in Durban.")

    # 2. Search fallback
    q_emb = embed_transcript_chunk("Durban residence?")
    results = search_fallback(q_emb, entity_id, budget_tokens=100)
    
    assert len(results) == 1
    assert "duplex" in results[0]

    # 3. Retrieve context with build_memory_context (when typed context has low similarity)
    # Since we have no typed memories, max similarity will be 0.0, which triggers fallback!
    context = build_memory_context(entity_id, memories=[], query_context="Where do they live?", persona="volta")
    assert len(context.fallback_chunks) == 1
    assert "duplex" in context.fallback_chunks[0]
