"""Versioned, sanitised evaluation artifacts for public benchmark claims.

The evaluator writes a human-readable ``BENCHMARKS.md`` and machine-readable
artifacts from the same in-memory result set. Keeping that rendering logic here
prevents README, slides, and submission text from drifting into hand-edited
numbers.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


METRIC_KEYS = (
    "recall",
    "correction",
    "forgetting",
    "quality",
    "db_stored",
    "db_superseded",
    "db_excluded",
)


def _json_line(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _safe_case(result: dict[str, Any]) -> dict[str, Any]:
    """Keep reproducible measurements without publishing conversations or secrets."""
    return {
        "run_id": result.get("run_id"),
        "system": result.get("system"),
        "persona": result.get("persona"),
        "replicate": result.get("replicate"),
        "status": result.get("status"),
        "metrics": result.get("metrics", {}),
        "qwen_calls": result.get("qwen_calls", []),
        "write_telemetry": result.get("write_telemetry", {}),
        "answer_telemetry": result.get("answer_telemetry", {}),
        "total_telemetry": result.get("total_telemetry", {}),
        # Error text is intentionally not published; it can contain provider or
        # transport details that belong in protected operational logs.
        "error": "failed" if result.get("status") == "failed" else None,
    }


def _metric(hits: int, total: int) -> dict[str, Any]:
    return {"hits": hits, "total": total, "ratio": hits / total if total else None}


def summarize_runs(
    runs: list[dict[str, Any]], labels: dict[str, str]
) -> dict[str, dict[str, Any]]:
    """Aggregate successful cases using documented P50 and average-cost rules."""
    output: dict[str, dict[str, Any]] = {}
    for system, label in labels.items():
        system_runs = [
            row
            for row in runs
            if row.get("system") == system and row.get("status") == "passed"
        ]
        metrics: dict[str, dict[str, Any]] = {}
        for key in METRIC_KEYS:
            metrics[key] = _metric(
                sum(int(row.get("metrics", {}).get(f"{key}_hits", 0)) for row in system_runs),
                sum(int(row.get("metrics", {}).get(f"{key}_total", 0)) for row in system_runs),
            )

        answer_latencies = [
            float(row.get("answer_telemetry", {}).get("latency_ms", 0)) for row in system_runs
        ]
        answer_tokens = [
            float(row.get("answer_telemetry", {}).get("input_tokens", 0))
            + float(row.get("answer_telemetry", {}).get("output_tokens", 0))
            for row in system_runs
        ]
        answer_costs = [
            float(row.get("answer_telemetry", {}).get("cost_usd", 0)) for row in system_runs
        ]
        write_latencies = [
            float(row.get("write_telemetry", {}).get("latency_ms", 0)) for row in system_runs
        ]
        write_costs = [
            float(row.get("write_telemetry", {}).get("cost_usd", 0)) for row in system_runs
        ]
        count = len(system_runs)
        output[system] = {
            "label": label,
            "metrics": metrics,
            "online": {
                "latencyP50Ms": median(answer_latencies) if answer_latencies else 0,
                "tokensP50": median(answer_tokens) if answer_tokens else 0,
                "costAvgUsd": sum(answer_costs) / count if count else 0.0,
            },
            "offline": {
                "latencyP50Ms": median(write_latencies) if write_latencies else 0,
                "costAvgUsd": sum(write_costs) / count if count else 0.0,
            },
            "sampleRuns": count,
        }
    return output


def build_evaluation_artifact(
    *,
    run_id: str,
    runs: list[dict[str, Any]],
    systems: dict[str, dict[str, Any]],
    model: str,
    evaluator_code_commit: str,
    configuration: dict[str, Any],
    completed_at: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cases = sorted(
        (_safe_case(result) for result in runs),
        key=lambda row: (
            str(row.get("system", "")),
            str(row.get("persona", "")),
            int(row.get("replicate") or 0),
        ),
    )
    case_payload = "\n".join(_json_line(case) for case in cases) + ("\n" if cases else "")
    case_sha = hashlib.sha256(case_payload.encode("utf-8")).hexdigest()
    config_sha = hashlib.sha256(_json_line(configuration).encode("utf-8")).hexdigest()
    successful = sum(1 for row in runs if row.get("status") == "passed")

    artifact = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "completedAt": completed_at or datetime.now(timezone.utc).isoformat(),
        "runId": run_id,
        "evaluatorCodeCommit": evaluator_code_commit or "unknown",
        "model": model,
        "configuration": configuration,
        "configurationSha256": config_sha,
        "expectedRuns": configuration.get("expectedRuns", len(runs)),
        "successfulRuns": successful,
        "failedRuns": len(runs) - successful,
        "caseArtifact": {
            "path": "backend/eval/artifacts/evaluation-cases.jsonl",
            "sha256": case_sha,
            "redaction": "Conversation text, provider payloads, and error details are excluded.",
        },
        "systems": systems,
    }
    return artifact, cases


def write_evaluation_artifacts(
    repo_root: Path,
    artifact: dict[str, Any],
    cases: list[dict[str, Any]],
) -> tuple[Path, Path]:
    artifact_dir = repo_root / "backend" / "eval" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    cases_path = artifact_dir / "evaluation-cases.jsonl"
    summary_path = artifact_dir / "evaluation-summary.json"
    cases_path.write_text(
        "\n".join(_json_line(case) for case in cases) + ("\n" if cases else ""), encoding="utf-8"
    )
    summary_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary_path, cases_path


def _fmt_metric(metric: dict[str, Any]) -> str:
    if not metric or not metric.get("total"):
        return "N/A"
    return f"{metric['ratio']:.4f} ({metric['hits']}/{metric['total']})"


def _fmt_number(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{value:.1f}" if isinstance(value, float) else str(value)


def render_benchmarks_markdown(artifact: dict[str, Any]) -> str:
    lines = [
        "# Volta Memory Benchmark Results",
        "",
        "> This report is generated from [`evaluation-summary.json`](backend/eval/artifacts/evaluation-summary.json). Do not hand-edit metric values.",
        "",
        "## Run provenance",
        "",
        f"- Run ID: `{artifact['runId']}`",
        f"- Completed: `{artifact['completedAt']}`",
        f"- Evaluator code commit: `{artifact['evaluatorCodeCommit']}`",
        f"- Qwen chat model: `{artifact['model']}`",
        f"- Cases: `{artifact['successfulRuns']}/{artifact['expectedRuns']}` successful; `{artifact['failedRuns']}` failed",
        f"- Sanitised case artifact SHA-256: `{artifact['caseArtifact']['sha256']}`",
        "",
        "## Comparative systems",
        "",
        "| System | Recall accuracy | Correction accuracy | Forgetting accuracy | Downstream quality | Online latency P50 (ms) | Online cost avg (USD) | Offline latency P50 (ms) | Offline cost avg (USD) | Runs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system in artifact["systems"].values():
        metrics = system["metrics"]
        online = system["online"]
        offline = system["offline"]
        lines.append(
            "| {label} | {recall} | {correction} | {forgetting} | {quality} | {online_latency} | ${online_cost:.6f} | {offline_latency} | ${offline_cost:.6f} | {runs} |".format(
                label=system["label"],
                recall=_fmt_metric(metrics["recall"]),
                correction=_fmt_metric(metrics["correction"]),
                forgetting=_fmt_metric(metrics["forgetting"]),
                quality=_fmt_metric(metrics["quality"]),
                online_latency=_fmt_number(online["latencyP50Ms"]),
                online_cost=online["costAvgUsd"],
                offline_latency=_fmt_number(offline["latencyP50Ms"]),
                offline_cost=offline["costAvgUsd"],
                runs=system["sampleRuns"],
            )
        )

    lines.extend(
        [
            "",
            "## Database lifecycle verification",
            "",
            "| System | DB stored accuracy | DB superseded accuracy | DB excluded accuracy |",
            "|---|---:|---:|---:|",
        ]
    )
    for system in artifact["systems"].values():
        metrics = system["metrics"]
        lines.append(
            f"| {system['label']} | {_fmt_metric(metrics['db_stored'])} | {_fmt_metric(metrics['db_superseded'])} | {_fmt_metric(metrics['db_excluded'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The report is comparative evidence, not a blanket quality claim. Volta's correction, selective-forgetting, recall, latency, and cost results should be read together with the per-case artifact and the documented baseline definitions in [EVALUATION.md](EVALUATION.md).",
            "",
        ]
    )
    return "\n".join(lines)
