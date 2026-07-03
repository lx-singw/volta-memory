"""Ebbinghaus-grounded stability modulation for decay."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from app.config import get_settings
from app.memory.models import Memory


def compute_stability(memory: Memory) -> float:
    """S_n = S_0 * growth_factor^reinforcement_count."""
    settings = get_settings()
    s0 = memory.stability_s0 or settings.s0_default
    importance = memory.importance_score or 0.5
    growth = settings.stability_growth_base + settings.stability_growth_importance_range * importance
    return s0 * math.pow(growth, max(memory.reinforcement_count - 1, 0))


def retention_strength(memory: Memory, now: datetime | None = None) -> float:
    """Stability-modulated retention used by decay.apply_decay."""
    _ = now
    return max(compute_stability(memory), 0.01)


def is_cross_session_reinforcement(memory: Memory, new_conversation_id: str) -> bool:
    """Only cross-session reinforcements count toward reinforcement_count growth."""
    if memory.source_session_id is None:
        return True
    return str(memory.source_session_id) != new_conversation_id
