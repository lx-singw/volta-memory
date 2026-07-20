#!/usr/bin/env python3
"""Create public, versioned benchmark artifacts from an evaluator JSONL file."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from eval.artifacts import (  # noqa: E402
    build_evaluation_artifact,
    render_benchmarks_markdown,
    summarize_runs,
    write_evaluation_artifacts,
)


LABELS = {
    "A": "A_no_memory",
    "B": "B_full_context",
    "C": "C_naive_rag",
    "D": "D_volta_memory",
}


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=REPO_ROOT / "backend" / "eval" / "run_results.jsonl",
    )
    parser.add_argument("--run-id", help="Select one run from a file containing checkpoints or prior runs.")
    parser.add_argument("--model", default="qwen-max")
    parser.add_argument("--evaluator-commit", default=None)
    parser.add_argument("--completed-at", default=None, help="ISO-8601 UTC completion time.")
    parser.add_argument("--write-benchmarks", action="store_true")
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in args.results.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise SystemExit(f"No evaluation results found in {args.results}")
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(str(row.get("run_id", "unknown")), []).append(row)
    selected_run = args.run_id or max(groups, key=lambda key: len(groups[key]))
    selected = groups.get(selected_run)
    if not selected:
        raise SystemExit(f"Run ID {selected_run!r} is not present in {args.results}")

    systems = [key for key in LABELS if any(row.get("system") == key for row in selected)]
    labels = {key: LABELS[key] for key in systems}
    personas = sorted({str(row.get("persona")) for row in selected})
    replicates = max((int(row.get("replicate") or 0) for row in selected), default=0)
    configuration = {
        "systems": systems,
        "personas": personas,
        "replicates": replicates,
        "expectedRuns": len(systems) * len(personas) * replicates,
        "sourceResults": str(args.results.resolve().relative_to(REPO_ROOT)),
    }
    completed = args.completed_at or datetime.fromtimestamp(
        args.results.stat().st_mtime, tz=timezone.utc
    ).isoformat()
    artifact, cases = build_evaluation_artifact(
        run_id=selected_run,
        runs=selected,
        systems=summarize_runs(selected, labels),
        model=args.model,
        evaluator_code_commit=args.evaluator_commit or git_commit(),
        configuration=configuration,
        completed_at=completed,
    )
    summary_path, cases_path = write_evaluation_artifacts(REPO_ROOT, artifact, cases)
    if args.write_benchmarks:
        (REPO_ROOT / "BENCHMARKS.md").write_text(render_benchmarks_markdown(artifact), encoding="utf-8")
    print(f"Wrote {summary_path} and {cases_path} from run {selected_run} ({len(selected)} cases).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
