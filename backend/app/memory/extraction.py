"""Post-conversation memory writing via Qwen extraction."""

from __future__ import annotations

from app.memory.models import MemoryDraft, MemoryType


def extract_observations(conversation_transcript: str) -> list[MemoryDraft]:
    """Scaffold extractor — replace with single Qwen end-of-session call."""
    drafts: list[MemoryDraft] = []
    lower = conversation_transcript.lower()

    if "backup" in lower or "load-shedding" in lower or "load shedding" in lower:
        drafts.append(
            MemoryDraft(
                memory_type=MemoryType.PREFERENCE,
                observation="backup power is primary motivation",
                base_confidence=0.75,
            )
        )

    if "r3" in lower or "bill" in lower:
        drafts.append(
            MemoryDraft(
                memory_type=MemoryType.FACT,
                observation="consumer mentioned a monthly electricity bill figure",
                base_confidence=0.8,
            )
        )

    if not drafts and conversation_transcript.strip():
        drafts.append(
            MemoryDraft(
                memory_type=MemoryType.OUTCOME,
                observation="initial solar consultation conversation completed",
                base_confidence=0.6,
            )
        )

    return drafts
