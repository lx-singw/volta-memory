"""Metric definitions and evaluation logic for Volta Memory lifecycle."""

from __future__ import annotations

import re
from typing import Any


def normalize_value(val: Any) -> str:
    if val is None:
        return ""
    # Convert to string and lowercase
    s = str(val).lower().strip()
    # Strip leading South African rand "r" symbol
    if s.startswith("r"):
        s = s[1:].strip()
    # Remove commas and spaces inside digit sequences (e.g. 3,200 -> 3200, 3 200 -> 3200)
    s = re.sub(r'(?<=\d)[,\s](?=\d)', '', s)
    # Normalize general whitespaces
    s = re.sub(r'\s+', ' ', s)
    return s


def is_retraction_or_revision(obs_lower: str) -> bool:
    keywords = ["retract", "no longer", "instead of", "corrected", "updated", "superseded", "not interest", "shifted from", "removed", "revised"]
    return any(kw in obs_lower for kw in keywords)


def evaluate_assertions(
    system: str,
    expectations: dict[str, Any],
    db_memories: list[Any],
    context_observations: list[str],
    reply: str
) -> dict[str, Any]:
    """Evaluates all assertions for a single scenario run.
    
    Returns detailed hit/total counts for recall, correction, forgetting, quality, and database states.
    """
    results = {
        "recall_hits": 0, "recall_total": 0,
        "correction_hits": 0, "correction_total": 0,
        "forgetting_hits": 0, "forgetting_total": 0,
        "quality_hits": 0, "quality_total": 0,
        "db_stored_hits": 0, "db_stored_total": 0,
        "db_superseded_hits": 0, "db_superseded_total": 0,
        "db_excluded_hits": 0, "db_excluded_total": 0
    }
    
    normalized_context = [normalize_value(obs) for obs in context_observations]
    normalized_reply = normalize_value(reply)
    
    # 1. Recall Accuracy
    should_recall = expectations.get("recall", [])
    if should_recall:
        results["recall_total"] = len(should_recall)
        for item in should_recall:
            norm_item = normalize_value(item)
            # Match item in either context observations or final reply
            if any(norm_item in ctx for ctx in normalized_context) or norm_item in normalized_reply:
                results["recall_hits"] += 1
                
    # 2. Correction Accuracy
    should_correct = expectations.get("should_correct", [])
    if should_correct:
        results["correction_total"] = len(should_correct)
        for item in should_correct:
            old_val = normalize_value(item.get("old"))
            new_val = normalize_value(item.get("new"))
            
            new_present = any(new_val in ctx for ctx in normalized_context) or new_val in normalized_reply
            
            old_absent = True
            for obs in context_observations:
                obs_lower = obs.lower()
                if old_val in normalize_value(obs):
                    if is_retraction_or_revision(obs_lower):
                        continue
                    old_absent = False
                    break
            if old_val in normalized_reply:
                old_absent = False
                
            if new_present and old_absent:
                results["correction_hits"] += 1
                
    # 3. Forgetting/Decay Accuracy (checks both should_not_recall and should_forget)
    should_forget = list(expectations.get("should_not_recall", []))
    for x in expectations.get("should_forget", []):
        if x not in should_forget:
            should_forget.append(x)
            
    if should_forget:
        results["forgetting_total"] = len(should_forget)
        for item in should_forget:
            norm_item = normalize_value(item)
            item_present = False
            for obs in context_observations:
                obs_lower = obs.lower()
                if norm_item in normalize_value(obs):
                    if is_retraction_or_revision(obs_lower):
                        continue
                    item_present = True
                    break
            if norm_item in normalized_reply:
                item_present = True
                
            if not item_present:
                results["forgetting_hits"] += 1
                
    # 4. Downstream Answer Quality
    quality_spec = expectations.get("downstream_quality", {})
    must_ref = quality_spec.get("must_reference", [])
    must_not_ref = quality_spec.get("must_not_reference", [])
    if must_ref or must_not_ref:
        total_q = len(must_ref) + len(must_not_ref)
        results["quality_total"] = total_q
        
        for item in must_ref:
            if normalize_value(item) in normalized_reply:
                results["quality_hits"] += 1
        for item in must_not_ref:
            if normalize_value(item) not in normalized_reply:
                results["quality_hits"] += 1
                
    # 5. Database Assertions (Evaluated only for Systems D/E)
    assertions = expectations.get("assertions", [])
    if (system in ["D", "E"]) and assertions:
        id_to_value = {}
        for a in assertions:
            aid = a.get("id")
            val = a.get("value")
            if aid and val is not None:
                id_to_value[aid] = val

        for assertion in assertions:
            assert_type = assertion.get("type")
            raw_target = assertion.get("value") or id_to_value.get(assertion.get("id")) or assertion.get("id")
            target_val = normalize_value(raw_target)
            
            if assert_type == "memory_stored":
                results["db_stored_total"] += 1
                created = any(target_val in normalize_value(m.observation) for m in db_memories)
                if created:
                    results["db_stored_hits"] += 1
                    
            elif assert_type == "superseded":
                results["db_superseded_total"] += 1
                old_id = assertion.get("old")
                new_id = assertion.get("new")
                
                old_raw = id_to_value.get(old_id, old_id) or assertion.get("value")
                new_raw = id_to_value.get(new_id, new_id) or assertion.get("value")
                
                old_val = normalize_value(old_raw)
                new_val = normalize_value(new_raw)
                
                old_superseded = any(
                    old_val in normalize_value(m.observation) and m.is_superseded
                    for m in db_memories
                )
                new_active = any(
                    new_val in normalize_value(m.observation) and not m.is_superseded
                    for m in db_memories
                )
                if old_superseded and new_active:
                    results["db_superseded_hits"] += 1
                    
            elif assert_type == "excluded_at_query":
                results["db_excluded_total"] += 1
                # Verification: memory was successfully created initially...
                was_created = any(target_val in normalize_value(m.observation) for m in db_memories)
                # ...but is now correctly excluded from the active context retrieval
                is_excluded = not any(target_val in ctx for ctx in normalized_context)
                if was_created and is_excluded:
                    results["db_excluded_hits"] += 1
                    
    return results


def summarize_metrics(runs: list[dict]) -> dict:
    """Summarizes runs by summing hits and totals across all replicates."""
    summary = {}
    for key in [
        "recall", "correction", "forgetting", "quality",
        "db_stored", "db_superseded", "db_excluded"
    ]:
        hits_key = f"{key}_hits"
        total_key = f"{key}_total"
        
        sum_hits = sum(r["metrics"][hits_key] for r in runs if hits_key in r["metrics"])
        sum_total = sum(r["metrics"][total_key] for r in runs if total_key in r["metrics"])
        
        summary[key] = {
            "hits": sum_hits,
            "total": sum_total,
            "ratio": sum_hits / sum_total if sum_total > 0 else None
        }
    return summary
