"""Application configuration.

All configuration is loaded from environment variables (or a local
`.env` file during development) via pydantic-settings. Nothing here
is hardcoded: credentials, URLs, and tunable parameters all come from
the environment so the same code can run against different
deployments without modification.

Use `get_settings()` to obtain the singleton settings instance. The
function is cached with `lru_cache` so the environment is parsed once
per process, not on every call.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetrievalWeights(BaseSettings):
    """Weights used by the confidence scorer.

    Kept as a nested model (rather than five loose floats) so callers
    can pass a single object around and so validation of the "weights
    sum to 1.0" invariant lives in one place.
    """

    relevance: float = Field(default=0.30, ge=0.0, le=1.0)
    agreement: float = Field(default=0.20, ge=0.0, le=1.0)
    freshness: float = Field(default=0.15, ge=0.0, le=1.0)
    source_reliability: float = Field(default=0.15, ge=0.0, le=1.0)
    claim_support: float = Field(default=0.20, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_sum(self) -> "RetrievalWeights":
        total = (
            self.relevance
            + self.agreement
            + self.freshness
            + self.source_reliability
            + self.claim_support
        )
        # Allow small floating point drift.
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Confidence weights must sum to 1.0, got {total:.4f}"
            )
        return self


class Settings(BaseSettings):
    """Top-level application settings.

    Instantiating this class reads and validates environment
    variables immediately, so configuration errors surface at
    startup rather than deep inside a request.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # --- Application ---
    app_name: str = Field(default="mil-evid", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Database ---
    database_url: str = Field(alias="DATABASE_URL")
    db_pool_size: int = Field(default=5, gt=0, alias="DB_POOL_SIZE")
    db_batch_size: int = Field(
        default=1000,
        gt=0,
        alias="DB_BATCH_SIZE",
        description="Row batch size for bulk metadata upserts.",
    )

    # --- ACLED ---
    acled_api_url: str = Field(alias="ACLED_API_URL")
    acled_username: str = Field(default="", alias="ACLED_USERNAME")
    acled_password: str = Field(default="", alias="ACLED_PASSWORD")
    acled_timeout_seconds: float = Field(default=15.0, alias="ACLED_TIMEOUT_SECONDS")
    acled_max_retries: int = Field(default=3, alias="ACLED_MAX_RETRIES")

    # --- Retrieval models ---
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

    # --- Index locations ---
    faiss_index_dir: str = Field(default="indexes/faiss", alias="FAISS_INDEX_DIR")
    bm25_index_dir: str = Field(default="indexes/bm25", alias="BM25_INDEX_DIR")

    # --- Retrieval tuning ---
    bm25_top_k: int = Field(default=50, gt=0, alias="BM25_TOP_K")
    dense_top_k: int = Field(default=50, gt=0, alias="DENSE_TOP_K")
    rrf_k: int = Field(default=60, gt=0, alias="RRF_K")
    rerank_top_n: int = Field(default=20, gt=0, alias="RERANK_TOP_N")

    # --- Preprocessing / chunking ---
    chunk_size: int = Field(
        default=1000,
        gt=0,
        alias="CHUNK_SIZE",
        description="Target chunk size in characters.",
    )
    chunk_overlap: int = Field(
        default=150,
        ge=0,
        alias="CHUNK_OVERLAP",
        description="Overlap between consecutive chunks, in characters.",
    )
    near_duplicate_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        alias="NEAR_DUPLICATE_THRESHOLD",
        description="Jaccard shingle similarity above which two documents are treated as near-duplicates.",
    )
    shingle_size: int = Field(
        default=5,
        gt=0,
        alias="SHINGLE_SIZE",
        description="Word n-gram size used for near-duplicate shingling.",
    )

    # --- Ingestion / storage locations ---
    raw_data_dir: str = Field(
        default="data/raw",
        alias="RAW_DATA_DIR",
        description="Root directory containing raw source files (ucdp/, icrc/, un_peacemaker/, sipri/).",
    )
    chunk_store_dir: str = Field(
        default="data/processed/chunks",
        alias="CHUNK_STORE_DIR",
        description=(
            "Local directory holding chunk text as JSONL files, one per "
            "source. This is the source of truth for chunk text — "
            "Postgres stores metadata only, never full chunk text, to "
            "stay within small/free database storage tiers."
        ),
    )
    primary_countries_raw: str = Field(
        default="",
        alias="PRIMARY_COUNTRIES",
        description=(
            "Comma-separated list of country names to filter static "
            "evidence to (MVP scope control). Empty means no filtering."
        ),
    )

    # --- Local LLM / Ollama ---
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL",
    )

    ollama_model: str = Field(
        # default="llama3.2:3b",
        default="llama3.1:8b",
        alias="OLLAMA_MODEL",
    )

    ollama_timeout_seconds: float = Field(
        default=120.0,
        gt=0,
        alias="OLLAMA_TIMEOUT_SECONDS",
    )

    @property
    def primary_countries(self) -> tuple[str, ...]:
        """Parsed, normalized primary-country list.

        Kept as a computed property (rather than a raw list field) so
        the comma-separated env value has one place where it's split
        and lightly cleaned. Country *name* normalization/aliasing
        (e.g. "US" -> "united states") lives in
        `modules.preprocessing.country_filter`, not here — settings
        should stay free of domain logic.
        """
        if not self.primary_countries_raw.strip():
            return ()
        return tuple(
            c.strip() for c in self.primary_countries_raw.split(",") if c.strip()
        )

    @model_validator(mode="after")
    def _check_chunk_overlap(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size "
                f"(got overlap={self.chunk_overlap}, size={self.chunk_size})"
            )
        return self

    # --- Thresholds ---
    contradiction_confidence_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, alias="CONTRADICTION_CONFIDENCE_THRESHOLD"
    )
    claim_support_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, alias="CLAIM_SUPPORT_THRESHOLD"
    )

    # --- Confidence weights ---
    weight_relevance: float = Field(default=0.30, alias="WEIGHT_RELEVANCE")
    weight_agreement: float = Field(default=0.20, alias="WEIGHT_AGREEMENT")
    weight_freshness: float = Field(default=0.15, alias="WEIGHT_FRESHNESS")
    weight_source_reliability: float = Field(
        default=0.15, alias="WEIGHT_SOURCE_RELIABILITY"
    )
    weight_claim_support: float = Field(default=0.20, alias="WEIGHT_CLAIM_SUPPORT")

    @property
    def confidence_weights(self) -> RetrievalWeights:
        """Build a validated `RetrievalWeights` from the flat env fields."""
        return RetrievalWeights(
            relevance=self.weight_relevance,
            agreement=self.weight_agreement,
            freshness=self.weight_freshness,
            source_reliability=self.weight_source_reliability,
            claim_support=self.weight_claim_support,
        )

    @property
    def acled_configured(self) -> bool:
        """Whether enough ACLED credentials are present to call the API.

        The pipeline uses this to decide whether to attempt dynamic
        evidence retrieval at all, rather than failing at call time.
        """
        return bool(self.acled_username and self.acled_password)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide `Settings` singleton.

    Cached so environment parsing/validation happens once. Tests that
    need different settings should call `get_settings.cache_clear()`
    after monkeypatching the environment.
    """
    return Settings()
