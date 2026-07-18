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
        ranked.append(
            ScoredMemory(memory=memory, effective_confidence=effective, score=score, tier=tier)
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
    ranked = rank_memories(entity_id, memories, query_context=query_context)
    packed = pack_to_token_budget(ranked, max_tokens=max_tokens)
    tokens_used = sum(count_tokens(item.memory.observation) for item in packed)
    
    gaps = find_missing_topics(memories, persona=persona)
    
    return MemoryContext(
        entity_id=entity_id,
        packed_memories=packed,
        tokens_used=tokens_used,
        known_gaps=gaps
    )
