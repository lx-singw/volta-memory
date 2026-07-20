"""Database-to-public DTO serializers. Raw evidence JSON never crosses /v1."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.api.contracts import (
    MemoryChangeDTO,
    MemoryDTO,
    MemoryRelationDTO,
    ProfileFactDTO,
    ProfileResponseDTO,
    ProvenanceDTO,
    PublicMemorySnapshotDTO,
    RelatedMemoryDTO,
    TimelineResponseDTO,
)
from app.config import get_settings
from app.db import get_connection
from app.memory.decay import apply_decay
from app.memory.models import Memory
from app.memory.store import list_memories


def _load_metadata(entity_id: str) -> tuple[dict[str, dict], list[dict]]:
    with get_connection() as conn:
        provenance_rows = conn.execute(
            """
            SELECT provenance.memory_id, provenance.source_quote, provenance.source_turn_index,
                   provenance.source_verified, provenance.is_constraint
            FROM memory_provenance provenance
            JOIN memories memory ON memory.id = provenance.memory_id
            WHERE memory.entity_id = %s
            """,
            (entity_id,),
        ).fetchall()
        relation_rows = conn.execute(
            """
            SELECT relation.source_memory_id, relation.target_memory_id, relation.relation_type, relation.created_at
            FROM memory_relations relation
            JOIN memories source_memory ON source_memory.id = relation.source_memory_id
            WHERE source_memory.entity_id = %s
            """,
            (entity_id,),
        ).fetchall()
    return ({str(row["memory_id"]): dict(row) for row in provenance_rows}, [dict(row) for row in relation_rows])


def _memory_status(memory: Memory, effective_confidence: float) -> str:
    if memory.is_superseded:
        return "retained"
    if effective_confidence < get_settings().confidence_surface_threshold:
        return "excluded" if memory.profile_slot.value == "none" else "needs_reconfirmation"
    return "eligible"


def _related(memory: Memory, provenance: dict | None) -> RelatedMemoryDTO:
    return RelatedMemoryDTO(
        id=str(memory.id),
        observation=memory.observation,
        source_quote=provenance.get("source_quote") if provenance and provenance.get("source_verified") else None,
        source_turn_index=provenance.get("source_turn_index") if provenance and provenance.get("source_verified") else None,
    )


def build_memory_dtos(entity_id: str) -> list[MemoryDTO]:
    memories = list_memories(entity_id, include_superseded=True)
    provenance_by_id, relations = _load_metadata(entity_id)
    memory_by_id = {str(memory.id): memory for memory in memories}
    prior_by_target: dict[str, str] = {}
    replacement_by_source: dict[str, str] = {}
    for relation in relations:
        if relation["relation_type"] == "supersedes":
            source_id = str(relation["source_memory_id"])
            target_id = str(relation["target_memory_id"])
            prior_by_target[target_id] = source_id
            replacement_by_source[source_id] = target_id

    payload: list[MemoryDTO] = []
    for memory in memories:
        memory_id = str(memory.id)
        provenance = provenance_by_id.get(memory_id)
        prior = memory_by_id.get(prior_by_target.get(memory_id, ""))
        replacement = memory_by_id.get(replacement_by_source.get(memory_id, ""))
        effective = round(apply_decay(memory), 4)
        payload.append(
            MemoryDTO(
                id=memory_id,
                observation=memory.observation,
                memory_type=memory.memory_type.value,
                profile_slot=memory.profile_slot.value,
                confidence=effective,
                importance=memory.importance_score,
                status=_memory_status(memory, effective),
                last_confirmed_at=memory.last_reinforced_at.isoformat() if memory.last_reinforced_at else None,
                provenance=ProvenanceDTO(
                    source_quote=provenance.get("source_quote") if provenance and provenance.get("source_verified") else None,
                    source_turn_index=provenance.get("source_turn_index") if provenance and provenance.get("source_verified") else None,
                    source_verified=bool(provenance and provenance.get("source_verified")),
                    is_constraint=provenance.get("is_constraint") if provenance else None,
                    prior=_related(prior, provenance_by_id.get(str(prior.id))) if prior else None,
                    replaced_by=_related(replacement, provenance_by_id.get(str(replacement.id))) if replacement else None,
                ),
                is_superseded=memory.is_superseded,
                superseded_by_id=str(memory.superseded_by_id) if memory.superseded_by_id else None,
                base_confidence=memory.base_confidence,
                effective_confidence=effective,
                reinforcement_count=memory.reinforcement_count,
            )
        )
    return payload


def build_memory_lookup(entity_id: str) -> dict[str, MemoryDTO]:
    return {memory.id: memory for memory in build_memory_dtos(entity_id)}


def build_timeline(entity_id: str) -> TimelineResponseDTO:
    memories = build_memory_dtos(entity_id)
    memories.sort(key=lambda memory: memory.last_confirmed_at or "")
    _provenance, relations = _load_metadata(entity_id)
    return TimelineResponseDTO(
        entity_id=entity_id,
        memories=memories,
        relationships=[
            MemoryRelationDTO(
                source_memory_id=str(relation["source_memory_id"]),
                target_memory_id=str(relation["target_memory_id"]),
                relation_type=relation["relation_type"],
                created_at=relation["created_at"].isoformat() if relation.get("created_at") else None,
            )
            for relation in relations
        ],
        total=len(memories),
        current=sum(1 for memory in memories if memory.status == "eligible"),
        retained=sum(1 for memory in memories if memory.status == "retained"),
    )


_PROFILE_LABELS = {
    "monthly_bill": "Electricity bill",
    "backup_priority": "Backup priority",
    "roof_home": "Roof & home",
    "budget": "Budget",
    "tariff": "Tariff",
    "none": "Other context",
}


def _profile_value(memory: MemoryDTO) -> str:
    # Keep the API authoritative without making a fragile frontend infer values.
    if memory.profile_slot == "monthly_bill":
        import re

        match = re.search(r"R\s?[\d,]+(?:\.\d+)?", memory.observation, re.IGNORECASE)
        if match:
            return match.group(0).replace(" ", "")
    return memory.observation


def build_profile(entity_id: str) -> ProfileResponseDTO:
    memories = build_memory_dtos(entity_id)
    candidates: dict[str, MemoryDTO] = {}
    for memory in memories:
        if memory.profile_slot == "none" or memory.status not in {"eligible", "needs_reconfirmation"}:
            continue
        existing = candidates.get(memory.profile_slot)
        if existing is None or (memory.last_confirmed_at or "") > (existing.last_confirmed_at or ""):
            candidates[memory.profile_slot] = memory

    facts = [
        ProfileFactDTO(
            profile_slot=memory.profile_slot,
            label=_PROFILE_LABELS[memory.profile_slot],
            display_value=_profile_value(memory),
            status=memory.status,
            source_memory_id=memory.id,
            confidence=memory.confidence,
            last_confirmed_at=memory.last_confirmed_at,
            source_verified=memory.provenance.source_verified,
        )
        for memory in candidates.values()
    ]
    facts.sort(key=lambda fact: fact.profile_slot)
    return ProfileResponseDTO(
        entity_id=entity_id,
        facts=facts,
        current_fact_count=sum(1 for memory in memories if memory.status == "eligible"),
        retained_fact_count=sum(1 for memory in memories if memory.status == "retained"),
        last_confirmed_at=max((fact.last_confirmed_at for fact in facts if fact.last_confirmed_at), default=None),
    )


def build_change_dtos(entity_id: str, changes: list[dict[str, Any]]) -> list[MemoryChangeDTO]:
    lookup = build_memory_lookup(entity_id)

    def snapshot(raw: dict | None) -> PublicMemorySnapshotDTO | None:
        if not raw:
            return None
        memory = lookup.get(str(raw.get("id")))
        if memory:
            return PublicMemorySnapshotDTO(
                id=memory.id,
                observation=memory.observation,
                memory_type=memory.memory_type,
                profile_slot=memory.profile_slot,
                confidence=memory.confidence,
                provenance=memory.provenance,
            )
        return PublicMemorySnapshotDTO(
            id=str(raw.get("id")),
            observation=str(raw.get("observation", "")),
            memory_type=str(raw.get("memory_type", "fact")),
            profile_slot=str(raw.get("profile_slot", "none")),
            confidence=float(raw.get("confidence", 0)),
        )

    result: list[MemoryChangeDTO] = []
    for change in changes:
        after = snapshot(change.get("after"))
        provenance = after.provenance if after else None
        result.append(
            MemoryChangeDTO(
                action=change["operation"],
                before=snapshot(change.get("before")),
                after=after,
                source_quote=provenance.source_quote if provenance else None,
                source_turn_index=provenance.source_turn_index if provenance else None,
                source_verified=provenance.source_verified if provenance else False,
            )
        )
    return result
