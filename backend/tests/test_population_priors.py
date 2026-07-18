from uuid import uuid4
from app.memory.priors import seed_population_priors
from app.memory.store import list_memories, get_connection


def test_seed_population_priors():
    entity_id = f"test-priors-{uuid4()}"
    session_id = uuid4()

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (id, entity_id) VALUES (%s, %s)",
            (session_id, entity_id)
        )

    # Seeding priors on message containing backup keyword
    seed_population_priors(entity_id, "We need backup during load shedding", session_id)
    
    memories = list_memories(entity_id, include_superseded=False)
    assert len(memories) == 1
    assert "backup duration" in memories[0].observation.lower()
    assert memories[0].source == "population_prior"
    assert memories[0].base_confidence == 0.35

    # Doing it again (when memories already exist) should NOT seed a duplicate prior
    seed_population_priors(entity_id, "Also worried about cost", session_id)
    memories_after = list_memories(entity_id, include_superseded=False)
    assert len(memories_after) == 1
