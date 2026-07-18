"""Thin wrapper around Qwen Cloud API — single provider contact point."""

from __future__ import annotations

import json
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

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> dict[str, Any] | list[Any]:
        settings = self.settings
        if not settings.qwen_api_key:
            logger.warning("QWEN_API_KEY not set — returning empty dict scaffold")
            return {}

        payload: dict[str, Any] = {
            "model": settings.qwen_model_extraction,
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
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
            content = data["output"]["choices"][0]["message"]["content"]
            content_clean = content.strip()
            if content_clean.startswith("```json"):
                content_clean = content_clean[7:]
            if content_clean.endswith("```"):
                content_clean = content_clean[:-3]
            content_clean = content_clean.strip()
            return json.loads(content_clean)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.error(f"Failed to parse Qwen JSON response: {data if 'data' in locals() else exc}")
            raise RuntimeError(f"Unexpected Qwen response or invalid JSON: {content if 'content' in locals() else data}") from exc

    def embed(self, text: str, text_type: str = "document") -> list[float]:
        settings = self.settings
        if not settings.qwen_api_key:
            logger.warning("QWEN_API_KEY not set — returning mock random embedding")
            seed = sum(ord(c) for c in text) % 997
            return [(seed + i) / settings.embedding_dimension for i in range(settings.embedding_dimension)]

        payload: dict[str, Any] = {
            "model": settings.qwen_model_embedding,
            "input": {
                "texts": [text],
            },
            "parameters": {
                "text_type": text_type
            }
        }

        headers = {"Authorization": f"Bearer {settings.qwen_api_key}"}
        url = f"{settings.qwen_api_base_url.rstrip('/')}/services/embeddings/text-embedding"

        with httpx.Client(timeout=settings.qwen_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        try:
            return data["output"]["embeddings"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Qwen embedding response shape: {data}") from exc


def get_qwen_client() -> QwenClient:
    return QwenClient()

