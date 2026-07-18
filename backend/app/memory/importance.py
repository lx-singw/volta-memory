"""Self-scored importance — modulates decay rate per memory."""

from __future__ import annotations

import logging
from app.config import get_settings
from app.chat.qwen_client import get_qwen_client
from app.memory.models import ImportanceResult, Memory

logger = logging.getLogger(__name__)


def score_importance(observation: str, conversation_context: str = "") -> ImportanceResult:
    """Call Qwen to rate the importance of this user observation (0.0 to 1.0)."""
    system_prompt = (
        "You are an expert memory analysis assistant. Your task is to rate the long-term importance "
        "of a specific user observation on a scale from 0.0 (very low, trivial greeting details) to 1.0 (very high, core preferences, energy configurations, budgets, or load-shedding backup requirements).\n\n"
        "Return a JSON object in this format:\n"
        "{\n"
        "  \"importance_score\": float (0.0 to 1.0),\n"
        "  \"importance_reasoning\": \"One sentence explanation of the score\"\n"
        "}"
    )

    user_prompt = f"Observation: {observation}\nContext: {conversation_context}"

    try:
        client = get_qwen_client()
        result = client.complete_json(system_prompt, user_prompt)
        if isinstance(result, dict) and "importance_score" in result:
            return ImportanceResult(
                importance_score=round(float(result["importance_score"]), 2),
                importance_reasoning=result.get("importance_reasoning", "Scored via Qwen Cloud."),
            )
    except Exception as e:
        logger.error(f"Error executing Qwen importance score: {e}")

    # Fallback heuristic
    length_factor = min(len(observation.split()) / 20.0, 1.0)
    return ImportanceResult(
        importance_score=round(0.4 + 0.4 * length_factor, 2), # range 0.4 to 0.8
        importance_reasoning="Fallback heuristic score based on observation length.",
    )


def effective_lambda(memory: Memory) -> float:
    settings = get_settings()
    base = settings.lambda_for_memory_type(memory.memory_type.value)
    # importance_score is already in 0-1 range
    importance = memory.importance_score or 0.5
    multiplier = 1.0 - (0.5 * importance)
    return base * max(multiplier, 0.25)
