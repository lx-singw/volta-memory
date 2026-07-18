import concurrent.futures
from uuid import uuid4
from app.memory.models import MemoryType, MemoryDraft
from app.memory.store import write_from_draft, list_memories, load_context


def test_concurrency_isolation():
    num_threads = 8
    entities = [f"concurrent-entity-{uuid4()}" for _ in range(num_threads)]
    appliances = [f"appliance-{i}" for i in range(num_threads)]

    def run_worker(index: int) -> tuple[int, bool]:
        entity_id = entities[index]
        appliance = appliances[index]
        
        try:
            # 1. Write unique memory for this entity
            draft = MemoryDraft(
                memory_type=MemoryType.PREFERENCE,
                observation=f"Homeowner has a {appliance} installed in their garage.",
                base_confidence=0.9,
                importance_score=0.7,
                importance_reasoning="Garage appliance detail",
                source="individual"
            )
            write_from_draft(entity_id, draft)

            # 2. Retrieve memory context for this entity
            context = load_context(entity_id, query_context="What appliances do they have?")
            observations = [item.memory.observation for item in context.packed_memories]

            # 3. Assert isolation
            # Must contain own unique appliance
            has_own = any(appliance in obs for obs in observations)
            # Must NOT contain any other worker's unique appliance
            has_other = False
            for other_idx, other_app in enumerate(appliances):
                if other_idx != index:
                    if any(other_app in obs for obs in observations):
                        has_other = True
                        break
                        
            success = has_own and not has_other
            return index, success
        except Exception as e:
            print(f"Worker {index} failed: {e}")
            return index, False

    # Execute workers concurrently in a ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_worker, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Assert that all workers executed successfully and verified isolation
    assert len(results) == num_threads
    for index, success in results:
        assert success, f"Worker {index} failed concurrency isolation checks!"
