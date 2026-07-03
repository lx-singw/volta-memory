"""Thin wrapper around Qwen Cloud API — single provider contact point."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class QwenClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def complete(self, system_prompt: str, messages: list[dict[str, str]], max_tokens: int = 512) -> str:
        settings = self.settings
        if not settings.qwen_api_key:
            logger.warning("QWEN_API_KEY not set — returning scaffold response")
            return (
                "I'm Volta, your energy advisor. (Scaffold mode — set QWEN_API_KEY for live inference.) "
                "Tell me more about your home and what you're hoping solar can solve."
            )

        payload: dict[str, Any] = {
            "model": settings.qwen_model_chat,
            "input": {
                "messages": [{"role": "system", "content": system_prompt}, *messages],
            },
            "parameters": {"max_tokens": max_tokens, "result_format": "message"},
        }

        headers = {"Authorization": f"Bearer {settings.qwen_api_key}"}
        url = f"{settings.qwen_api_base_url.rstrip('/')}/services/aigc/text-generation/generation"

        with httpx.Client(timeout=settings.qwen_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        try:
            return data["output"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Qwen response shape: {data}") from exc


def get_qwen_client() -> QwenClient:
    return QwenClient()
