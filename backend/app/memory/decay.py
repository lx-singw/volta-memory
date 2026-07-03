"""Confidence decay model — timely forgetting without deletion."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from uuid import UUID

from app.config import get_settings
from app.memory.models import Memory, MemoryType
from app.memory.stability import retention_strength


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def apply_decay(memory: Memory, now: datetime | None = None) -> float:
    """Compute effective confidence at query time."""
    settings = get_settings()
    now = now or _utcnow()
    last = memory.last_reinforced_at or memory.first_observed_at or now
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    days = max((now - last).total_seconds() / 86400.0, 0.0)
    lam = settings.lambda_for_memory_type(memory.memory_type.value)

    if memory.memory_type == MemoryType.CORRECTION and days <= settings.correction_floor_days:
        return max(memory.base_confidence, settings.confidence_surface_threshold + 0.01)

    retention = retention_strength(memory, now=now)
    decay_factor = math.exp(-lam * days / max(retention, 0.01))
    return memory.base_confidence * decay_factor


def reinforce(memory: Memory, new_evidence: dict | None = None) -> Memory:
    """Reset decay clock and nudge confidence upward (capped at 0.98)."""
    updated = memory.model_copy(deep=True)
    updated.last_reinforced_at = _utcnow()
    updated.reinforcement_count += 1
    updated.base_confidence = min(updated.base_confidence + 0.03, 0.98)
    if new_evidence:
        updated.evidence = new_evidence
    return updated


def confidence_tier(effective_confidence: float) -> str:
    settings = get_settings()
    if effective_confidence >= settings.confidence_high_tier_threshold:
        return "high"
    if effective_confidence >= settings.confidence_surface_threshold:
        return "medium"
    return "below_surface"
