"""Ground truth expectations per eval persona."""

from __future__ import annotations

from typing import Any


def expected_recall(persona_id: str) -> list[str]:
    """Keywords or observations expected to be recalled in session 2+."""
    _expectations: dict[str, list[str]] = {
        "persona_01_backup_priority": ["backup"],
        "persona_20_adversarial": [],
    }
    return _expectations.get(persona_id, [])


def expected_superseded(persona_id: str) -> list[str]:
    return []


def load_persona_expectations(persona: dict[str, Any]) -> dict[str, Any]:
    persona_id = persona.get("id", "")
    return {
        "recall": expected_recall(persona_id),
        "superseded": expected_superseded(persona_id),
    }
