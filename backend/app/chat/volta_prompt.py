"""Volta system prompt builder with confidence-tier phrasing."""

from __future__ import annotations

from app.config import get_settings
from app.memory.models import MemoryContext, ScoredMemory


def _format_memory_line(item: ScoredMemory) -> str:
    obs = item.memory.observation
    action = item.dialogue_action
    
    if action == "CLARIFY":
        return f"- {obs} (action: CLARIFY — low confidence but high importance; proactively ask user for clarification)"
    elif action == "STATE":
        return f"- {obs} (action: STATE — high confidence; state plainly)"
    elif action == "SOFT_CHECK":
        return f"- {obs} (action: SOFT_CHECK — medium confidence; check softly)"
    return f"- {obs} (action: IGNORE)"


def build_system_prompt(memory_context: MemoryContext, persona_template: str | None = None) -> str:
    settings = get_settings()
    base = persona_template or (
        "You are Volta, a warm and direct AI energy advisor for South African homeowners. "
        "Use plain language. Focus on solar sizing, load-shedding backup planning, and "
        "basic SA electricity tariff context. Do not generate quotes or connect to installers."
    )

    memory_lines = ""
    if memory_context.packed_memories:
        # Exclude IGNORE memories from prompt
        visible_memories = [m for m in memory_context.packed_memories if m.dialogue_action != "IGNORE"]
        if visible_memories:
            memory_lines = "\n".join(_format_memory_line(item) for item in visible_memories)

    gap_lines = ""
    if memory_context.known_gaps:
        gap_list = ", ".join(memory_context.known_gaps)
        gap_lines = (
            f"Known gaps in your understanding of this user: [{gap_list}].\n"
            f"If relevant to the flow of conversation, ask natural follow-up questions to understand these details better."
        )

    fallback_lines = ""
    if memory_context.fallback_chunks:
        chunks_str = "\n".join(f"- {chunk}" for chunk in memory_context.fallback_chunks)
        fallback_lines = (
            f"Vague/partial recollections of past conversation segments (fallback context):\n"
            f"{chunks_str}\n"
            f"Treat these recollections as vague memories — phrase them as things you might recall loosely if helpful."
        )

    tier_note = (
        f"Confidence actions: STATE = state plainly, "
        f"SOFT_CHECK = check softly, CLARIFY = ask direct clarifying questions."
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
    if fallback_lines:
        prompt += f"\n\n{fallback_lines}"
    if gap_lines:
        prompt += f"\n\n{gap_lines}"
    if explain_note:
        prompt += f"\n{explain_note}"

    return prompt
