"""Post-conversation memory writing via Qwen extraction."""

from __future__ import annotations

import logging
from app.chat.qwen_client import get_qwen_client
from app.memory.models import MemoryDraft, MemoryType

logger = logging.getLogger(__name__)


def format_transcript_with_turns(raw_transcript: str) -> str:
    lines = []
    valid_line_idx = 1
    for line in raw_transcript.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Turn "):
            lines.append(line)
        else:
            lines.append(f"Turn {valid_line_idx}: {line}")
            valid_line_idx += 1
    return "\n".join(lines)


def extract_observations(conversation_transcript: str) -> list[MemoryDraft]:
    """Call Qwen Cloud to extract memory drafts from the session transcript."""
    if not conversation_transcript.strip():
        return []

    formatted_transcript = format_transcript_with_turns(conversation_transcript)

    system_prompt = (
        "You are an expert memory extraction agent. Analyze the conversation transcript provided "
        "and extract key factual observations about the user's preferences, household details, "
        "tariff context, electricity bills, energy goals, or specific corrections/preferences. "
        "\n\n"
        "Return a JSON array of objects representing these memory drafts. Each object must have exactly the following structure:\n"
        "{\n"
        "  \"memory_type\": \"preference\" | \"fact\" | \"outcome\" | \"correction\",\n"
        "  \"observation\": \"Concise observation statement in plain, third-person English (e.g. 'User has a monthly bill of R3000')\",\n"
        "  \"base_confidence\": 0.0 to 1.0 (estimated confidence of accuracy),\n"
        "  \"importance_score\": 0.0 to 1.0 (how important this information is for future consultations, 1.0 being highly important),\n"
        "  \"importance_reasoning\": \"One sentence explanation of the importance score\",\n"
        "  \"source_quote\": \"The exact verbatim quote from the user's message that supports this observation (must be a literal substring of the transcript)\",\n"
        "  \"source_turn_index\": 1-based integer index of the Turn in the transcript containing this observation,\n"
        "  \"is_constraint\": true | false (true if this observation represents a constraint on the solution space, e.g. roof size, budget, location constraints)\n"
        "}\n\n"
        "Guidelines:\n"
        "- Do not extract temporary greetings or transient chat states.\n"
        "- Ensure the observation is factual and independent.\n"
        "- The source_quote MUST be from the user role in the conversation, not the assistant.\n"
        "- Output ONLY valid raw JSON array of objects. Do not wrap in markdown or any other tags."
    )

    try:
        client = get_qwen_client()
        result = client.complete_json(system_prompt, formatted_transcript)
        if not isinstance(result, list):
            logger.error(f"Extraction result was not a list: {result}")
            return []

        drafts: list[MemoryDraft] = []
        for item in result:
            try:
                mtype_str = item.get("memory_type", "fact").lower()
                if mtype_str not in [e.value for e in MemoryType]:
                    mtype_str = "fact"

                evidence = {
                    "source_quote": item.get("source_quote"),
                    "source_turn_index": item.get("source_turn_index"),
                    "is_constraint": bool(item.get("is_constraint", False))
                }

                drafts.append(
                    MemoryDraft(
                        memory_type=MemoryType(mtype_str),
                        observation=item.get("observation", ""),
                        base_confidence=float(item.get("base_confidence", 0.75)),
                        importance_score=float(item.get("importance_score", 0.5)),
                        importance_reasoning=item.get("importance_reasoning", ""),
                        evidence=evidence,
                    )
                )
            except Exception as e:
                logger.error(f"Error parsing single memory draft: {item}, error: {e}")
        return drafts
    except Exception as e:
        logger.error(f"Error executing Qwen extraction: {e}")
        return [
            MemoryDraft(
                memory_type=MemoryType.OUTCOME,
                observation="Failed Qwen memory extraction, session ended.",
                base_confidence=0.5,
            )
        ]

