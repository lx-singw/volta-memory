"""Consolidation cycle — cluster stale low-confidence memories."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.config import get_settings
from app.chat.qwen_client import get_qwen_client
from app.memory.decay import apply_decay
from app.memory.models import ConsolidationResult, Memory, MemoryDraft, MemoryType
from app.memory.store import list_memories, supersede, write_from_draft

logger = logging.getLogger(__name__)


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
    from app.utils.clock import get_now
    now = get_now()
    memories = list_memories(entity_id, include_superseded=False)
    stale = _stale_candidates(memories, now)

    if len(stale) < 2:
        return ConsolidationResult(memories_consolidated=0)

    stale_text = "\n".join(f"- {item.observation}" for item in stale[:5])

    system_prompt = (
        "You are an expert memory consolidation assistant. Your task is to take multiple stale memories "
        "about a user and consolidate them into a single, cohesive, and concise observation statement. "
        "Do not lose critical facts (like budget, location, preferences) but merge redundancies and "
        "simplify phrasing.\n\n"
        "Return a JSON object in this format:\n"
        "{\n"
        "  \"consolidated_observation\": \"A single consolidated observation statement in plain English (e.g. 'User has R3000 monthly bill and wants load-shedding backup')\",\n"
        "  \"confidence\": float (0.0 to 1.0, representing the confidence of this consolidated observation)\n"
        "}"
    )

    user_prompt = f"Stale memories to consolidate:\n{stale_text}"

    consolidated_obs = f"Consolidated summary: {'; '.join(item.observation for item in stale[:5])}"
    confidence = 0.7

    try:
        client = get_qwen_client()
        result = client.complete_json(system_prompt, user_prompt)
        if isinstance(result, dict) and "consolidated_observation" in result:
            consolidated_obs = result["consolidated_observation"]
            confidence = float(result.get("confidence", 0.7))
    except Exception as e:
        logger.error(f"Error executing Qwen consolidation: {e}")

    draft = MemoryDraft(
        memory_type=MemoryType.CONSOLIDATED,
        observation=consolidated_obs,
        base_confidence=confidence,
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
