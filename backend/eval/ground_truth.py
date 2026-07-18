"""Ground truth expectations per eval persona."""

from __future__ import annotations

from typing import Any


def expected_recall(persona_id: str) -> list[str]:
    """Keywords or observations expected to be recalled in session 2+."""
    _expectations: dict[str, list[str]] = {
        "persona_01_backup_priority": ["backup"],
        "persona_02_cost_priority": ["cost", "savings"],
        "persona_03_hybrid_motivation": ["savings", "backup"],
        "persona_04_large_home": ["pool", "bedroom", "large"],
        "persona_05_small_apartment": ["townhouse", "roof"],
        "persona_06_financing_interest": ["financing"],
        "persona_07_tariff_complexity": ["tariff", "city power"],
        "persona_08_battery_sizing": ["battery"],
        "persona_09_installer_skeptic": ["installer"],
        "persona_10_solar_newbie": ["first"],
        "persona_11_technical_user": ["kw", "kwh"],
        "persona_12_elderly_homeowner": ["simple"],
        "persona_13_landlord_rental": ["rental", "landlord"],
        "persona_14_future_expansion": ["expansion", "future"],
        "persona_15_correction_bill": ["bill", "r2500"],
        "persona_16_correction_priority": ["priority"],
        "persona_17_decay_irrelevant": ["irrelevant"],
        "persona_18_reinforced_preference": ["preference"],
        "persona_19_consolidation_candidate": ["consolidated"],
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
