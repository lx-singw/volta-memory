"""Camel-case public API contracts shared by all /v1 routes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def camel_case(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=camel_case, populate_by_name=True)


class RelatedMemoryDTO(ApiModel):
    id: str
    observation: str
    source_quote: str | None = None
    source_turn_index: int | None = None


class ProvenanceDTO(ApiModel):
    source_quote: str | None = None
    source_turn_index: int | None = None
    source_verified: bool = False
    is_constraint: bool | None = None
    prior: RelatedMemoryDTO | None = None
    replaced_by: RelatedMemoryDTO | None = None


class MemoryDTO(ApiModel):
    id: str
    observation: str
    memory_type: Literal["preference", "fact", "outcome", "correction", "consolidated"]
    profile_slot: Literal["monthly_bill", "backup_priority", "roof_home", "budget", "tariff", "none"]
    confidence: float
    importance: float | None = None
    status: Literal["eligible", "needs_reconfirmation", "retained", "excluded"]
    last_confirmed_at: str | None = None
    provenance: ProvenanceDTO
    is_superseded: bool = False
    superseded_by_id: str | None = None
    base_confidence: float | None = None
    effective_confidence: float | None = None
    reinforcement_count: int = 1


class ProfileFactDTO(ApiModel):
    profile_slot: Literal["monthly_bill", "backup_priority", "roof_home", "budget", "tariff", "none"]
    label: str
    display_value: str
    status: Literal["eligible", "needs_reconfirmation", "retained", "excluded"]
    source_memory_id: str
    confidence: float
    last_confirmed_at: str | None = None
    source_verified: bool = False


class ProfileResponseDTO(ApiModel):
    entity_id: str
    facts: list[ProfileFactDTO] = Field(default_factory=list)
    current_fact_count: int = 0
    retained_fact_count: int = 0
    last_confirmed_at: str | None = None


class MemoryRelationDTO(ApiModel):
    source_memory_id: str
    target_memory_id: str
    relation_type: Literal["supersedes", "reinforces", "consolidates"]
    created_at: str | None = None


class TimelineResponseDTO(ApiModel):
    entity_id: str
    memories: list[MemoryDTO]
    relationships: list[MemoryRelationDTO] = Field(default_factory=list)
    total: int
    current: int
    retained: int


class PublicMemorySnapshotDTO(ApiModel):
    id: str
    observation: str
    memory_type: str
    profile_slot: str
    confidence: float
    provenance: ProvenanceDTO | None = None


class MemoryChangeDTO(ApiModel):
    action: Literal["created", "reinforced", "corrected"]
    before: PublicMemorySnapshotDTO | None = None
    after: PublicMemorySnapshotDTO | None = None
    source_quote: str | None = None
    source_turn_index: int | None = None
    source_verified: bool = False


class EndSessionResponseDTO(ApiModel):
    session_id: str
    ended_at: str
    memory_changes: list[MemoryChangeDTO] = Field(default_factory=list)
    extraction_status: Literal["completed"] = "completed"


class StartSessionResponseDTO(ApiModel):
    session_id: str
    entity_id: str
    persona: str
    started_at: str


class ExcludedMemoryDTO(ApiModel):
    """A retrieval exclusion tied to one durable public memory record."""

    memory_id: str
    reason: str
    memory: MemoryDTO | None = None


class ExplainTraceDTO(ApiModel):
    referenced_memory_ids: list[str] = Field(default_factory=list)
    primary_influence_memory_id: str | None = None
    confidence_tier_choice: str | None = None
    counterfactual: str | None = None
    used_memory_ids: list[str] = Field(default_factory=list)
    available_memory_ids: list[str] = Field(default_factory=list)
    excluded_memories: list[ExcludedMemoryDTO] = Field(default_factory=list)


class MessageResponseDTO(ApiModel):
    reply: str
    memory_context_used: list[MemoryDTO] = Field(default_factory=list)
    tokens_used: int
    message_id: str | None = None
    known_gaps: list[str] = Field(default_factory=list)
    explain_trace: ExplainTraceDTO | None = None


class MessageRequestDTO(ApiModel):
    message: str = Field(min_length=1, max_length=12_000)


class WorkspaceResponseDTO(ApiModel):
    entity_id: str
    entity_type: Literal["showcase", "anonymous", "user"]
    csrf_token: str


class RequestMagicLinkDTO(ApiModel):
    email: str = Field(min_length=3, max_length=320)


class VerifyMagicLinkDTO(ApiModel):
    token: str = Field(min_length=20, max_length=512)
