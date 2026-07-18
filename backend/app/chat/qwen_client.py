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

    def complete_stream(self, system_prompt: str, messages: list[dict[str, str]], max_tokens: int = 512):
        settings = self.settings
        if not settings.qwen_api_key:
            yield "I'm Volta. (Scaffold stream mode.) Solar advice incoming..."
            return

        payload: dict[str, Any] = {
            "model": settings.qwen_model_chat,
            "input": {
                "messages": [{"role": "system", "content": system_prompt}, *messages],
            },
            "parameters": {
                "max_tokens": max_tokens, 
                "result_format": "message",
                "incremental_output": True
            },
        }

        headers = {
            "Authorization": f"Bearer {settings.qwen_api_key}",
            "X-DashScope-SSE": "enable"
        }
        url = f"{settings.qwen_api_base_url.rstrip('/')}/services/aigc/text-generation/generation"

        last_len = 0
        with httpx.Client(timeout=settings.qwen_timeout_seconds) as client:
            with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:])
                            content = data["output"]["choices"][0]["message"]["content"]
                            if content:
                                if len(content) > last_len:
                                    delta = content[last_len:]
                                    last_len = len(content)
                                    yield delta
                                else:
                                    yield content
                        except Exception:
                            continue

    def complete_with_tools(self, system_prompt: str, messages: list[dict[str, str]], entity_id: str) -> str:
        settings = self.settings
        if not settings.qwen_api_key:
            return self.complete(system_prompt, messages)

        # Define tools schema
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_memory_context",
                    "description": "Recall persistent user memories or past conversation segments relevant to a query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_memory",
                    "description": "Save a new observation/preference to user's persistent memory store.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "observation": {"type": "string", "description": "User observation text"},
                            "memory_type": {"type": "string", "enum": ["preference", "fact", "outcome"]}
                        },
                        "required": ["observation", "memory_type"]
                    }
                }
            }
        ]

        chat_history = [{"role": "system", "content": system_prompt}, *messages]

        for _ in range(3):
            payload = {
                "model": settings.qwen_model_chat,
                "input": {
                    "messages": chat_history,
                },
                "parameters": {
                    "result_format": "message",
                },
                "tools": tools
            }

            headers = {"Authorization": f"Bearer {settings.qwen_api_key}"}
            url = f"{settings.qwen_api_base_url.rstrip('/')}/services/aigc/text-generation/generation"

            with httpx.Client(timeout=settings.qwen_timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            choice = data["output"]["choices"][0]
            message = choice["message"]
            chat_history.append(message)

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                return message.get("content") or ""

            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                func_args = json.loads(tool_call["function"]["arguments"])
                tool_call_id = tool_call.get("id")

                # Execute matching tool
                try:
                    if func_name == "get_memory_context":
                        from app.memory.store import list_memories
                        from app.memory.retrieval import build_memory_context
                        mems = list_memories(entity_id, include_superseded=False)
                        context = build_memory_context(entity_id, mems, query_context=func_args.get("query", ""))
                        result_str = "\n".join(f"- {m.memory.observation}" for m in context.packed_memories) or "No memories found."
                    elif func_name == "write_memory":
                        from app.memory.store import write_memory
                        from app.memory.models import MemoryType
                        mem = write_memory(
                            entity_id=entity_id,
                            memory_type=MemoryType(func_args.get("memory_type")),
                            observation=func_args.get("observation"),
                            confidence=0.85
                        )
                        result_str = f"Successfully wrote memory: {mem.observation}"
                    else:
                        result_str = f"Tool {func_name} not supported."
                except Exception as e:
                    result_str = f"Error running tool: {e}"

                tool_response = {
                    "role": "tool",
                    "name": func_name,
                    "content": result_str
                }
                if tool_call_id:
                    tool_response["tool_call_id"] = tool_call_id
                chat_history.append(tool_response)

        return chat_history[-1].get("content") or ""


def get_qwen_client() -> QwenClient:
    return QwenClient()

