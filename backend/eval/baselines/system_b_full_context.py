"""Baseline B — naive full transcript concatenation."""

from __future__ import annotations

from app.chat.qwen_client import get_qwen_client
from app.memory.explainability import parse_explain_block


def respond(entity_id: str, transcript: str, user_message: str) -> dict:
    system_prompt = (
        "You are Volta, a warm and direct AI energy advisor for South African homeowners. "
        "Use plain language. Focus on solar sizing, load-shedding backup planning, and "
        "basic SA electricity tariff context. Do not generate quotes or connect to installers.\n\n"
        f"Here is the complete history of your past conversations with this user:\n{transcript}\n\n"
        "Reply directly to the latest user message, taking the history into account."
    )
    messages = [{"role": "user", "content": user_message}]
    
    # Baseline B calls clean complete without tools
    reply = get_qwen_client().complete(system_prompt, messages, purpose="generation")
    explain = parse_explain_block(reply)
    user_reply = explain.user_facing_text
    
    return {
        "reply": user_reply,
        "memory_context_used": [{"observation": line} for line in transcript.splitlines() if line.strip()]
    }
