# Volta Memory — API Reference
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

---

## Table of Contents
- [1. Overview](#1-overview)
- [2. Chat Endpoints](#2-chat-endpoints)
- [3. Memory Debug Endpoints](#3-memory-debug-endpoints)

---

## 1. Overview

**Base URL:** `http://localhost:8000` (dev) — Alibaba Cloud-hosted URL in production
**Format:** JSON
**Auth:** None — single-demo-consumer scope, out of scope per PRD Section 5

---

## 2. Chat Endpoints

### POST /sessions
Start a new conversation session for the demo entity.

**Response 201:**
```json
{
  "session_id": "uuid",
  "entity_id": "demo-consumer-1",
  "started_at": "2026-06-28T09:00:00Z"
}
```

---

### POST /sessions/{session_id}/messages
Send a message and get Volta's response.

**Request body:**
```json
{
  "message": "I want to understand solar for my house, load-shedding is killing me"
}
```

**Response 200:**
```json
{
  "reply": "Totally understand — load-shedding is exhausting to plan around. 
            Before I recommend anything, tell me: is your main concern getting 
            your bill down, having backup power during outages, or both?",
  "memory_context_used": [],
  "tokens_used": 142
}
```

In later sessions, `memory_context_used` is populated:
```json
{
  "reply": "Last time you mentioned backup power was the real driver — still 
            the case? If so, let's talk battery sizing for your situation.",
  "memory_context_used": [
    { "memory_id": "uuid", "observation": "backup power is primary motivation", 
      "effective_confidence": 0.81, "tier": "high" }
  ],
  "tokens_used": 168
}
```

---

### POST /sessions/{session_id}/end
Explicitly end a session, triggering memory extraction.

**Response 200:**
```json
{
  "session_id": "uuid",
  "ended_at": "2026-06-28T09:14:00Z",
  "memories_written": [
    { "memory_type": "preference", "observation": "backup power is primary motivation", "confidence": 0.75 },
    { "memory_type": "fact", "observation": "monthly bill is R3,200", "confidence": 0.80 }
  ]
}
```

---

## 3. Memory Debug Endpoints

These power the transparency view shown in the demo video (PRD 4.6).

### GET /entities/{entity_id}/memories
Returns all memories for the demo entity, including superseded ones, with computed effective confidence.

**Response 200:**
```json
{
  "entity_id": "demo-consumer-1",
  "memories": [
    {
      "id": "uuid",
      "memory_type": "preference",
      "observation": "backup power is primary motivation",
      "base_confidence": 0.75,
      "effective_confidence": 0.81,
      "reinforcement_count": 2,
      "is_superseded": false,
      "last_reinforced_at": "2026-07-01T10:00:00Z"
    },
    {
      "id": "uuid",
      "memory_type": "fact",
      "observation": "monthly bill is R3,200",
      "base_confidence": 0.80,
      "effective_confidence": 0.12,
      "reinforcement_count": 1,
      "is_superseded": true,
      "superseded_by_id": "uuid"
    },
    {
      "id": "uuid",
      "memory_type": "correction",
      "observation": "monthly bill is R3,800",
      "base_confidence": 0.95,
      "effective_confidence": 0.93,
      "reinforcement_count": 1,
      "is_superseded": false
    }
  ]
}
```

This single endpoint is the one shown on screen in the demo video immediately after a memory-driven response — it is the proof artifact that the mechanism is real, not scripted theatre.

---

### GET /entities/{entity_id}/memories/active-context?query={text}
Returns exactly what would be retrieved and packed into the system prompt for a given hypothetical query — useful for demonstrating token budget enforcement directly.

**Response 200:**
```json
{
  "query": "what would a system cost me now?",
  "max_tokens_budget": 800,
  "tokens_used": 214,
  "packed_memories": [
    { "observation": "monthly bill is R3,800", "score": 0.91 },
    { "observation": "backup power is primary motivation", "score": 0.74 }
  ],
  "excluded_below_threshold": 1,
  "excluded_over_budget": 0
}
```


---

# ADDENDUM — Endpoints for Maximum-Depth Upgrades
**Added: June 2026**

---

## 4. Explainability Endpoint

### GET /messages/{message_id}/explain
Returns the parsed explainability trace for a given assistant response.

**Response 200:**
```json
{
  "message_id": "uuid",
  "referenced_memories": [
    { "id": "uuid", "observation": "backup power is primary motivation", "importance_score": 0.82 }
  ],
  "primary_influence_memory_id": "uuid",
  "confidence_tier_choice": "Stated plainly — memory effective_confidence was 0.87, above the 0.85 plain-statement threshold",
  "counterfactual": "Without this memory, the response would have asked about priorities again rather than referencing backup power directly"
}
```

---

## 5. Importance Validation Endpoint

### GET /eval/importance-validation
Returns the human-vs-Qwen importance scoring benchmark results (Design Doc Section 11.3).

**Response 200:**
```json
{
  "sample_size": 40,
  "mean_absolute_error": 0.11,
  "results": [
    { "observation": "I really can't deal with another outage during exam season", 
      "human_score": 0.9, "qwen_score": 0.85, "abs_error": 0.05 }
  ]
}
```

---

## 6. Eval Harness Endpoints

### POST /eval/run
Triggers a full eval harness run across all 20 personas and all 4 system variants (A/B/C/D).

**Response 202 (async — long-running):**
```json
{
  "run_id": "uuid",
  "status": "running",
  "estimated_completion": "2026-07-02T10:15:00Z"
}
```

### GET /eval/runs/{run_id}/results
```json
{
  "run_id": "uuid",
  "status": "completed",
  "summary": {
    "A_no_memory":     { "recall_accuracy": 0.31, "forgetting_correctness": null, "cost_usd_avg": 0.008 },
    "B_full_context":  { "recall_accuracy": 0.94, "forgetting_correctness": 0.12, "cost_usd_avg": 0.061 },
    "C_naive_rag":     { "recall_accuracy": 0.71, "forgetting_correctness": 0.38, "cost_usd_avg": 0.019 },
    "D_volta_memory":  { "recall_accuracy": 0.91, "forgetting_correctness": 0.88, "cost_usd_avg": 0.014 }
  },
  "adversarial_persona_result": {
    "poisoning_attempt_suppressed": true,
    "plausibility_flag_correctly_applied": true
  }
}
```

*(Illustrative figures shown for schema clarity — actual run replaces these with real measured results, written into `BENCHMARKS.md`.)*

---

## 7. Consolidation Endpoint

### GET /entities/{entity_id}/consolidation-log
```json
{
  "entity_id": "demo-consumer-1",
  "consolidations": [
    {
      "triggered_at_session_count": 5,
      "memories_consolidated": 7,
      "consolidated_observation": "Consistently price-sensitive but values reliability; has asked about financing twice",
      "token_savings_estimate": 340
    }
  ]
}
```

---

## 8. Second Persona Endpoint

### POST /sessions?persona=study_coach
Starts a session using the study-coach persona instead of Volta, sharing the identical memory engine — demonstrates the same `/sessions`, `/messages`, and memory endpoints work unmodified against a completely different domain.

**Response 201:**
```json
{
  "session_id": "uuid",
  "persona": "study_coach",
  "entity_id": "demo-consumer-2",
  "started_at": "2026-07-02T09:00:00Z"
}
```

