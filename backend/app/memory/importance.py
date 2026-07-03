"""Self-scored importance — modulates decay rate per memory."""

from __future__ import annotations

from app.config import get_settings
from app.memory.models import ImportanceResult, Memory


def score_importance(observation: str, conversation_context: str = "") -> ImportanceResult:
    """Placeholder — production path calls Qwen via importance scoring prompt."""
    _ = conversation_context
    length_factor = min(len(observation.split()) / 20.0, 1.0)
    return ImportanceResult(
        importance_score=round(0.4 + 0.4 * length_factor, 2),
        importance_reasoning="Scaffold heuristic — replace with Qwen self-score.",
    )


def effective_lambda(memory: Memory) -> float:
    settings = get_settings()
    base = settings.lambda_for_memory_type(memory.memory_type.value)
    importance = memory.importance_score or 0.5
    multiplier = 1.0 - (0.5 * importance)
    return base * max(multiplier, 0.25)
