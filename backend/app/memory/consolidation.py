"""Consolidation cycle — cluster stale low-confidence memories."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.config import get_settings
from app.memory.decay import apply_decay
from app.memory.models import ConsolidationResult, Memory, MemoryDraft, MemoryType
from app.memory.store import list_memories, supersede, write_from_draft


def should_consolidate(entity_id: str, completed_session_count: int) -> bool:
    settings = get_settings()
    if not settings.consolidation_enabled:
        return False
    return completed_session_count > 0 and completed_session_count % settings.consolidation_session_interval == 0


def _stale_candidates(memories: list[Memory], now: datetime) -> list[Memory]:
    settings = get_settings()
    cutoff = now - timedelta(days=settings.consolidation_staleness_days)
    candidates: list[Memory] = []

    for memory in memories:
        if memory.is_superseded:
            continue
        last = memory.last_reinforced_at or memory.first_observed_at
        if last and last < cutoff and apply_decay(memory, now=now) < 0.65:
            candidates.append(memory)

    return candidates


def run_consolidation(entity_id: str) -> ConsolidationResult:
    now = datetime.now(timezone.utc)
    memories = list_memories(entity_id, include_superseded=False)
    stale = _stale_candidates(memories, now)

    if len(stale) < 2:
        return ConsolidationResult(memories_consolidated=0)

    summary = "; ".join(item.observation for item in stale[:5])
    draft = MemoryDraft(
        memory_type=MemoryType.CONSOLIDATED,
        observation=f"Consolidated summary: {summary}",
        base_confidence=0.7,
    )
    consolidated = write_from_draft(entity_id, draft)

    for memory in stale:
        if memory.id:
            supersede(memory.id, consolidated)

    token_savings = sum(len(m.observation.split()) for m in stale) - len(consolidated.observation.split())
    return ConsolidationResult(
        memories_consolidated=len(stale),
        consolidated_memory_id=consolidated.id,
        token_savings_estimate=max(token_savings, 0),
    )
