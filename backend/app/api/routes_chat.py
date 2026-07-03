"""Chat and session HTTP routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.chat.session import end_session, send_message, start_session
from app.config import get_settings

router = APIRouter(tags=["chat"])


class StartSessionResponse(BaseModel):
    session_id: str
    entity_id: str
    persona: str = "volta"
    started_at: str


class MessageRequest(BaseModel):
    message: str = Field(min_length=1)


class MessageResponse(BaseModel):
    reply: str
    memory_context_used: list[dict]
    tokens_used: int
    message_id: str | None = None


class EndSessionResponse(BaseModel):
    session_id: str
    ended_at: str
    memories_written: list[dict]


@router.post("/sessions", response_model=StartSessionResponse, status_code=201)
def create_session(
    persona: str = Query(default="volta"),
    entity_id: str | None = Query(default=None),
) -> StartSessionResponse:
    settings = get_settings()
    resolved_entity = entity_id or (
        "demo-consumer-2" if persona == "study_coach" else "demo-consumer-1"
    )
    session = start_session(resolved_entity, persona=persona)
    return StartSessionResponse(
        session_id=str(session.id),
        entity_id=session.entity_id,
        persona=persona,
        started_at=session.started_at.isoformat(),
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
def post_message(session_id: UUID, body: MessageRequest, persona: str = Query(default="volta")) -> MessageResponse:
    try:
        result = send_message(session_id, body.message, persona=persona)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MessageResponse(**result)


@router.post("/sessions/{session_id}/end", response_model=EndSessionResponse)
def post_end_session(session_id: UUID) -> EndSessionResponse:
    try:
        result = end_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EndSessionResponse(**result)
