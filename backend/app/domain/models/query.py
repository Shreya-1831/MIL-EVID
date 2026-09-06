"""Domain models produced by the query analysis module."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Perspective, TimeScope


class QueryClassification(BaseModel):
    """Structured understanding of a user's natural-language query.

    This is the single artifact that the rest of the pipeline
    (retrieval, dynamic-evidence fetch, perspective analysis) reads
    to decide what to do — nothing downstream re-parses the raw query
    string. See `modules/query_analysis` for the classifier that
    produces this and the `QueryClassifier` protocol that allows it
    to be swapped for an LLM-backed implementation later.
    """

    model_config = ConfigDict(frozen=True)

    raw_query: str = Field(..., min_length=1)
    normalized_query: str = Field(..., min_length=1)
    regions: tuple[str, ...] = Field(
        default_factory=tuple, description="Detected region/location mentions."
    )
    actors: tuple[str, ...] = Field(
        default_factory=tuple, description="Detected actor/organization mentions."
    )
    time_scope: TimeScope = TimeScope.UNSPECIFIED
    requires_dynamic_evidence: bool = Field(
        default=False,
        description="Whether current (ACLED) evidence should be fetched.",
    )
    required_perspectives: tuple[Perspective, ...] = Field(
        default_factory=lambda: (
            Perspective.MILITARY,
            Perspective.LEGAL,
            Perspective.HISTORICAL,
        )
    )
