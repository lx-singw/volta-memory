"""Explainability trace parsing from [EXPLAIN] blocks."""

from __future__ import annotations

import re
from uuid import UUID

from app.memory.models import ExplainTrace

EXPLAIN_PATTERN = re.compile(r"\[EXPLAIN\](.*?)\[/EXPLAIN\]", re.DOTALL | re.IGNORECASE)


def parse_explain_block(raw_response: str) -> ExplainTrace:
    match = EXPLAIN_PATTERN.search(raw_response)
    if not match:
        return ExplainTrace(
            referenced_memory_ids=[],
            user_facing_text=raw_response.strip(),
        )

    block = match.group(1).strip()
    user_facing = EXPLAIN_PATTERN.sub("", raw_response).strip()

    primary = None
    counterfactual = None
    tier_choice = None
    for line in block.splitlines():
        lower = line.lower()
        if lower.startswith("primary:"):
            primary = line.split(":", 1)[1].strip()
        elif lower.startswith("counterfactual:"):
            counterfactual = line.split(":", 1)[1].strip()
        elif lower.startswith("tier:"):
            tier_choice = line.split(":", 1)[1].strip()

    referenced: list[UUID] = []
    if primary:
        try:
            referenced.append(UUID(primary))
        except ValueError:
            pass

    primary_id = referenced[0] if referenced else None
    return ExplainTrace(
        referenced_memory_ids=referenced,
        primary_influence_memory_id=primary_id,
        confidence_tier_choice=tier_choice,
        counterfactual=counterfactual,
        user_facing_text=user_facing,
    )
