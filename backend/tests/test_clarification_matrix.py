from app.memory.models import Memory, MemoryType
from app.memory.clarification import compute_dialogue_action


def test_compute_dialogue_action():
    # 1. High importance, low confidence -> CLARIFY
    m1 = Memory(
        entity_id="test",
        memory_type=MemoryType.PREFERENCE,
        observation="Solar is critical",
        base_confidence=0.4,
        importance_score=0.8
    )
    assert compute_dialogue_action(m1, 0.45) == "CLARIFY"

    # 2. High importance, high confidence -> STATE
    m2 = Memory(
        entity_id="test",
        memory_type=MemoryType.PREFERENCE,
        observation="Solar is critical",
        base_confidence=0.9,
        importance_score=0.85
    )
    assert compute_dialogue_action(m2, 0.88) == "STATE"

    # 3. Low importance -> IGNORE
    m3 = Memory(
        entity_id="test",
        memory_type=MemoryType.PREFERENCE,
        observation="Solar is critical",
        base_confidence=0.8,
        importance_score=0.3
    )
    assert compute_dialogue_action(m3, 0.8) == "IGNORE"

    # 4. Standard -> SOFT_CHECK
    m4 = Memory(
        entity_id="test",
        memory_type=MemoryType.PREFERENCE,
        observation="Solar is critical",
        base_confidence=0.7,
        importance_score=0.6
    )
    assert compute_dialogue_action(m4, 0.7) == "SOFT_CHECK"
