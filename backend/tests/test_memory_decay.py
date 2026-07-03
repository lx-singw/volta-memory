"""Unit tests for confidence decay."""

from datetime import datetime, timedelta, timezone

from app.memory.decay import apply_decay, reinforce
from app.memory.models import Memory, MemoryType


def _memory(**overrides) -> Memory:
    base = {
        "entity_id": "test-entity",
        "memory_type": MemoryType.PREFERENCE,
        "observation": "backup power is primary motivation",
        "base_confidence": 0.8,
        "reinforcement_count": 1,
        "first_observed_at": datetime.now(timezone.utc) - timedelta(days=30),
        "last_reinforced_at": datetime.now(timezone.utc) - timedelta(days=30),
    }
    base.update(overrides)
    return Memory(**base)


def test_decay_reduces_confidence_over_time():
    memory = _memory()
    now = datetime.now(timezone.utc)
    effective = apply_decay(memory, now=now)
    assert effective < memory.base_confidence


def test_reinforcement_increments_count_and_caps_confidence():
    memory = _memory(base_confidence=0.97)
    updated = reinforce(memory)
    assert updated.reinforcement_count == 2
    assert updated.base_confidence <= 0.98


def test_correction_floor_keeps_surface_visibility():
    memory = _memory(
        memory_type=MemoryType.CORRECTION,
        base_confidence=0.95,
        last_reinforced_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    effective = apply_decay(memory)
    assert effective >= 0.5
