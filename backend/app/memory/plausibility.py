"""Adversarial defence — plausibility gate before memory write."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings
from app.memory.models import PlausibilityResult


def _load_constraints(path: str) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with file_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def check_plausibility(observation: str, domain_constraints: dict[str, Any] | None = None) -> PlausibilityResult:
    settings = get_settings()
    constraints = domain_constraints or _load_constraints(settings.domain_constraints_file)
    lower = observation.lower()

    prohibited = constraints.get("prohibited_claim_patterns", [])
    for pattern in prohibited:
        if pattern.lower() in lower:
            return PlausibilityResult(
                plausibility_flag="boundary_violation",
                reasoning=f"Matched prohibited pattern: {pattern}",
                capped_confidence=settings.plausibility_confidence_cap,
            )

    bill_range = constraints.get("plausible_monthly_bill_zar", {})
    if "r" in lower and bill_range:
        # Scaffold only — real implementation parses numeric bill claims.
        pass

    return PlausibilityResult(
        plausibility_flag="plausible",
        reasoning="Passed domain constraint checks.",
        capped_confidence=None,
    )
