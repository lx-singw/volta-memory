"""Application configuration — single source of truth for environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Qwen Cloud
    qwen_api_key: str = Field(default="", alias="QWEN_API_KEY")
    qwen_api_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/api/v1", alias="QWEN_API_BASE_URL"
    )
    qwen_model_chat: str = Field(default="qwen-max", alias="QWEN_MODEL_CHAT")
    qwen_model_extraction: str = Field(default="qwen-plus", alias="QWEN_MODEL_EXTRACTION")
    qwen_model_embedding: str = Field(default="text-embedding-v2", alias="QWEN_MODEL_EMBEDDING")
    qwen_max_retries: int = Field(default=3, alias="QWEN_MAX_RETRIES")
    qwen_timeout_seconds: int = Field(default=30, alias="QWEN_TIMEOUT_SECONDS")

    # Database
    database_url: str = Field(
        default="postgresql://volta:changeme@localhost:5432/volta_memory", alias="DATABASE_URL"
    )
    database_pool_min_size: int = Field(default=2, alias="DATABASE_POOL_MIN_SIZE")
    database_pool_max_size: int = Field(default=10, alias="DATABASE_POOL_MAX_SIZE")
    database_ssl_mode: str = Field(default="disable", alias="DATABASE_SSL_MODE")

    # Memory tuning
    max_memory_tokens: int = Field(default=800, alias="MAX_MEMORY_TOKENS")
    fallback_budget_tokens: int = Field(default=150, alias="FALLBACK_BUDGET_TOKENS")
    decay_lambda_preference: float = Field(default=0.02, alias="DECAY_LAMBDA_PREFERENCE")
    decay_lambda_fact: float = Field(default=0.01, alias="DECAY_LAMBDA_FACT")
    decay_lambda_outcome: float = Field(default=0.05, alias="DECAY_LAMBDA_OUTCOME")
    decay_lambda_correction: float = Field(default=0.02, alias="DECAY_LAMBDA_CORRECTION")
    correction_floor_days: int = Field(default=14, alias="CORRECTION_FLOOR_DAYS")
    confidence_surface_threshold: float = Field(default=0.5, alias="CONFIDENCE_SURFACE_THRESHOLD")
    confidence_high_tier_threshold: float = Field(default=0.85, alias="CONFIDENCE_HIGH_TIER_THRESHOLD")
    stability_growth_base: float = Field(default=1.5, alias="STABILITY_GROWTH_BASE")
    stability_growth_importance_range: float = Field(
        default=1.0, alias="STABILITY_GROWTH_IMPORTANCE_RANGE"
    )
    s0_default: float = Field(default=1.0, alias="S0_DEFAULT")

    # Hybrid retrieval
    hybrid_retrieval_enabled: bool = Field(default=True, alias="HYBRID_RETRIEVAL_ENABLED")
    hybrid_similarity_threshold: float = Field(default=0.6, alias="HYBRID_SIMILARITY_THRESHOLD")
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")
    vector_index_backend: str = Field(default="pgvector", alias="VECTOR_INDEX_BACKEND")

    # Plausibility
    plausibility_check_enabled: bool = Field(default=True, alias="PLAUSIBILITY_CHECK_ENABLED")
    plausibility_confidence_cap: float = Field(default=0.3, alias="PLAUSIBILITY_CONFIDENCE_CAP")
    domain_constraints_file: str = Field(
        default="config/domain_constraints.yaml", alias="DOMAIN_CONSTRAINTS_FILE"
    )

    # Consolidation
    consolidation_enabled: bool = Field(default=True, alias="CONSOLIDATION_ENABLED")
    consolidation_session_interval: int = Field(default=5, alias="CONSOLIDATION_SESSION_INTERVAL")
    consolidation_staleness_days: int = Field(default=21, alias="CONSOLIDATION_STALENESS_DAYS")

    # Explainability
    explainability_enabled: bool = Field(default=True, alias="EXPLAINABILITY_ENABLED")
    explain_block_max_tokens: int = Field(default=120, alias="EXPLAIN_BLOCK_MAX_TOKENS")

    # Eval harness
    eval_persona_dir: str = Field(default="eval/personas/", alias="EVAL_PERSONA_DIR")
    eval_results_output: str = Field(default="BENCHMARKS.md", alias="EVAL_RESULTS_OUTPUT")
    eval_system_variants: str = Field(default="A,B,C,D", alias="EVAL_SYSTEM_VARIANTS")
    eval_run_adversarial: bool = Field(default=True, alias="EVAL_RUN_ADVERSARIAL")
    importance_validation_dataset: str = Field(
        default="eval/importance_validation_labels.json",
        alias="IMPORTANCE_VALIDATION_DATASET",
    )

    # App / server
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", alias="APP_ENV"
    )
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    cors_allowed_origins: str = Field(default="http://localhost:3000", alias="CORS_ALLOWED_ORIGINS")
    session_idle_timeout_minutes: int = Field(default=30, alias="SESSION_IDLE_TIMEOUT_MINUTES")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_redact_api_keys: bool = Field(default=True, alias="LOG_REDACT_API_KEYS")
    cost_tracking_enabled: bool = Field(default=True, alias="COST_TRACKING_ENABLED")

    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    def lambda_for_memory_type(self, memory_type: str) -> float:
        mapping = {
            "preference": self.decay_lambda_preference,
            "fact": self.decay_lambda_fact,
            "outcome": self.decay_lambda_outcome,
            "correction": self.decay_lambda_correction,
            "consolidated": self.decay_lambda_preference,
        }
        return mapping.get(memory_type, self.decay_lambda_fact)

    def redacted_repr(self) -> dict[str, object]:
        data = self.model_dump()
        if self.log_redact_api_keys and data.get("qwen_api_key"):
            data["qwen_api_key"] = "***"
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
