"""Chat and session HTTP routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.chat.session import SessionEndingInProgress, SessionExtractionUnavailable, end_session, send_message, start_session
from app.config import get_settings

router = APIRouter(tags=["chat"])


def _reject_legacy_mutation_in_production() -> None:
    if get_settings().app_env == "production":
        raise HTTPException(
            status_code=410,
            detail="Legacy mutations are disabled in production. Use /v1 routes.",
        )


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
    known_gaps: list[str] = Field(default_factory=list)
    explain_trace: dict | None = None


class EndSessionResponse(BaseModel):
    session_id: str
    ended_at: str
    memories_written: list[dict]
    memory_changes: list[dict] = Field(default_factory=list)
    extraction_status: str = "completed"


@router.post("/sessions", response_model=StartSessionResponse, status_code=201)
def create_session(
    persona: str = Query(default="volta"),
    entity_id: str | None = Query(default=None),
) -> StartSessionResponse:
    settings = get_settings()
    if settings.app_env == "production":
        raise HTTPException(
            status_code=410,
            detail="Legacy sessions are disabled in production. Use /v1/sessions.",
        )
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


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: UUID, 
    body: MessageRequest, 
    persona: str = Query(default="volta"),
    stream: bool = Query(default=False)
):
    _reject_legacy_mutation_in_production()
    import json
    from fastapi.responses import StreamingResponse
    from app.chat.session import send_message_stream
    
    if stream:
        def event_generator():
            try:
                for chunk in send_message_stream(session_id, body.message, persona=persona):
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
                
                from app.db import get_connection
                with get_connection() as conn:
                    last_msg = conn.execute(
                        """
                        SELECT id, memory_context_used FROM messages
                        WHERE conversation_id = %s AND role = 'assistant'
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (session_id,)
                    ).fetchone()
                    if last_msg:
                        trace_row = conn.execute(
                            """
                            SELECT referenced_memory_ids, primary_influence_memory_id, confidence_tier_choice, counterfactual
                            FROM explain_traces WHERE message_id = %s
                            """,
                            (last_msg["id"],)
                        ).fetchone()
                        
                        trace_dict = None
                        if trace_row:
                            trace_dict = {
                                "referenced_memory_ids": [str(x) for x in trace_row["referenced_memory_ids"]],
                                "primary_influence_memory_id": str(trace_row["primary_influence_memory_id"]) if trace_row["primary_influence_memory_id"] else None,
                                "confidence_tier_choice": trace_row["confidence_tier_choice"],
                                "counterfactual": trace_row["counterfactual"]
                            }
                        
                        ctx_data = last_msg['memory_context_used']
                        if isinstance(ctx_data, str):
                            ctx_data = json.loads(ctx_data)
                        
                        chunk_data = {
                            'memory_context_used': ctx_data,
                            'explain_trace': trace_dict
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
            except ValueError as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    try:
        result = send_message(session_id, body.message, persona=persona)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MessageResponse(**result)


@router.post("/sessions/{session_id}/end", response_model=EndSessionResponse)
def post_end_session(
    session_id: UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> EndSessionResponse:
    _reject_legacy_mutation_in_production()
    try:
        result = end_session(session_id, idempotency_key=idempotency_key)
    except SessionEndingInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SessionExtractionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EndSessionResponse(**result)
