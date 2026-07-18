import pytest
from app.chat.session import start_session, send_message, end_session
from app.memory.store import list_memories
from app.memory.meta_memory import find_missing_topics


def test_study_coach_end_to_end():
    entity_id = "test-student-123"
    persona = "study_coach"

    # 1. Start session
    session = start_session(entity_id, persona=persona)
    session_id = session.id

    # 2. Interact with Study Coach
    res1 = send_message(
        session_id,
        "Hi, I need help studying for my AP Calculus chemistry exam. My current grade is 68% and I want to improve to 85%.",
        persona=persona
    )
    assert res1["reply"] is not None

    res2 = send_message(
        session_id,
        "I can only study for about 6 hours every week because of my part-time job.",
        persona=persona
    )
    assert res2["reply"] is not None

    # 3. End session to trigger extraction
    end_res = end_session(session_id)
    assert len(end_res["memories_written"]) > 0

    # 4. Check that memories were stored correctly
    memories = list_memories(entity_id, include_superseded=False)
    assert len(memories) > 0

    # Verify that at least one of the study coach topics was extracted
    observations_lower = [m.observation.lower() for m in memories]
    has_subject = any("calculus" in obs or "chemistry" in obs or "study" in obs for obs in observations_lower)
    has_grade = any("68" in obs or "grade" in obs or "score" in obs for obs in observations_lower)
    
    assert has_subject or has_grade, f"Extracted memories did not match student details: {observations_lower}"

    # 5. Check meta-memory gap detection for study coach
    missing = find_missing_topics(memories, persona=persona)
    assert isinstance(missing, list)
