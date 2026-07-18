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
    candidates = [
        m for m in existing_memories
        if not m.is_superseded and m.memory_type in {MemoryType.FACT, MemoryType.CORRECTION, MemoryType.PREFERENCE}
    ]

    if not candidates:
        return None

    candidates_list = "\n".join(f"{idx}: {m.observation}" for idx, m in enumerate(candidates))

    system_prompt = (
        "You are a contradiction detection assistant for an AI memory system. "
        "Your task is to determine if a new observation about a user directly contradicts or "
        "supersedes any existing memories in the provided list. "
        "A contradiction or supersession occurs when the new observation updates, corrects, or opposes a previous statement (e.g. changing monthly bill from R3000 to R2500, changing solar preference, or altering budget).\n\n"
        "Return a JSON object in this format:\n"
        "{\n"
        "  \"has_conflict\": true | false,\n"
        "  \"conflicted_index\": null | integer (the index from the list),\n"
        "  \"reasoning\": \"One sentence explanation of your decision\"\n"
        "}"
    )

    user_prompt = (
        f"New Observation:\n{new_observation}\n\n"
        f"Existing Memories:\n{candidates_list}"
    )

    try:
        client = get_qwen_client()
        result = client.complete_json(system_prompt, user_prompt)
        if isinstance(result, dict) and result.get("has_conflict"):
            conflicted_idx = result.get("conflicted_index")
            if conflicted_idx is not None and 0 <= int(conflicted_idx) < len(candidates):
                return candidates[int(conflicted_idx)]
    except Exception as e:
        logger.error(f"Error executing Qwen contradiction check: {e}")
        # Scaffold heuristic fallback
        normalized = new_observation.lower()
        for memory in candidates:
            existing = memory.observation.lower()
            if _looks_like_bill_correction(normalized, existing):
                return memory

    return None


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
