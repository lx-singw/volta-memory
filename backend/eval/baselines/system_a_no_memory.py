"""Baseline A — no memory across sessions."""

from __future__ import annotations

from app.chat.qwen_client import get_qwen_client
from app.memory.explainability import parse_explain_block


def respond(entity_id: str, _transcript: str, user_message: str) -> dict:
    system_prompt = (
        "You are Volta, a warm and direct AI energy advisor for South African homeowners. "
        "Use plain language. Focus on solar sizing, load-shedding backup planning, and "
        "basic SA electricity tariff context. Do not generate quotes or connect to installers. "
        "You have no memory of any previous conversations with this user. "
        "Reply directly to the user's message."
    )
    messages = [{"role": "user", "content": user_message}]
    
    # Baseline A calls clean, parameter-less complete without tools to guarantee zero memory access
    reply = get_qwen_client().complete(system_prompt, messages, purpose="generation")
    explain = parse_explain_block(reply)
    user_reply = explain.user_facing_text
    
    return {
        "reply": user_reply,
        "memory_context_used": []
    }
