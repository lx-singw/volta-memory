"""Thin wrapper around Qwen Cloud API — single provider contact point."""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator

import httpx

from app.chat.tokenizer import count_tokens
from app.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class QwenCall:
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    request_id: str | None
    cost_usd: float
    purpose: str

_qwen_calls_context: ContextVar[list[QwenCall] | None] = ContextVar("qwen_calls", default=None)
_current_system_context: ContextVar[str | None] = ContextVar("current_system", default=None)
_current_persona_context: ContextVar[str | None] = ContextVar("current_persona", default=None)
_current_replicate_context: ContextVar[int | None] = ContextVar("current_replicate", default=None)
_qwen_deadline_context: ContextVar[float | None] = ContextVar("qwen_deadline", default=None)


class QwenInvocationDeadlineExceeded(TimeoutError):
    """Raised before a Qwen call can exceed the request's configured budget."""


@contextmanager
def qwen_invocation_budget(seconds: float | None = None) -> Iterator[None]:
    """Share one monotonic deadline across every Qwen call in a request.

    Nested callers can only shorten the deadline.  This matters for end-session
    extraction, where extraction, scoring, and contradiction classification all
    use Qwen and must fit inside one Function Compute invocation.
    """
    settings = get_settings()
    requested_seconds = (
        settings.qwen_invocation_budget_seconds if seconds is None else seconds
    )
    now = time.monotonic()
    requested_deadline = now + max(0.0, float(requested_seconds))
    parent_deadline = _qwen_deadline_context.get()
    deadline = (
        min(parent_deadline, requested_deadline)
        if parent_deadline is not None
        else requested_deadline
    )
    token = _qwen_deadline_context.set(deadline)
    try:
        yield
    finally:
        _qwen_deadline_context.reset(token)


def _effective_deadline(settings) -> float:
    """Return the ambient request deadline or create a bounded local one."""
    return _qwen_deadline_context.get() or (
        time.monotonic() + max(0.0, float(settings.qwen_invocation_budget_seconds))
    )


def _attempt_timeout_seconds(settings, deadline: float) -> float:
    """Compute a per-attempt timeout without spending the request's tail room."""
    remaining = deadline - time.monotonic()
    safety_margin = 0.15
    if remaining <= safety_margin:
        raise QwenInvocationDeadlineExceeded(
            "Qwen invocation budget exhausted before another request could start."
        )
    configured = min(
        float(settings.qwen_timeout_seconds),
        float(settings.qwen_attempt_timeout_seconds),
    )
    return max(0.05, min(configured, remaining - safety_margin))


def _retry_delay_seconds(settings, attempt: int, deadline: float) -> float:
    """Bound exponential backoff by the remaining invocation budget."""
    desired = max(0.0, float(settings.qwen_retry_initial_delay_seconds)) * (2**attempt)
    remaining = deadline - time.monotonic() - 0.15
    return min(desired, max(0.0, remaining))

def set_eval_context(system: str | None, persona: str | None, replicate: int | None) -> None:
    _current_system_context.set(system)
    _current_persona_context.set(persona)
    _current_replicate_context.set(replicate)

def start_tracking_calls() -> None:
    _qwen_calls_context.set([])

def get_current_calls() -> list[QwenCall] | None:
    return _qwen_calls_context.get()

def stop_tracking_calls() -> list[QwenCall] | None:
    calls = _qwen_calls_context.get()
    _qwen_calls_context.set(None)
    return calls

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    if "embedding" in model.lower() or "embed" in model.lower():
        return (input_tokens / 1000.0) * 0.0007
    return (input_tokens / 1000.0) * 0.002 + (output_tokens / 1000.0) * 0.006

