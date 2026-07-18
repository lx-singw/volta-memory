"""Token-budgeted memory ranking — core track deliverable."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from app.chat.tokenizer import count_tokens
from app.config import get_settings
from app.memory.decay import apply_decay, confidence_tier
from app.memory.models import ConfidenceTier, Memory, MemoryContext, ScoredMemory


def _recency_weight(memory: Memory, now: datetime) -> float:
    last = memory.last_reinforced_at or memory.first_observed_at or now
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    days = max((now - last).total_seconds() / 86400.0, 0.0)
    return 1.0 / (1.0 + days)


def rank_memories(entity_id: str, memories: list[Memory], query_context: str = "") -> list[ScoredMemory]:
    """score = confidence * log(1 + reinforcement_count) * recency_weight"""
    _ = query_context
    settings = get_settings()
    now = datetime.now(timezone.utc)
    ranked: list[ScoredMemory] = []

    for memory in memories:
        if memory.is_superseded or memory.entity_id != entity_id:
            continue
        effective = apply_decay(memory, now=now)
        if effective < settings.confidence_surface_threshold:
            continue
        score = effective * math.log1p(memory.reinforcement_count) * _recency_weight(memory, now)
        tier = ConfidenceTier(confidence_tier(effective))
        
        from app.memory.clarification import compute_dialogue_action
        action = compute_dialogue_action(memory, effective)
        
        ranked.append(
            ScoredMemory(memory=memory, effective_confidence=effective, score=score, tier=tier, dialogue_action=action)
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def pack_to_token_budget(ranked_memories: list[ScoredMemory], max_tokens: int | None = None) -> list[ScoredMemory]:
    """Greedily fill budget using real tokenizer counts."""
    settings = get_settings()
    budget = max_tokens if max_tokens is not None else settings.max_memory_tokens
    packed: list[ScoredMemory] = []
    used = 0

    for item in ranked_memories:
        text = item.memory.observation
        tokens = count_tokens(text)
        if used + tokens > budget:
            continue
        packed.append(item)
        used += tokens

    return packed


def build_memory_context(
    entity_id: str,
    memories: list[Memory],
    query_context: str = "",
    max_tokens: int | None = None,
    persona: str = "volta",
) -> MemoryContext:
    from app.memory.meta_memory import find_missing_topics
    from app.memory.embeddings import embed_transcript_chunk, search_fallback
    
    ranked = rank_memories(entity_id, memories, query_context=query_context)
    packed = pack_to_token_budget(ranked, max_tokens=max_tokens)
    tokens_used = sum(count_tokens(item.memory.observation) for item in packed)
    
    gaps = find_missing_topics(memories, persona=persona)
    
    fallback_chunks = []
    settings = get_settings()
    if settings.hybrid_retrieval_enabled and query_context.strip():
        query_embedding = embed_transcript_chunk(query_context)
        
        max_similarity = 0.0
        for item in packed:
            obs = item.memory.observation
            obs_embedding = embed_transcript_chunk(obs)
            dot = sum(a * b for a, b in zip(query_embedding, obs_embedding))
            norm_q = math.sqrt(sum(a * a for a in query_embedding))
            norm_o = math.sqrt(sum(a * a for a in obs_embedding))
            sim = dot / (norm_q * norm_o) if (norm_q * norm_o) > 0 else 0.0
            if sim > max_similarity:
                max_similarity = sim
                
        if max_similarity < settings.hybrid_similarity_threshold:
            fallback_chunks = search_fallback(
                query_embedding=query_embedding,
                entity_id=entity_id,
                budget_tokens=settings.fallback_budget_tokens
            )
            
    return MemoryContext(
        entity_id=entity_id,
        packed_memories=packed,
        tokens_used=tokens_used,
        known_gaps=gaps,
        fallback_chunks=fallback_chunks
    )
