"""Unit tests for token-budgeted retrieval ranking."""

from datetime import datetime, timedelta, timezone

from app.memory.models import Memory, MemoryType
from app.memory.retrieval import build_memory_context, pack_to_token_budget, rank_memories


def _memory(observation: str, confidence: float, reinforced_days_ago: int = 0) -> Memory:
    now = datetime.now(timezone.utc)
    last = now.replace(microsecond=0)
    if reinforced_days_ago:
        last = last - timedelta(days=reinforced_days_ago)
    return Memory(
        entity_id="demo-consumer-1",
        memory_type=MemoryType.FACT,
        observation=observation,
        base_confidence=confidence,
        reinforcement_count=2 if reinforced_days_ago == 0 else 1,
        first_observed_at=last,
        last_reinforced_at=last,
    )


def test_ranking_prefers_high_confidence_recent_memories():
    memories = [
        _memory("old low relevance detail from session 1", 0.55, reinforced_days_ago=45),
        _memory("backup power is primary motivation", 0.9, reinforced_days_ago=0),
    ]
    ranked = rank_memories("demo-consumer-1", memories)
    assert ranked[0].memory.observation.startswith("backup power")


def test_pack_respects_token_budget():
    memories = [
        _memory("short", 0.9),
        _memory("another reasonably sized memory observation for testing budget packing", 0.85),
    ]
    ranked = rank_memories("demo-consumer-1", memories)
    packed = pack_to_token_budget(ranked, max_tokens=5)
    assert len(packed) <= len(ranked)


def test_build_memory_context_excludes_below_threshold():
    memories = [_memory("faded detail", 0.2, reinforced_days_ago=120)]
    context = build_memory_context("demo-consumer-1", memories)
    assert context.packed_memories == []
