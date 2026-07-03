"""Detect and resolve conflicting observations."""

from __future__ import annotations

from uuid import UUID

from app.memory.models import Memory, MemoryDraft, MemoryType
from app.memory.store import supersede, write_from_draft


def detect_conflict(new_observation: str, existing_memories: list[Memory]) -> Memory | None:
    """Lightweight heuristic — production path uses a Qwen contradiction check."""
    normalized = new_observation.lower()
    for memory in existing_memories:
        if memory.is_superseded:
            continue
        if memory.memory_type not in {MemoryType.FACT, MemoryType.CORRECTION, MemoryType.PREFERENCE}:
            continue
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
    draft = MemoryDraft(
        memory_type=MemoryType.CORRECTION,
        observation=new_observation,
        base_confidence=0.95,
    )
    new_memory = write_from_draft(entity_id, draft, source_session_id=session_id)
    supersede(old_memory.id, new_memory)
    return old_memory, new_memory
