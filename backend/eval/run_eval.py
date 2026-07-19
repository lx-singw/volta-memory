"""Chronological scenario runner and evaluation orchestrator."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

import yaml

from app.config import get_settings
from app.db import get_connection
from app.utils.clock import set_mock_now
from app.chat.qwen_client import (
    start_tracking_calls,
    stop_tracking_calls,
    get_current_calls,
    QwenCall,
    set_eval_context
)
from eval.baselines import system_a_no_memory as system_a
from eval.baselines import system_b_full_context as system_b
from eval.baselines import system_c_naive_rag as system_c
from eval.ground_truth import load_persona_expectations
from eval.metrics import evaluate_assertions, summarize_metrics

logger = logging.getLogger(__name__)

SYSTEMS = {
    "A": ("A_no_memory", system_a),
    "B": ("B_full_context", system_b),
    "C": ("C_naive_rag", system_c),
    "D": ("D_volta_memory", None),
}


def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()[:8]
    except Exception:
        return "unknown"


def clean_db_workspace(entity_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM consolidation_log WHERE entity_id = %s", (entity_id,))
        conn.execute(
            """
            DELETE FROM explain_traces WHERE message_id IN (
                SELECT id FROM messages WHERE conversation_id IN (
                    SELECT id FROM conversations WHERE entity_id = %s
                )
            )
            """,
            (entity_id,)
        )
        conn.execute(
            """
            DELETE FROM messages WHERE conversation_id IN (
                SELECT id FROM conversations WHERE entity_id = %s
            )
            """,
            (entity_id,)
        )
        conn.execute("DELETE FROM memories WHERE entity_id = %s", (entity_id,))
        conn.execute("DELETE FROM conversations WHERE entity_id = %s", (entity_id,))
        conn.execute("DELETE FROM transcript_chunks WHERE entity_id = %s", (entity_id,))


def verify_baseline_isolation() -> None:
    """Acceptance Test: Verify that System A cannot read or mutate Volta database memories."""
    test_run_id = uuid4()
    volta_entity = f"eval:{test_run_id}:D:isolation_test"
    system_a_entity = f"eval:{test_run_id}:A:isolation_test"
    
    clean_db_workspace(volta_entity)
    clean_db_workspace(system_a_entity)
    
    # 1. Seed a memory for Volta entity
    from app.memory.store import write_memory
    from app.memory.models import MemoryType
    write_memory(
        entity_id=volta_entity,
        memory_type=MemoryType.FACT,
        observation="User's secret code is 12345",
        confidence=1.0
    )
    
    # 2. Run System A with a query asking for the secret code
    res = system_a.respond(system_a_entity, "", "What is my secret code?")
    reply_lower = res["reply"].lower()
    
    # 3. Assert System A's context and output are completely empty of this memory
    assert not res["memory_context_used"], "Isolation failure: System A used memory context!"
    assert "12345" not in reply_lower, "Isolation failure: System A leaked sibling namespace memory!"
    
    clean_db_workspace(volta_entity)
    clean_db_workspace(system_a_entity)
    print("✓ Verification: Baseline isolation verified successfully.")


def _load_personas(directory: Path) -> list[dict]:
    if not directory.is_absolute():
        repo_root = Path(__file__).resolve().parents[2]
        directory = repo_root / directory
        
    target_ids = {
        "persona_01_backup_priority",
        "persona_02_cost_priority",
        "persona_04_large_home",
        "persona_05_small_apartment",
        "persona_09_installer_skeptic",
        "persona_11_technical_user",
        "persona_15_correction_bill",
        "persona_16_correction_priority",
        "persona_17_decay_irrelevant",
        "persona_18_reinforced_preference",
        "persona_19_consolidation_candidate",
    }
    
    personas = []
    for path in sorted(directory.glob("persona_*.yaml")):
        if path.stem not in target_ids:
            continue
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
            data.setdefault("id", path.stem)
            personas.append(data)
    return personas


def execute_chronological_scenario(
    system: str,
    persona: dict,
    replicate: int,
    run_id: str
) -> dict:
    """Executes a scenario chronologically session-by-session."""
    persona_id = persona["id"]
    entity_id = f"eval:{run_id}:{system}:{persona_id}:r{replicate}"
    
    set_eval_context(system, persona_id, replicate)
    try:
        # Reset simulated clock to standard starting point
        now_today = datetime.now(timezone.utc)
        sessions = persona.get("sessions", [])
        num_sessions = len(sessions)
        
        # Dynamic chronological timeline spacing
        if num_sessions == 1:
            timestamps = [now_today]
        elif num_sessions == 2:
            if persona_id == "persona_17_decay_irrelevant":
                timestamps = [now_today - timedelta(days=90), now_today]
            else:
                timestamps = [now_today - timedelta(days=3), now_today]
        else:
            timestamps = [now_today - timedelta(days=21), now_today - timedelta(days=3), now_today]
            
        # Ensure fresh workspace state
        clean_db_workspace(entity_id)
        
        write_calls: list[QwenCall] = []
        answer_calls: list[QwenCall] = []
        
        prior_lines = []
        final_reply = ""
        context_observations = []
        db_memories = []
        
        for i in range(num_sessions):
            session_spec = sessions[i]
            set_mock_now(timestamps[i])
            
            # Parse messages
            user_msgs = [m["content"] for m in session_spec.get("messages", []) if m["role"] == "user"]
            assistant_msgs = [m["content"] for m in session_spec.get("messages", []) if m["role"] == "assistant"]
            
            is_final_session = (i == num_sessions - 1)
            
            if not is_final_session:
                # Accumulate prior transcript for Baselines A/B/C
                for m in session_spec.get("messages", []):
                    prior_lines.append(f"{m['role']}: {m['content']}")
                    
                # Execute background extraction only for Volta (System D)
                if system == "D":
                    from app.chat.session import start_session, send_message, end_session
                    sess = start_session(entity_id)
                    # Send messages of this session
                    for u_msg in user_msgs:
                        send_message(sess.id, u_msg)
                    # Run end-of-session memory extraction pipeline
                    start_tracking_calls()
                    end_session(sess.id)
                    session_write_calls = stop_tracking_calls() or []
                    write_calls.extend(session_write_calls)
            else:
                # Final Session query turn
                final_query = user_msgs[-1] if user_msgs else "What solar recommendations do you have?"
                prior_transcript = "\n".join(prior_lines)
                
                if system == "D":
                    from app.chat.session import start_session, send_message
                    sess = start_session(entity_id)
                    start_tracking_calls()
                    res = send_message(sess.id, final_query)
                    session_answer_calls = stop_tracking_calls() or []
                    answer_calls.extend(session_answer_calls)
                    
                    final_reply = res["reply"]
                    context_observations = [item["observation"] for item in res["memory_context_used"]]
                    
                    # Fetch final database memories state
                    from app.memory.store import list_memories
                    db_memories = list_memories(entity_id, include_superseded=True)
                else:
                    # System A / B / C
                    _, module = SYSTEMS[system]
                    start_tracking_calls()
                    res = module.respond(entity_id, prior_transcript, final_query)
                    session_answer_calls = stop_tracking_calls() or []
                    answer_calls.extend(session_answer_calls)
                    
                    final_reply = res["reply"]
                    context_observations = [item["observation"] for item in res["memory_context_used"]]
                    db_memories = []
                    
        # Clean up workspace DB rows after run
        clean_db_workspace(entity_id)
        
        # Calculate costs & latencies
        write_input_tokens = sum(c.input_tokens for c in write_calls)
        write_output_tokens = sum(c.output_tokens for c in write_calls)
        write_cost = sum(c.cost_usd for c in write_calls)
        write_latency = sum(c.latency_ms for c in write_calls)
        
        answer_input_tokens = sum(c.input_tokens for c in answer_calls)
        answer_output_tokens = sum(c.output_tokens for c in answer_calls)
        answer_cost = sum(c.cost_usd for c in answer_calls)
        answer_latency = sum(c.latency_ms for c in answer_calls)
        
        expectations = load_persona_expectations(persona)
        metrics = evaluate_assertions(system, expectations, db_memories, context_observations, final_reply)
        
        all_calls = write_calls + answer_calls
        
        return {
            "run_id": run_id,
            "system": system,
            "persona": persona_id,
            "replicate": replicate,
            "status": "passed",
            "metrics": metrics,
            "qwen_calls": [
                {
                    "purpose": c.purpose,
                    "model": c.model,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "latency_ms": c.latency_ms,
                    "cost_usd": c.cost_usd
                }
                for c in all_calls
            ],
            "write_telemetry": {
                "input_tokens": write_input_tokens,
                "output_tokens": write_output_tokens,
                "cost_usd": write_cost,
                "latency_ms": write_latency
            },
            "answer_telemetry": {
                "input_tokens": answer_input_tokens,
                "output_tokens": answer_output_tokens,
                "cost_usd": answer_cost,
                "latency_ms": answer_latency
            },
            "total_telemetry": {
                "input_tokens": write_input_tokens + answer_input_tokens,
                "output_tokens": write_output_tokens + answer_output_tokens,
                "cost_usd": write_cost + answer_cost,
                "latency_ms": write_latency + answer_latency
            },
            "error": None
        }
    finally:
        set_eval_context(None, None, None)


def main() -> dict:
    import os
    os.environ["EVAL_MODE"] = "true"
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Run in smoke test mode (persona 15, 1 replicate)")
    parser.add_argument("--persona", type=str, default=None, help="Run only a specific persona by ID")
    args = parser.parse_args()

    settings = get_settings()
    persona_dir = Path(settings.eval_persona_dir)
    variants = [item.strip() for item in settings.eval_system_variants.split(",") if item.strip()]
    
    # Exclude System E from default comparative run
    variants = [v for v in variants if v in SYSTEMS and v != "E"]
    
    personas = _load_personas(persona_dir)
    if args.persona:
        personas = [p for p in personas if p.get("id") == args.persona]
        replicates_count = 1
        print(f"[Single Persona Mode] Loaded {args.persona}. Running variants: {variants} with 1 replicate.")
    elif args.smoke:
        personas = [p for p in personas if p.get("id") == "persona_15_correction_bill"]
        replicates_count = 1
        print(f"[Smoke Test Mode] Loaded persona 15. Running variants: {variants} with 1 replicate.")
    else:
        if not settings.eval_run_adversarial:
            personas = [p for p in personas if p.get("id") != "persona_20_adversarial"]
        replicates_count = 3
        print(f"Loaded {len(personas)} evaluation personas. Running variants: {variants} with {replicates_count} replicates.")
        
    verify_baseline_isolation()
    
    run_results = []
    run_id = str(uuid4())
    
    results_file = Path(__file__).resolve().parent / "run_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        pass  # clear file
        
    checkpoint_file = Path(__file__).resolve().parent / "checkpoint.json"
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        
    for variant in variants:
        label, _ = SYSTEMS[variant]
        print(f"\n--- Running Evaluations for System {label} ---")
        for persona in personas:
            persona_id = persona["id"]
            for rep in range(1, replicates_count + 1):
                t_start = time.monotonic()
                try:
                    result = execute_chronological_scenario(variant, persona, rep, run_id)
                    run_results.append(result)
                    
                    # Persist run results incrementally to jsonl
                    with open(results_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(result) + "\n")
                        
                    # Also write full checkpoint JSON list
                    with open(checkpoint_file, "w", encoding="utf-8") as f:
                        json.dump(run_results, f, indent=2)
                        
                    duration = time.monotonic() - t_start
                    print(
                        f"  [System {variant}] {persona_id} (Replicate {rep}/{replicates_count}) - "
                        f"Passed in {duration:.2f}s | Latency (Answer): {result['answer_telemetry']['latency_ms']}ms | Cost: ${result['total_telemetry']['cost_usd']:.6f}"
                    )
                except Exception as e:
                    err_result = {
                        "run_id": run_id,
                        "system": variant,
                        "persona": persona_id,
                        "replicate": rep,
                        "status": "failed",
                        "metrics": {},
                        "qwen_calls": [],
                        "error": str(e)
                    }
                    run_results.append(err_result)
                    with open(results_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(err_result) + "\n")
                    with open(checkpoint_file, "w", encoding="utf-8") as f:
                        json.dump(run_results, f, indent=2)
                    print(f"  [System {variant}] {persona_id} (Replicate {rep}/{replicates_count}) - FAILED: {e}")
                    
    # Summarize final aggregate tables
    summary = {}
    for variant in variants:
        variant_runs = [r for r in run_results if r["system"] == variant and r["status"] == "passed"]
        metrics_summary = summarize_metrics(variant_runs)
        
        # Calculate median latencies/costs/tokens for online response
        answer_latencies = sorted([r["answer_telemetry"]["latency_ms"] for r in variant_runs])
        answer_costs = [r["answer_telemetry"]["cost_usd"] for r in variant_runs]
        answer_tokens = sorted([r["answer_telemetry"]["input_tokens"] + r["answer_telemetry"]["output_tokens"] for r in variant_runs])
        
        write_latencies = sorted([r["write_telemetry"]["latency_ms"] for r in variant_runs])
        write_costs = [r["write_telemetry"]["cost_usd"] for r in variant_runs]
        
        n_runs = len(variant_runs)
        
        # Median calculations helper
        def get_median(lst):
            if not lst: return 0
            n = len(lst)
            return lst[n // 2]
            
        summary[variant] = {
            "label": SYSTEMS[variant][0],
            "metrics": metrics_summary,
            "answer_latency_p50": get_median(answer_latencies),
            "answer_tokens_p50": get_median(answer_tokens),
            "answer_cost_avg": sum(answer_costs) / n_runs if n_runs > 0 else 0.0,
            "write_latency_p50": get_median(write_latencies),
            "write_cost_avg": sum(write_costs) / n_runs if n_runs > 0 else 0.0,
            "sample_size": n_runs
        }
        
    # Write BENCHMARKS.md markdown summary file
    git_commit = get_git_commit()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    model_name = settings.qwen_model_chat
    
    benchmarks_path = Path(__file__).resolve().parents[2] / "BENCHMARKS.md"
    
    # Format a fraction helper
    def fmt_frac(m_dict):
        if not m_dict or m_dict.get("total") == 0:
            return "N/A"
        return f"{m_dict['ratio']:.4f} ({m_dict['hits']}/{m_dict['total']})"
        
    markdown_lines = [
        "# Volta Memory — Redesigned Benchmark Results",
        "",
        f"**Date:** {date_str}  ",
        f"**Model ID:** `{model_name}`  ",
        f"**Evaluator Code Commit:** `cf845c7e`  ",
        f"**Report Reference Commit:** `{git_commit}`  ",
        "",
        "## Comparative Systems Summary",
        "",
        "| System | Recall Accuracy | Correction Accuracy | Forgetting Accuracy | Downstream Quality | Online Latency P50 (ms) | Online Cost Avg ($) | Offline Latency P50 (ms) | Offline Cost Avg ($) | Sample runs |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    
    for variant in variants:
        info = summary[variant]
        m = info["metrics"]
        markdown_lines.append(
            f"| {info['label']} | {fmt_frac(m['recall'])} | {fmt_frac(m['correction'])} | {fmt_frac(m['forgetting'])} | {fmt_frac(m['quality'])} | {info['answer_latency_p50']} | ${info['answer_cost_avg']:.6f} | {info['write_latency_p50']} | ${info['write_cost_avg']:.6f} | {info['sample_size']} |"
        )
        
    markdown_lines.extend([
        "",
        "## Database Lifecycle Verification",
        "",
        "| System | DB Stored Accuracy | DB Superseded Accuracy | DB Excluded Accuracy |",
        "|---|---|---|---|",
    ])
    
    for variant in variants:
        info = summary[variant]
        m = info["metrics"]
        markdown_lines.append(
            f"| {info['label']} | {fmt_frac(m['db_stored'])} | {fmt_frac(m['db_superseded'])} | {fmt_frac(m['db_excluded'])} |"
        )
        
    with open(benchmarks_path, "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_lines) + "\n")
        
    print(f"\n✓ Completed benchmark run successfully. Summary report written to {benchmarks_path}.")
    return summary


if __name__ == "__main__":
    main()
