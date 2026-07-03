"""Volta system prompt builder with confidence-tier phrasing."""

from __future__ import annotations

from app.config import get_settings
from app.memory.models import MemoryContext, ScoredMemory


def _format_memory_line(item: ScoredMemory) -> str:
    obs = item.memory.observation
    if item.tier.value == "high":
        return f"- {obs} (state plainly — high confidence)"
    if item.tier.value == "medium":
        return f"- {obs} (check softly — medium confidence)"
    return f"- {obs}"


def build_system_prompt(memory_context: MemoryContext, persona_template: str | None = None) -> str:
    settings = get_settings()
    base = persona_template or (
        "You are Volta, a warm and direct AI energy advisor for South African homeowners. "
        "Use plain language. Focus on solar sizing, load-shedding backup, and tariff context."
    )

    if not memory_context.packed_memories:
        return base

    memory_lines = "\n".join(_format_memory_line(item) for item in memory_context.packed_memories)
    tier_note = (
        f"Confidence tiers: plain statement >= {settings.confidence_high_tier_threshold}, "
        f"soft check >= {settings.confidence_surface_threshold}, below threshold do not surface."
    )

    explain_note = ""
    if settings.explainability_enabled:
        explain_note = (
            "\nAfter your user-facing answer, append an [EXPLAIN]...[/EXPLAIN] block summarizing "
            "which memories influenced the response, the tier choice, and a one-sentence counterfactual."
        )

    return (
        f"{base}\n\n"
        f"Known memories for this consumer (token budget {settings.max_memory_tokens}):\n"
        f"{memory_lines}\n\n"
        f"{tier_note}{explain_note}"
    )
