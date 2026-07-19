"""Baseline C — embedding-only naive RAG in memory."""

from __future__ import annotations

from app.chat.qwen_client import get_qwen_client
from app.memory.explainability import parse_explain_block


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(x * y for x, y in zip(v1, v2))
    n1 = sum(x * x for x in v1) ** 0.5
    n2 = sum(x * x for x in v2) ** 0.5
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


def respond(entity_id: str, transcript: str, user_message: str) -> dict:
    qwen = get_qwen_client()
    
    # 1. Parse prior turns into distinct candidate chunks
    turns = [line.strip() for line in transcript.splitlines() if line.strip()]
    
    top_chunks = []
    if turns:
        # 2. Embed the turns and query locally in-memory (fully isolated from DB tables)
        try:
            query_emb = qwen.embed(user_message, purpose="embedding")
            candidates = []
            for turn in turns:
                turn_emb = qwen.embed(turn, purpose="embedding")
                sim = cosine_similarity(query_emb, turn_emb)
                candidates.append((sim, turn))
            
            # Sort descending by similarity
            candidates.sort(key=lambda x: x[0], reverse=True)
            
            # Select top-k within budget (e.g., top 3 matching turns)
            top_chunks = [turn for _, turn in candidates[:3]]
        except Exception:
            # Fallback to last 2 turns if embedding fails
            top_chunks = turns[-2:]
            
    chunks_str = "\n".join(f"- {chunk}" for chunk in top_chunks)
    
    system_prompt = (
        "You are Volta, a warm and direct AI energy advisor for South African homeowners. "
        "Use plain language. Focus on solar sizing, load-shedding backup planning, and "
        "basic SA electricity tariff context. Do not generate quotes or connect to installers.\n\n"
        "Here are some recalled fragments of past conversations with this user:\n"
        f"{chunks_str}\n\n"
        "Reply directly to the user's message using these recalled fragments if helpful."
    )
    messages = [{"role": "user", "content": user_message}]
    
    # Baseline C calls clean complete without tools
    reply = qwen.complete(system_prompt, messages, purpose="generation")
    explain = parse_explain_block(reply)
    user_reply = explain.user_facing_text
    
    return {
        "reply": user_reply,
        "memory_context_used": [{"observation": chunk} for chunk in top_chunks]
    }
