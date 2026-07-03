"""40-item human-labeled importance benchmark scaffold."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings
from app.memory.importance import score_importance


def run_importance_validation() -> dict:
    settings = get_settings()
    dataset_path = Path(settings.importance_validation_dataset)
    if not dataset_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        dataset_path = backend_root / dataset_path
    if not dataset_path.exists():
        return {"sample_size": 0, "mean_absolute_error": None, "results": []}

    with dataset_path.open(encoding="utf-8") as handle:
        items = json.load(handle)

    results = []
    errors = []
    for item in items:
        human = float(item["human_importance_score"])
        qwen = score_importance(item["observation_text"]).importance_score
        abs_error = abs(human - qwen)
        errors.append(abs_error)
        results.append(
            {
                "observation": item["observation_text"],
                "human_score": human,
                "qwen_score": qwen,
                "abs_error": round(abs_error, 3),
            }
        )

    mae = round(sum(errors) / len(errors), 3) if errors else None
    return {"sample_size": len(results), "mean_absolute_error": mae, "results": results}
