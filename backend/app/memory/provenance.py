"""Verified, UI-safe provenance and lifecycle persistence for memories."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable
from uuid import UUID, uuid4

from app.memory.models import Memory, ProfileSlot


_SLOTS = {slot.value for slot in ProfileSlot}
_NUMBER_RE = re.compile(r"\b(?:r\s?\d|\d[\d,.]*\s?(?:rand|zar))", re.IGNORECASE)


def infer_profile_slot(observation: str, requested: str | None = None) -> ProfileSlot:
    """Return a bounded, server-owned profile slot for an observation."""
    if requested in _SLOTS:
        return ProfileSlot(requested)

    value = observation.lower()
    if "bill" in value or ("electricity" in value and _NUMBER_RE.search(value)):
        return ProfileSlot.MONTHLY_BILL
    if any(term in value for term in ("backup", "load-shedding", "load shedding", "lights on")):
        return ProfileSlot.BACKUP_PRIORITY
    if any(term in value for term in ("roof", "home", "house", "flat", "duplex", "property")):
        return ProfileSlot.ROOF_HOME
    if any(term in value for term in ("budget", "afford", "spend", "financ")):
        return ProfileSlot.BUDGET
    if any(term in value for term in ("tariff", "time-of-use", "time of use", "rate plan")):
        return ProfileSlot.TARIFF
    return ProfileSlot.NONE


def sanitize_provenance(
    evidence: dict[str, Any] | None,
    user_turns: Iterable[dict[str, Any]] | None,
    observation: str,
) -> tuple[dict[str, Any], ProfileSlot]:
    """Validate a model quote against the claimed *user* turn.

    A quote is proof only when it is an exact, non-empty substring of the user
    message identified by ``source_turn_index``. Invalid model output is removed
    instead of being shown as user evidence.
    """
    raw = dict(evidence or {})
    quote = raw.get("source_quote")
    quote = quote.strip() if isinstance(quote, str) else None
    turn_index = raw.get("source_turn_index")
    try:
        turn_index = int(turn_index) if turn_index is not None else None
    except (TypeError, ValueError):
        turn_index = None

    matched: dict[str, Any] | None = None
    if quote and turn_index and user_turns:
        for turn in user_turns:
            if turn.get("turn_index") == turn_index and quote in str(turn.get("content") or ""):
                matched = turn
                break

    profile_slot = infer_profile_slot(observation, raw.get("profile_slot"))
    return {
        "source_quote": quote if matched else None,
        "source_turn_index": turn_index if matched else None,
        "source_message_id": str(matched["message_id"]) if matched and matched.get("message_id") else None,
        "source_verified": bool(matched),
        "is_constraint": bool(raw.get("is_constraint", False)),
        "profile_slot": profile_slot.value,
    }, profile_slot


def persist_provenance(
    connection: Any,
    memory: Memory,
    source_session_id: UUID | None = None,
) -> None:
    """Persist the already-sanitized provenance carried by a memory draft."""
    evidence = memory.evidence or {}
    message_id = evidence.get("source_message_id")
    try:
        message_id = UUID(str(message_id)) if message_id else None
    except (TypeError, ValueError):
        message_id = None

    connection.execute(
        """
        INSERT INTO memory_provenance (
            id, memory_id, original_user_message_id, source_session_id,
            source_turn_index, source_quote, source_verified, is_constraint
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (memory_id) DO UPDATE SET
            original_user_message_id = EXCLUDED.original_user_message_id,
            source_session_id = EXCLUDED.source_session_id,
            source_turn_index = EXCLUDED.source_turn_index,
            source_quote = EXCLUDED.source_quote,
            source_verified = EXCLUDED.source_verified,
            is_constraint = EXCLUDED.is_constraint
        """,
        (
            uuid4(),
            memory.id,
            message_id,
            source_session_id or memory.source_session_id,
            evidence.get("source_turn_index"),
            evidence.get("source_quote"),
            bool(evidence.get("source_verified", False)),
            evidence.get("is_constraint"),
        ),
    )


def persist_relation(
    connection: Any,
    source_memory_id: UUID,
    target_memory_id: UUID,
    relation_type: str,
    source_session_id: UUID | None,
) -> None:
    connection.execute(
        """
        INSERT INTO memory_relations (
            id, source_memory_id, target_memory_id, relation_type, source_session_id
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (source_memory_id, target_memory_id, relation_type) DO NOTHING
        """,
        (uuid4(), source_memory_id, target_memory_id, relation_type, source_session_id),
    )


def persist_lifecycle_event(
    connection: Any,
    *,
    entity_id: str,
    session_id: UUID,
    action: str,
    before_memory_id: UUID | None,
    after_memory_id: UUID | None,
    display_payload: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO memory_lifecycle_events (
            id, entity_id, session_id, action, before_memory_id, after_memory_id, display_payload
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            uuid4(),
            entity_id,
            session_id,
            action,
            before_memory_id,
            after_memory_id,
            json.dumps(display_payload),
        ),
    )
