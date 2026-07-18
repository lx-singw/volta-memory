"""Pydantic models for the memory subsystem."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    PREFERENCE = "preference"
    FACT = "fact"
    OUTCOME = "outcome"
    CORRECTION = "correction"
    CONSOLIDATED = "consolidated"


class ConfidenceTier(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    BELOW_SURFACE = "below_surface"


class Memory(BaseModel):
    id: UUID | None = None
    entity_id: str
    memory_type: MemoryType
    observation: str
    evidence: dict[str, Any] | None = None
    base_confidence: float = Field(ge=0.0, le=1.0)
    reinforcement_count: int = 1
    cross_session_reinforcement_count: int = 1
    first_observed_at: datetime | None = None
    last_reinforced_at: datetime | None = None
    is_superseded: bool = False
    superseded_by_id: UUID | None = None
    source_session_id: UUID | None = None
    importance_score: float | None = None
    importance_reasoning: str | None = None
    stability_s0: float | None = None
    plausibility_flag: str = "plausible"
    consolidation_source_ids: list[UUID] | None = None
    source: str = "individual"


class MemoryDraft(BaseModel):
    memory_type: MemoryType
    observation: str
    base_confidence: float = 0.75
    evidence: dict[str, Any] | None = None
    importance_score: float | None = None
    importance_reasoning: str | None = None
    source: str = "individual"


class ScoredMemory(BaseModel):
    memory: Memory
    effective_confidence: float
    score: float
    tier: ConfidenceTier
    dialogue_action: str = "STATE"


class MemoryContext(BaseModel):
    entity_id: str
    packed_memories: list[ScoredMemory] = Field(default_factory=list)
    tokens_used: int = 0
    known_gaps: list[str] = Field(default_factory=list)
    fallback_chunks: list[str] = Field(default_factory=list)


class ImportanceResult(BaseModel):
    importance_score: float
    importance_reasoning: str


class PlausibilityResult(BaseModel):
    plausibility_flag: str
    reasoning: str
    capped_confidence: float | None = None


class ExplainTrace(BaseModel):
    referenced_memory_ids: list[UUID]
    primary_influence_memory_id: UUID | None = None
    confidence_tier_choice: str | None = None
    counterfactual: str | None = None
    user_facing_text: str


class ConsolidationResult(BaseModel):
    memories_consolidated: int
    consolidated_memory_id: UUID | None = None
    token_savings_estimate: int = 0


class Session(BaseModel):
    id: UUID
    entity_id: str
    persona: str = "volta"
    started_at: datetime
    ended_at: datetime | None = None
