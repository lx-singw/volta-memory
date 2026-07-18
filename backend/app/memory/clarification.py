"""Dialogue action decision logic — uncertainty-aware active clarification."""

from __future__ import annotations

import logging
from app.memory.models import Memory

logger = logging.getLogger(__name__)


def compute_dialogue_action(memory: Memory, effective_confidence: float) -> str:
    """Dialogue action decision matrix.
    
    If importance is high (>= 0.7) but effective confidence is low (< 0.5),
    return "CLARIFY".
    """
    importance = memory.importance_score or 0.5
    
    if importance >= 0.7 and effective_confidence < 0.5:
        return "CLARIFY"
    elif importance >= 0.7 and effective_confidence >= 0.85:
        return "STATE"
    elif importance < 0.4:
        return "IGNORE"
    else:
        return "SOFT_CHECK"
