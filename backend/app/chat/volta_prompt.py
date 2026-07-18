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
        "Use plain language. Focus on solar sizing, load-shedding backup planning, and "
        "basic SA electricity tariff context. Do not generate quotes or connect to installers."
    )

    memory_lines = ""
    if memory_context.packed_memories:
        memory_lines = "\n".join(_format_memory_line(item) for item in memory_context.packed_memories)

    gap_lines = ""
    if memory_context.known_gaps:
        gap_list = ", ".join(memory_context.known_gaps)
        gap_lines = (
            f"Known gaps in your understanding of this user: [{gap_list}].\n"
            f"If relevant to the flow of conversation, ask natural follow-up questions to understand these details better."
        )

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

    prompt = base
    if memory_lines:
        prompt += (
            f"\n\nKnown memories for this consumer (token budget {settings.max_memory_tokens}):\n"
            f"{memory_lines}\n\n"
            f"{tier_note}"
        )
    if gap_lines:
        prompt += f"\n\n{gap_lines}"
    if explain_note:
        prompt += f"\n{explain_note}"

    return prompt
