"""Detect and resolve conflicting observations."""

from __future__ import annotations

import logging
from uuid import UUID

from app.chat.qwen_client import get_qwen_client
from app.memory.models import Memory, MemoryDraft, MemoryType
from app.memory.store import supersede, write_from_draft

logger = logging.getLogger(__name__)


def detect_conflict(new_observation: str, existing_memories: list[Memory]) -> Memory | None:
    """Call Qwen to semantically check if new_observation contradicts any active existing memories."""
    res = classify_relationship(new_observation, existing_memories)
    if res.get("relationship") == "contradicts":
        return res.get("target_memory")
    return None


def classify_relationship(new_observation: str, existing_memories: list[Memory]) -> dict[str, Any]:
    """Call Qwen to classify the relationship of new_observation to existing memories.
    Returns:
    {
        "relationship": "contradicts" | "reinforces" | "unrelated",
        "target_memory": Memory | None,
        "reasoning": str
    }
    """
    candidates = [
        m for m in existing_memories
        if not m.is_superseded and m.memory_type in {MemoryType.FACT, MemoryType.CORRECTION, MemoryType.PREFERENCE}
    ]

    if not candidates:
        return {"relationship": "unrelated", "target_memory": None, "reasoning": "No active memories of matching type found."}

    candidates_list = "\n".join(f"{idx}: {m.observation}" for idx, m in enumerate(candidates))

    system_prompt = (
        "You are a semantic relationship classification engine for an AI memory system. "
        "Your task is to analyze a new user observation against a list of existing memories "
        "and determine if the new observation:\n"
        "1. 'contradicts': updates, corrects, or opposes a previous observation (e.g. changing monthly bill from R3000 to R2500, changing solar preference, or changing roof layout).\n"
        "2. 'reinforces': repeats, confirms, supports, or reinforces an existing memory without contradicting it (e.g. stating 'backup is key' again, or restating their house size).\n"
        "3. 'unrelated': describes a different aspect or topic entirely (e.g. no semantic overlap or reference to the topics in the existing memories).\n\n"
        "Return a JSON object in this format:\n"
        "{\n"
        "  \"relationship\": \"contradicts\" | \"reinforces\" | \"unrelated\",\n"
        "  \"target_index\": null | integer (the index from the list that is contradicted or reinforced),\n"
        "  \"reasoning\": \"One sentence explaining your decision\"\n"
        "}"
    )

    user_prompt = (
        f"New Observation:\n{new_observation}\n\n"
        f"Existing Memories:\n{candidates_list}"
    )

    try:
        client = get_qwen_client()
        result = client.complete_json(system_prompt, user_prompt)
        if isinstance(result, dict) and "relationship" in result:
            rel = result["relationship"]
            if rel in {"contradicts", "reinforces"}:
                target_idx = result.get("target_index")
                if target_idx is not None and 0 <= int(target_idx) < len(candidates):
                    return {
                        "relationship": rel,
                        "target_memory": candidates[int(target_idx)],
                        "reasoning": result.get("reasoning", "")
                    }
    except Exception as e:
        logger.error(f"Error in Qwen relationship classification: {e}")

    # Fallback to local heuristic
    normalized = new_observation.lower()
    for memory in candidates:
        existing = memory.observation.lower()
        if _looks_like_bill_correction(normalized, existing):
            return {
                "relationship": "contradicts",
                "target_memory": memory,
                "reasoning": "Matched bill correction heuristic."
            }
        elif normalized == existing or normalized in existing or existing in normalized:
            return {
                "relationship": "reinforces",
                "target_memory": memory,
                "reasoning": "Matched substring duplicate heuristic."
            }

    return {"relationship": "unrelated", "target_memory": None, "reasoning": "Default fallback relationship."}


def _looks_like_bill_correction(new_text: str, old_text: str) -> bool:
    if "bill" not in new_text and "bill" not in old_text:
        return False
    if "r" not in new_text or "r" not in old_text:
        return False
    return new_text != old_text


def resolve(old_memory: Memory, new_observation: str, entity_id: str, session_id: UUID | None) -> tuple[Memory, Memory]:
    from app.memory.importance import score_importance
    importance = score_importance(new_observation)
    draft = MemoryDraft(
        memory_type=MemoryType.CORRECTION,
        observation=new_observation,
        base_confidence=0.95,
        importance_score=importance.importance_score,
        importance_reasoning=importance.importance_reasoning,
    )
    new_memory = write_from_draft(entity_id, draft, source_session_id=session_id)
    supersede(old_memory.id, new_memory)
    return old_memory, new_memory
