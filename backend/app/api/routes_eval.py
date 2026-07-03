"""Eval harness HTTP routes."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/eval", tags=["eval"])

_RUNS: dict[str, dict] = {}


def _run_eval_job(run_id: str) -> None:
    try:
        from eval.run_eval import run_eval

        summary = run_eval()
        _RUNS[run_id]["status"] = "completed"
        _RUNS[run_id]["summary"] = summary
    except Exception as exc:  # noqa: BLE001 — scaffold captures failure for API visibility
        _RUNS[run_id]["status"] = "failed"
        _RUNS[run_id]["error"] = str(exc)


@router.post("/run", status_code=202)
def start_eval_run(background_tasks: BackgroundTasks) -> dict:
    run_id = str(uuid4())
    _RUNS[run_id] = {"status": "running"}
    background_tasks.add_task(_run_eval_job, run_id)
    return {"run_id": run_id, "status": "running"}


@router.get("/runs/{run_id}/results")
def get_eval_results(run_id: str) -> dict:
    if run_id not in _RUNS:
        return {"run_id": run_id, "status": "not_found"}
    return {"run_id": run_id, **_RUNS[run_id]}


@router.get("/importance-validation")
def get_importance_validation() -> dict:
    from eval.importance_validation import run_importance_validation

    return run_importance_validation()
