"""Application configuration for the optimized MIL-EVID runtime."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetrievalWeights(BaseSettings):
    relevance: float = Field(default=0.30, ge=0.0, le=1.0)
    agreement: float = Field(default=0.20, ge=0.0, le=1.0)
    freshness: float = Field(default=0.15, ge=0.0, le=1.0)
    source_reliability: float = Field(default=0.15, ge=0.0, le=1.0)
    claim_support: float = Field(default=0.20, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_sum(self) -> "RetrievalWeights":
        total = (
            self.relevance + self.agreement + self.freshness
            + self.source_reliability + self.claim_support
        )
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Confidence weights must sum to 1.0, got {total:.4f}")
        return self


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",env_nested_delimiter="__",extra="ignore",)

    app_name: str = Field(default="mil-evid", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(alias="DATABASE_URL")
    db_pool_size: int = Field(default=5, gt=0, alias="DB_POOL_SIZE")
    db_batch_size: int = Field(default=1000, gt=0, alias="DB_BATCH_SIZE")

    acled_api_url: str = Field(alias="ACLED_API_URL")
    acled_username: str = Field(default="", alias="ACLED_USERNAME")
    acled_password: str = Field(default="", alias="ACLED_PASSWORD")
    acled_timeout_seconds: float = Field(default=15.0, alias="ACLED_TIMEOUT_SECONDS")
    acled_max_retries: int = Field(default=3, alias="ACLED_MAX_RETRIES")

    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY",)
    jwt_algorithm: str = Field(default="HS256",alias="JWT_ALGORITHM",)
    access_token_expire_minutes: int = Field(default=30,gt=0,alias="ACCESS_TOKEN_EXPIRE_MINUTES",)
    refresh_token_expire_days: int = Field(default=7,gt=0,alias="REFRESH_TOKEN_EXPIRE_DAYS",)
    
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        alias="RERANKER_MODEL",
    )
    nli_model: str = Field(
        default="cross-encoder/nli-MiniLM2-L6-H768",
        alias="NLI_MODEL",
    )

    faiss_index_dir: str = Field(default="indexes/faiss", alias="FAISS_INDEX_DIR")
    bm25_index_dir: str = Field(default="indexes/bm25", alias="BM25_INDEX_DIR")

    # Runtime retrieval controls.
    bm25_top_k: int = Field(default=15, gt=0, alias="BM25_TOP_K")
    dense_top_k: int = Field(default=15, gt=0, alias="DENSE_TOP_K")
    rrf_k: int = Field(default=60, gt=0, alias="RRF_K")
    rerank_top_n: int = Field(default=4, gt=0, alias="RERANK_TOP_N")
    rerank_candidate_k: int = Field(default=15, gt=0, alias="RERANK_CANDIDATE_K")

    chunk_size: int = Field(default=1000, gt=0, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=150, ge=0, alias="CHUNK_OVERLAP")
    near_duplicate_threshold: float = Field(default=0.85, ge=0.0, le=1.0, alias="NEAR_DUPLICATE_THRESHOLD")
    shingle_size: int = Field(default=5, gt=0, alias="SHINGLE_SIZE")

    raw_data_dir: str = Field(default="data/raw", alias="RAW_DATA_DIR")
    chunk_store_dir: str = Field(default="data/processed/chunks", alias="CHUNK_STORE_DIR")
    primary_countries_raw: str = Field(default="", alias="PRIMARY_COUNTRIES")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")
    ollama_timeout_seconds: float = Field(default=120.0, gt=0, alias="OLLAMA_TIMEOUT_SECONDS")
    ollama_num_predict: int = Field(default=220, gt=32, alias="OLLAMA_NUM_PREDICT")
    ollama_keep_alive: str = Field(default="24h", alias="OLLAMA_KEEP_ALIVE")

    analysis_max_concurrency: int = Field(default=3, ge=1, le=4, alias="ANALYSIS_MAX_CONCURRENCY")
    verification_max_concurrency: int = Field(default=4, ge=1, le=4, alias="VERIFICATION_MAX_CONCURRENCY")
    contradiction_max_concurrency: int = Field(default=4, ge=1, le=4, alias="CONTRADICTION_MAX_CONCURRENCY")

    contradiction_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0, alias="CONTRADICTION_CONFIDENCE_THRESHOLD")
    claim_support_threshold: float = Field(default=0.5, ge=0.0, le=1.0, alias="CLAIM_SUPPORT_THRESHOLD")

    weight_relevance: float = Field(default=0.30, alias="WEIGHT_RELEVANCE")
    weight_agreement: float = Field(default=0.20, alias="WEIGHT_AGREEMENT")
    weight_freshness: float = Field(default=0.15, alias="WEIGHT_FRESHNESS")
    weight_source_reliability: float = Field(default=0.15, alias="WEIGHT_SOURCE_RELIABILITY")
    weight_claim_support: float = Field(default=0.20, alias="WEIGHT_CLAIM_SUPPORT")

    @property
    def primary_countries(self) -> tuple[str, ...]:
        if not self.primary_countries_raw.strip():
            return ()
        return tuple(
            c.strip()
            for c in self.primary_countries_raw.split(",")
            if c.strip()
        )

    @model_validator(mode="after")
    def _check_chunk_overlap(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size "
                f"(got overlap={self.chunk_overlap}, size={self.chunk_size})"
            )
        return self

    @property
    def confidence_weights(self) -> RetrievalWeights:
        return RetrievalWeights(
            relevance=self.weight_relevance,
            agreement=self.weight_agreement,
            freshness=self.weight_freshness,
            source_reliability=self.weight_source_reliability,
            claim_support=self.weight_claim_support,
        )

    @property
    def acled_configured(self) -> bool:
        return bool(self.acled_username and self.acled_password)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
