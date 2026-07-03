"""Eval metrics — recall, forgetting, contradiction handling, cost, latency."""

from __future__ import annotations

from statistics import mean


def recall_accuracy(expected: list[str], observed: list[str]) -> float | None:
    if not expected:
        return None
    hits = sum(1 for item in expected if any(item.lower() in obs.lower() for obs in observed))
    return hits / len(expected)


def forgetting_correctness(excluded_irrelevant: int, total_irrelevant: int) -> float | None:
    if total_irrelevant == 0:
        return None
    return excluded_irrelevant / total_irrelevant


def summarize_metrics(rows: list[dict]) -> dict:
    recalls = [row["recall_accuracy"] for row in rows if row.get("recall_accuracy") is not None]
    forgetting = [row["forgetting_correctness"] for row in rows if row.get("forgetting_correctness") is not None]
    costs = [row["cost_usd"] for row in rows if row.get("cost_usd") is not None]

    return {
        "recall_accuracy": round(mean(recalls), 4) if recalls else None,
        "forgetting_correctness": round(mean(forgetting), 4) if forgetting else None,
        "cost_usd_avg": round(mean(costs), 6) if costs else None,
        "sample_size": len(rows),
    }
