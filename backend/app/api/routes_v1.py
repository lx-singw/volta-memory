"""Authenticated, tenant-scoped public API for the Volta product UI."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from app.api.contracts import (
    EndSessionResponseDTO,
    ExcludedMemoryDTO,
    ExplainTraceDTO,
    MessageRequestDTO,
    MessageResponseDTO,
    RequestMagicLinkDTO,
    StartSessionResponseDTO,
    VerifyMagicLinkDTO,
    WorkspaceResponseDTO,
)
from app.api.serializers import build_change_dtos, build_memory_lookup, build_profile, build_timeline
from app.auth import (
    Workspace,
    clear_workspace_cookies,
    consume_magic_link,
    create_anonymous_workspace,
    create_magic_link,
    deliver_magic_link,
    get_workspace,
    require_csrf,
)
from app.chat.session import (
    SessionEndingInProgress,
    SessionExtractionUnavailable,
    end_session,
    send_message,
    start_session,
)
from app.config import get_settings
from app.db import get_connection


router = APIRouter(prefix="/v1", tags=["v1"])


def _workspace_response(workspace: Workspace) -> WorkspaceResponseDTO:
    return WorkspaceResponseDTO(
        entity_id=workspace.entity_id,
        entity_type=workspace.entity_type,
        csrf_token=workspace.csrf_token,
    )


def _require_writable(workspace: Workspace) -> None:
    if workspace.is_read_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This workspace is read-only.",
        )


def _require_session_owner(session_id: UUID, entity_id: str) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = %s AND entity_id = %s",
            (session_id, entity_id),
        ).fetchone()
    if not row:
        # Do not reveal whether a session exists in a different tenant.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")


def _serialize_message(entity_id: str, result: dict[str, Any]) -> MessageResponseDTO:
    lookup = build_memory_lookup(entity_id)
    context = []
    for item in result.get("memory_context_used") or []:
        memory_id = str(item.get("memory_id") or item.get("id") or "")
        if memory_id in lookup:
            context.append(lookup[memory_id])
    trace = result.get("explain_trace") or {}
    context_ids = {memory.id for memory in context}
    raw_referenced = [str(memory_id) for memory_id in trace.get("referenced_memory_ids") or []]
    used_ids = [memory_id for memory_id in (trace.get("used_memory_ids") or raw_referenced) if memory_id in context_ids]
    available_ids = [memory_id for memory_id in (trace.get("available_memory_ids") or []) if memory_id in context_ids and memory_id not in used_ids]
    if not trace.get("available_memory_ids"):
        available_ids = [memory.id for memory in context if memory.id not in used_ids]
    excluded = []
    for item in trace.get("excluded_memories") or []:
        memory_id = str(item.get("memory_id") or item.get("memoryId") or "")
        reason = str(item.get("reason") or "").strip()
        memory = lookup.get(memory_id)
        # Do not synthesize an exclusion from a memory's current status. A
        # missing trace entry is deliberately not rendered as "not used".
        if memory_id and reason and memory:
            excluded.append(ExcludedMemoryDTO(memory_id=memory_id, reason=reason, memory=memory))
    primary = str(trace.get("primary_influence_memory_id") or "")
    return MessageResponseDTO(
        reply=result["reply"],
        memory_context_used=context,
        tokens_used=result["tokens_used"],
        message_id=result.get("message_id"),
        known_gaps=result.get("known_gaps") or [],
        explain_trace=ExplainTraceDTO(
            referenced_memory_ids=used_ids,
            primary_influence_memory_id=primary if primary in used_ids else None,
            confidence_tier_choice=trace.get("confidence_tier_choice"),
            counterfactual=trace.get("counterfactual"),
            used_memory_ids=used_ids,
            available_memory_ids=available_ids,
            excluded_memories=excluded,
        ),
    )


@router.get("/me", response_model=WorkspaceResponseDTO)
def get_me(workspace: Workspace = Depends(get_workspace)) -> WorkspaceResponseDTO:
    return _workspace_response(workspace)


@router.post("/try", response_model=WorkspaceResponseDTO, status_code=status.HTTP_201_CREATED)
def create_try_workspace(
    request: Request,
    response: Response,
    workspace: Workspace = Depends(get_workspace),
) -> WorkspaceResponseDTO:
    """Start a fresh isolated sandbox after same-origin CSRF validation.

    The browser first bootstraps an opaque workspace through ``GET /v1/me``.
    Requiring that workspace's CSRF token here prevents another origin from
    replacing a visitor's cookie-bound tenant with a new anonymous workspace.
    """
    require_csrf(request, workspace)
    return _workspace_response(create_anonymous_workspace(response))


@router.get("/me/profile")
def get_my_profile(workspace: Workspace = Depends(get_workspace)) -> dict:
    return build_profile(workspace.entity_id).model_dump(by_alias=True)


@router.get("/me/memories")
def get_my_memories(workspace: Workspace = Depends(get_workspace)) -> dict:
    timeline = build_timeline(workspace.entity_id)
    return {
        "entityId": workspace.entity_id,
        "memories": [memory.model_dump(by_alias=True) for memory in timeline.memories],
        "relationships": [relationship.model_dump(by_alias=True) for relationship in timeline.relationships],
    }


@router.get("/me/memories/{memory_id}")
def get_my_memory(memory_id: str, workspace: Workspace = Depends(get_workspace)) -> dict:
    memory = build_memory_lookup(workspace.entity_id).get(memory_id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found.")
    return memory.model_dump(by_alias=True)


@router.get("/me/memory-timeline")
def get_my_timeline(workspace: Workspace = Depends(get_workspace)) -> dict:
    return build_timeline(workspace.entity_id).model_dump(by_alias=True)


@router.get("/showcase/profile")
def get_showcase_profile() -> dict:
    return build_profile(get_settings().public_showcase_entity_id).model_dump(by_alias=True)


@router.get("/showcase/memories")
def get_showcase_memories() -> dict:
    entity_id = get_settings().public_showcase_entity_id
    timeline = build_timeline(entity_id)
    return {
        "entityId": entity_id,
        "memories": [memory.model_dump(by_alias=True) for memory in timeline.memories],
        "relationships": [relationship.model_dump(by_alias=True) for relationship in timeline.relationships],
    }


@router.get("/showcase/memories/{memory_id}")
def get_showcase_memory(memory_id: str) -> dict:
    memory = build_memory_lookup(get_settings().public_showcase_entity_id).get(memory_id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found.")
    return memory.model_dump(by_alias=True)


@router.get("/showcase/timeline")
def get_showcase_timeline() -> dict:
    return build_timeline(get_settings().public_showcase_entity_id).model_dump(by_alias=True)


@router.post("/sessions", response_model=StartSessionResponseDTO, status_code=status.HTTP_201_CREATED)
def create_session(
    request: Request,
    persona: str = "volta",
    workspace: Workspace = Depends(get_workspace),
) -> StartSessionResponseDTO:
    require_csrf(request, workspace)
    _require_writable(workspace)
    session = start_session(workspace.entity_id, persona=persona)
    return StartSessionResponseDTO(
        session_id=str(session.id),
        entity_id=session.entity_id,
        persona=persona,
        started_at=session.started_at.isoformat(),
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageResponseDTO)
def post_message(
    session_id: UUID,
    body: MessageRequestDTO,
    request: Request,
    persona: str = "volta",
    workspace: Workspace = Depends(get_workspace),
) -> MessageResponseDTO:
    require_csrf(request, workspace)
    _require_writable(workspace)
    _require_session_owner(session_id, workspace.entity_id)
    try:
        result = send_message(session_id, body.message, persona=persona)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc
    return _serialize_message(workspace.entity_id, result)


@router.post("/sessions/{session_id}/end", response_model=EndSessionResponseDTO)
def post_end_session(
    session_id: UUID,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    workspace: Workspace = Depends(get_workspace),
) -> EndSessionResponseDTO:
    require_csrf(request, workspace)
    _require_writable(workspace)
    _require_session_owner(session_id, workspace.entity_id)
    try:
        result = end_session(session_id, idempotency_key=idempotency_key)
    except SessionEndingInProgress as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SessionExtractionUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from exc

    return EndSessionResponseDTO(
        session_id=result["session_id"],
        ended_at=result["ended_at"],
        memory_changes=build_change_dtos(workspace.entity_id, result.get("memory_changes") or []),
    )


@router.get("/messages/{message_id}/explain")
def get_message_explain(message_id: UUID, workspace: Workspace = Depends(get_workspace)) -> dict:
    with get_connection() as conn:
        trace = conn.execute(
            """
            SELECT trace.referenced_memory_ids, trace.primary_influence_memory_id,
                   trace.confidence_tier_choice, trace.counterfactual,
                   trace.available_memory_ids, trace.exclusion_trace, message.memory_context_used
            FROM explain_traces trace
            JOIN messages message ON message.id = trace.message_id
            JOIN conversations conversation ON conversation.id = message.conversation_id
            WHERE trace.message_id = %s AND conversation.entity_id = %s
            """,
            (message_id, workspace.entity_id),
        ).fetchone()
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Explain trace not found.")

    lookup = build_memory_lookup(workspace.entity_id)
    referenced_ids = [str(value) for value in (trace["referenced_memory_ids"] or [])]
    context_snapshot = trace["memory_context_used"] or []
    if isinstance(context_snapshot, str):
        try:
            context_snapshot = json.loads(context_snapshot)
        except json.JSONDecodeError:
            context_snapshot = []
    context_ids = {
        str(item.get("memory_id") or item.get("id") or "")
        for item in context_snapshot
        if isinstance(item, dict)
    }
    used = [lookup[memory_id] for memory_id in referenced_ids if memory_id in lookup and memory_id in context_ids]
    stored_available_ids = [str(value) for value in (trace["available_memory_ids"] or [])]
    available_ids = stored_available_ids or [memory_id for memory_id in context_ids if memory_id not in referenced_ids]
    available = [lookup[memory_id] for memory_id in available_ids if memory_id in lookup]
    exclusion_trace = trace["exclusion_trace"] or []
    if isinstance(exclusion_trace, str):
        try:
            exclusion_trace = json.loads(exclusion_trace)
        except json.JSONDecodeError:
            exclusion_trace = []
    not_used = []
    for item in exclusion_trace:
        if not isinstance(item, dict):
            continue
        memory_id = str(item.get("memory_id") or item.get("memoryId") or "")
        reason = str(item.get("reason") or "").strip()
        memory = lookup.get(memory_id)
        if memory_id and reason and memory:
            not_used.append({
                "memoryId": memory_id,
                "reason": reason,
                "memory": memory.model_dump(by_alias=True),
            })
    return {
        "messageId": str(message_id),
        "used": [memory.model_dump(by_alias=True) for memory in used],
        "available": [memory.model_dump(by_alias=True) for memory in available],
        "notUsed": not_used,
        "confidenceTierChoice": trace["confidence_tier_choice"],
        "counterfactual": trace["counterfactual"],
    }


@router.get("/me/export")
def export_workspace(workspace: Workspace = Depends(get_workspace)) -> dict:
    """Portable user-controlled copy of the tenant's durable memory state."""
    timeline = build_timeline(workspace.entity_id)
    profile = build_profile(workspace.entity_id)
    return {
        "entityId": workspace.entity_id,
        "entityType": workspace.entity_type,
        "profile": profile.model_dump(by_alias=True),
        "timeline": timeline.model_dump(by_alias=True),
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    request: Request,
    response: Response,
    workspace: Workspace = Depends(get_workspace),
) -> Response:
    require_csrf(request, workspace)
    _require_writable(workspace)
    with get_connection() as conn:
        user_email = None
        if workspace.user_id:
            user_row = conn.execute("SELECT email FROM users WHERE id = %s", (workspace.user_id,)).fetchone()
            user_email = user_row["email"] if user_row else None
        # A pending passwordless token must not resurrect a workspace that the
        # owner explicitly chose to erase.
        conn.execute("DELETE FROM auth_login_tokens WHERE entity_id = %s", (workspace.entity_id,))
        conn.execute("DELETE FROM memory_lifecycle_events WHERE entity_id = %s", (workspace.entity_id,))
        conn.execute(
            """
            DELETE FROM explain_traces WHERE message_id IN (
                SELECT message.id FROM messages message
                JOIN conversations conversation ON conversation.id = message.conversation_id
                WHERE conversation.entity_id = %s
            )
            """,
            (workspace.entity_id,),
        )
        conn.execute(
            "DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE entity_id = %s)",
            (workspace.entity_id,),
        )
        conn.execute("DELETE FROM transcript_chunks WHERE entity_id = %s", (workspace.entity_id,))
        conn.execute("DELETE FROM memories WHERE entity_id = %s", (workspace.entity_id,))
        conn.execute("DELETE FROM conversations WHERE entity_id = %s", (workspace.entity_id,))
        conn.execute("DELETE FROM entities WHERE id = %s", (workspace.entity_id,))
        if workspace.user_id:
            remaining = conn.execute(
                "SELECT 1 FROM entities WHERE owner_user_id = %s LIMIT 1",
                (workspace.user_id,),
            ).fetchone()
            if not remaining:
                # This is a permanent account deletion, not merely a memory
                # reset: revoke every server session and one-time link tied to
                # the identity before removing its email row.
                conn.execute("DELETE FROM auth_sessions WHERE user_id = %s", (workspace.user_id,))
                if user_email:
                    conn.execute("DELETE FROM auth_login_tokens WHERE email = %s", (user_email,))
                conn.execute("DELETE FROM users WHERE id = %s", (workspace.user_id,))
    clear_workspace_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/auth/request-link")
def request_magic_link(
    body: RequestMagicLinkDTO,
    request: Request,
    workspace: Workspace = Depends(get_workspace),
) -> dict:
    require_csrf(request, workspace)
    _require_writable(workspace)
    if "@" not in body.email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid email address is required.")
    _token, link = create_magic_link(body.email, workspace.entity_id)
    delivery = deliver_magic_link(body.email, link)
    # Development returns a link solely to make local passwordless testing possible.
    return {"status": "sent", **delivery}


@router.post("/auth/verify", response_model=WorkspaceResponseDTO)
def verify_magic_link(body: VerifyMagicLinkDTO, response: Response) -> WorkspaceResponseDTO:
    return _workspace_response(consume_magic_link(body.token, response))