def _record_call(model: str, input_tokens: int, output_tokens: int, latency_ms: int, request_id: str | None, purpose: str) -> None:
    calls = _qwen_calls_context.get()
    cost = calculate_cost(model, input_tokens, output_tokens)
    
    sys_val = _current_system_context.get()
    if sys_val is not None:
        pers_val = _current_persona_context.get()
        rep_val = _current_replicate_context.get()
        print(f"    [Qwen Call] System {sys_val} | {pers_val} | Rep {rep_val} | "
              f"Purpose: {purpose} | Model: {model} | "
              f"Tokens: {input_tokens} in / {output_tokens} out | "
              f"Latency: {latency_ms}ms | Cost: ${cost:.6f}")

    # Function Compute forwards structured stdout/stderr to SLS.  This payload
    # intentionally contains operational metadata only—never prompts, replies,
    # source quotes, or workspace identifiers.
    logger.info(
        "volta_event=%s",
        json.dumps(
            {
                "event": "qwen_call",
                "model": model,
                "purpose": purpose,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "cost_usd": round(cost, 8),
                "request_id": request_id,
                "evaluation": (
                    {"system": sys_val, "persona": _current_persona_context.get(), "replicate": _current_replicate_context.get()}
                    if sys_val is not None
                    else None
                ),
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
    )
              
    if calls is not None:
        calls.append(QwenCall(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            request_id=request_id,
            cost_usd=cost,
            purpose=purpose
        ))


def _post_with_retry(
    client: httpx.Client,
    url: str,
    *,
    settings=None,
    deadline: float | None = None,
    **kwargs,
) -> httpx.Response:
    """Post with bounded retries rather than retrying beyond FC's request cap."""
    settings = settings or get_settings()
    deadline = deadline or _effective_deadline(settings)
    max_attempts = max(1, int(settings.qwen_max_retries))
    transient_errors = (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.TimeoutException,
        httpx.NetworkError,
    )

    for attempt in range(max_attempts):
        try:
            return client.post(
                url,
                timeout=_attempt_timeout_seconds(settings, deadline),
                **kwargs,
            )
        except transient_errors as exc:
            if attempt == max_attempts - 1:
                logger.error("HTTP post failed after %s bounded attempts: %s", max_attempts, exc)
                raise

            delay = _retry_delay_seconds(settings, attempt, deadline)
            if delay <= 0:
                raise QwenInvocationDeadlineExceeded(
                    "Qwen invocation budget exhausted while retrying a transient error."
                ) from exc
            logger.warning(
                "HTTP post transient error: %s. Retrying in %.2fs within invocation budget.",
                exc,
                delay,
            )
            logger.warning(
                "volta_event=%s",
                json.dumps(
                    {
                        "event": "qwen_retry",
                        "attempt": attempt + 1,
                        "delay_seconds": round(delay, 3),
                        "remaining_budget_seconds": round(max(0.0, deadline - time.monotonic()), 3),
                        "error_type": type(exc).__name__,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
            time.sleep(delay)

    # The loop always returns or raises, but keeping an explicit error makes
    # future edits fail safely instead of silently issuing an unbounded call.
    raise QwenInvocationDeadlineExceeded("Qwen request did not receive an attempt.")


class QwenClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def complete(self, system_prompt: str, messages: list[dict[str, str]], max_tokens: int = 512, purpose: str = "generation") -> str:
        settings = self.settings
        if not settings.qwen_api_key:
            logger.warning("QWEN_API_KEY not set — returning scaffold response")
            reply = (
                "I'm Volta, your energy advisor. (Scaffold mode — set QWEN_API_KEY for live inference.) "
                "Tell me more about your home and what you're hoping solar can solve."
            )
            input_toks = count_tokens(system_prompt + json.dumps(messages))
            output_toks = count_tokens(reply)
            _record_call(settings.qwen_model_chat, input_toks, output_toks, 50, None, purpose)
            return reply

        payload: dict[str, Any] = {
            "model": settings.qwen_model_chat,
            "input": {
                "messages": [{"role": "system", "content": system_prompt}, *messages],
            },
            "parameters": {"max_tokens": max_tokens, "result_format": "message"},
        }

        headers = {"Authorization": f"Bearer {settings.qwen_api_key}"}
        url = f"{settings.qwen_api_base_url.rstrip('/')}/services/aigc/text-generation/generation"

        deadline = _effective_deadline(settings)
        t0 = time.monotonic()
        with httpx.Client(timeout=settings.qwen_attempt_timeout_seconds) as client:
            response = _post_with_retry(
                client, url, json=payload, headers=headers, settings=settings, deadline=deadline
            )
            response.raise_for_status()
            data = response.json()
        latency = int((time.monotonic() - t0) * 1000)

        try:
            choice = data["output"]["choices"][0]
            reply = choice["message"]["content"]
            usage = data.get("usage", {})
            input_toks = usage.get("input_tokens", 0)
            output_toks = usage.get("output_tokens", 0)
            _record_call(
                settings.qwen_model_chat,
                input_toks,
                output_toks,
                latency,
                response.headers.get("x-request-id"),
                purpose
            )
            return reply
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Qwen response shape: {data}") from exc

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024, purpose: str = "extraction") -> dict[str, Any] | list[Any]:
        settings = self.settings
        if not settings.qwen_api_key:
            logger.warning("QWEN_API_KEY not set — returning empty dict scaffold")
            input_toks = count_tokens(system_prompt + user_prompt)
            _record_call(settings.qwen_model_extraction, input_toks, 0, 50, None, purpose)
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

        deadline = _effective_deadline(settings)
        t0 = time.monotonic()
        with httpx.Client(timeout=settings.qwen_attempt_timeout_seconds) as client:
            response = _post_with_retry(
                client, url, json=payload, headers=headers, settings=settings, deadline=deadline
            )
            response.raise_for_status()
            data = response.json()
        latency = int((time.monotonic() - t0) * 1000)

        try:
            content = data["output"]["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_toks = usage.get("input_tokens", 0)
            output_toks = usage.get("output_tokens", 0)
            _record_call(
                settings.qwen_model_extraction,
                input_toks,
                output_toks,
                latency,
                response.headers.get("x-request-id"),
                purpose
            )
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

    def embed(self, text: str, text_type: str = "document", purpose: str = "embedding") -> list[float]:
        settings = self.settings
        if not settings.qwen_api_key:
            logger.warning("QWEN_API_KEY not set — returning mock random embedding")
            seed = sum(ord(c) for c in text) % 997
            input_toks = count_tokens(text)
            _record_call(settings.qwen_model_embedding, input_toks, 0, 10, None, purpose)
            return [(seed + i) / settings.embedding_dimension for i in range(settings.embedding_dimension)]

        payload: dict[str, Any] = {
            "model": settings.qwen_model_embedding,
            "input": text,
            "dimensions": settings.embedding_dimension
        }

        base_url = settings.qwen_api_base_url.rstrip('/')
        if "api/v1" in base_url:
            base_url = base_url.replace("api/v1", "compatible-mode/v1")
        elif "compatible-mode/v1" not in base_url:
            base_url = f"{base_url}/compatible-mode/v1"
        url = f"{base_url}/embeddings"

        headers = {
            "Authorization": f"Bearer {settings.qwen_api_key}",
            "Content-Type": "application/json"
        }

        deadline = _effective_deadline(settings)
        t0 = time.monotonic()
        with httpx.Client(timeout=settings.qwen_attempt_timeout_seconds) as client:
            response = _post_with_retry(
                client, url, json=payload, headers=headers, settings=settings, deadline=deadline
            )
            response.raise_for_status()
            data = response.json()
        latency = int((time.monotonic() - t0) * 1000)

        try:
            usage = data.get("usage", {})
            input_toks = usage.get("total_tokens", usage.get("input_tokens", 0))
            _record_call(
                settings.qwen_model_embedding,
                input_toks,
                0,
                latency,
                response.headers.get("x-request-id"),
                purpose
            )
            return data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Qwen embedding response shape: {data}") from exc

    def complete_stream(self, system_prompt: str, messages: list[dict[str, str]], max_tokens: int = 512, purpose: str = "generation"):
        settings = self.settings
        if not settings.qwen_api_key:
            reply = "I'm Volta. (Scaffold stream mode.) Solar advice incoming..."
            input_toks = count_tokens(system_prompt + json.dumps(messages))
            output_toks = count_tokens(reply)
            _record_call(settings.qwen_model_chat, input_toks, output_toks, 50, None, purpose)
            yield reply
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

        t0 = time.monotonic()
        stream_usage = {}
        last_req_id = None
        last_len = 0
        deadline = _effective_deadline(settings)
        max_attempts = max(1, int(settings.qwen_max_retries))
        transient_errors = (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.TimeoutException,
            httpx.NetworkError,
        )

        for attempt in range(max_attempts):
            try:
                attempt_timeout = _attempt_timeout_seconds(settings, deadline)
                with httpx.Client(timeout=attempt_timeout) as client:
                    with client.stream(
                        "POST", url, json=payload, headers=headers, timeout=attempt_timeout
                    ) as response:
                        response.raise_for_status()
                        last_req_id = response.headers.get("x-request-id")
                        for line in response.iter_lines():
                            if line.startswith("data:"):
                                try:
                                    data = json.loads(line[5:])
                                    usage = data.get("usage", {})
                                    if usage:
                                        stream_usage = usage
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
                break
            except transient_errors as exc:
                if attempt == max_attempts - 1:
                    logger.error("HTTP stream failed after %s bounded attempts: %s", max_attempts, exc)
                    raise
                delay = _retry_delay_seconds(settings, attempt, deadline)
                if delay <= 0:
                    raise QwenInvocationDeadlineExceeded(
                        "Qwen stream invocation budget exhausted while retrying."
                    ) from exc
                logger.warning(
                    "HTTP stream transient error: %s. Retrying in %.2fs within invocation budget.",
                    exc,
                    delay,
                )
                time.sleep(delay)

        latency = int((time.monotonic() - t0) * 1000)
        input_toks = stream_usage.get("input_tokens", 0)
        output_toks = stream_usage.get("output_tokens", 0)
        _record_call(settings.qwen_model_chat, input_toks, output_toks, latency, last_req_id, purpose)

    def complete_with_tools(self, system_prompt: str, messages: list[dict[str, str]], entity_id: str, purpose: str = "tool_call") -> str:
        settings = self.settings
        if not settings.qwen_api_key:
            return self.complete(system_prompt, messages, purpose=purpose)

        # The chat-time tool surface is deliberately read-only.  Durable memory
        # writes must go through the verified, idempotent end-session lifecycle
        # so they always have source provenance and an audit event.
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
            }
        ]

        chat_history = [{"role": "system", "content": system_prompt}, *messages]

        deadline = _effective_deadline(settings)
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

            t0 = time.monotonic()
            with httpx.Client(timeout=settings.qwen_attempt_timeout_seconds) as client:
                response = _post_with_retry(
                    client, url, json=payload, headers=headers, settings=settings, deadline=deadline
                )
                response.raise_for_status()
                data = response.json()
            latency = int((time.monotonic() - t0) * 1000)

            choice = data["output"]["choices"][0]
            message = choice["message"]
            chat_history.append(message)

            usage = data.get("usage", {})
            input_toks = usage.get("input_tokens", 0)
            output_toks = usage.get("output_tokens", 0)
            _record_call(
                settings.qwen_model_chat,
                input_toks,
                output_toks,
                latency,
                response.headers.get("x-request-id"),
                purpose
            )

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
                    else:
                        result_str = (
                            f"Tool {func_name} is not available. Memory changes are saved only "
                            "when the user ends a consultation and the source-linked lifecycle verifies them."
                        )
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
