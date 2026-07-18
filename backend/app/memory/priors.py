"""Cold-start population priors seeding."""

from __future__ import annotations

import logging
from uuid import UUID

from app.db import get_connection
from app.memory.models import MemoryDraft, MemoryType
from app.memory.store import list_memories, write_from_draft

logger = logging.getLogger(__name__)


def seed_population_priors(entity_id: str, first_message: str, session_id: UUID) -> None:
    """If the user has zero memories, scan the first message for keywords and seed provisional priors."""
    existing = list_memories(entity_id, include_superseded=False)
    if existing:
        return  # Not a cold-start

    try:
        with get_connection() as conn:
            patterns = conn.execute(
                "SELECT signal_keyword, inferred_observation, inferred_type, probability FROM population_patterns"
            ).fetchall()
    except Exception as e:
        logger.error(f"Failed to query population patterns: {e}")
        return

    normalized_msg = first_message.lower()
    for pattern in patterns:
        kw = pattern["signal_keyword"].lower()
        if kw in normalized_msg:
            draft = MemoryDraft(
                memory_type=MemoryType(pattern["inferred_type"]),
                observation=pattern["inferred_observation"],
                base_confidence=0.35,
                importance_score=0.4,
                importance_reasoning=f"Seeded from population cold-start prior matching keyword '{kw}'.",
                source="population_prior"
            )
            try:
                write_from_draft(entity_id, draft, source_session_id=session_id)
                logger.info(f"Seeded population prior for {entity_id}: {draft.observation}")
            except Exception as e:
                logger.error(f"Failed to write seeded prior: {e}")
