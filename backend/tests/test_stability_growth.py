from datetime import datetime, timezone, timedelta
from uuid import uuid4
from app.memory.models import Memory, MemoryType
from app.memory.decay import reinforce
from app.memory.stability import compute_stability


def test_cross_session_reinforcement():
    session1 = uuid4()
    session2 = uuid4()

    memory = Memory(
        entity_id="test-entity",
        memory_type=MemoryType.PREFERENCE,
        observation="Loves solar power",
        base_confidence=0.8,
        reinforcement_count=1,
        cross_session_reinforcement_count=1,
        source_session_id=session1,
        importance_score=0.5
    )

    # 1. Reinforce in the same session (counts should NOT increment cross_session_reinforcement_count)
    reinforced1 = reinforce(memory, session_id=session1)
    assert reinforced1.reinforcement_count == 2
    assert reinforced1.cross_session_reinforcement_count == 1

    # 2. Reinforce in a new session (cross_session_reinforcement_count should increment)
    reinforced2 = reinforce(memory, session_id=session2)
    assert reinforced2.reinforcement_count == 2
    assert reinforced2.cross_session_reinforcement_count == 2


def test_ebbinghaus_stability_growth():
    # stability s0 default is settings.s0_default (e.g. 10.0 or 15.0)
    # growth_factor = 1.5 + (importance_score * 1.0)
    # S_n = S_0 * growth_factor ^ (cross_session_reinforcement_count - 1)
    memory1 = Memory(
        entity_id="test-entity",
        memory_type=MemoryType.PREFERENCE,
        observation="Loves solar power",
        base_confidence=0.8,
        reinforcement_count=1,
        cross_session_reinforcement_count=1,
        importance_score=0.5,
        stability_s0=10.0
    )

    memory2 = Memory(
        entity_id="test-entity",
        memory_type=MemoryType.PREFERENCE,
        observation="Loves solar power",
        base_confidence=0.8,
        reinforcement_count=2,
        cross_session_reinforcement_count=2,
        importance_score=0.5,
        stability_s0=10.0
    )

    s1 = compute_stability(memory1)
    s2 = compute_stability(memory2)

    assert s1 == 10.0
    assert s2 == 20.0  # 10 * 2.0^1
