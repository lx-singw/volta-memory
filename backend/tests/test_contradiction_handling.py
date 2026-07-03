"""Unit tests for contradiction detection and supersession."""

from uuid import uuid4

from app.memory.contradiction import detect_conflict
from app.memory.models import Memory, MemoryType


def test_detects_bill_amount_conflict():
    existing = Memory(
        id=uuid4(),
        entity_id="demo-consumer-1",
        memory_type=MemoryType.FACT,
        observation="monthly bill is R3,200",
        base_confidence=0.8,
    )
    conflict = detect_conflict("actually my monthly bill is R3,800", [existing])
    assert conflict is not None
    assert conflict.id == existing.id


def test_no_conflict_for_unrelated_observation():
    existing = Memory(
        id=uuid4(),
        entity_id="demo-consumer-1",
        memory_type=MemoryType.PREFERENCE,
        observation="backup power is primary motivation",
        base_confidence=0.8,
    )
    conflict = detect_conflict("I prefer black panels aesthetically", [existing])
    assert conflict is None
