"""Shared enumerations used across domain models and modules.

Keeping these in one file avoids scattering string literals ("military",
"legal", "supported", ...) throughout the codebase, which is a common
source of silent bugs (typos that don't fail until runtime).
"""

from __future__ import annotations

from enum import Enum


class Perspective(str, Enum):
    """The three analytical perspectives MIL-EVID organizes evidence into."""

    MILITARY = "military"
    LEGAL = "legal"
    HISTORICAL = "historical"


class SourceType(str, Enum):
    """Where a piece of evidence originated from."""

    UCDP = "ucdp"
    SIPRI = "sipri"
    ICRC_IHL = "icrc_ihl"
    UN_PEACEMAKER = "un_peacemaker"
    ACLED = "acled"


class RetrievalMethod(str, Enum):
    """Which retrieval method surfaced a given piece of evidence."""

    BM25 = "bm25"
    DENSE = "dense"
    HYBRID = "hybrid"


class ContradictionStatus(str, Enum):
    """Outcome of comparing two evidence items for logical consistency."""

    ENTAILMENT = "entailment"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"


class ContradictionType(str, Enum):
    """Finer-grained classification of a detected contradiction.

    Distinguishing these matters: a temporal discrepancy (two sources
    giving different dates for the same event) is a very different
    finding from a factual contradiction (sources disagreeing on what
    happened), and both differ from cases where the model is simply
    unsure.
    """

    FACTUAL = "factual"
    TEMPORAL = "temporal"
    UNCERTAIN = "uncertain"
    NONE = "none"


class ClaimVerificationStatus(str, Enum):
    """Whether a generated claim is backed by retrieved evidence."""

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"


class ConfidenceLevel(str, Enum):
    """Coarse bucket for the final confidence score, for display."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimeScope(str, Enum):
    """Whether a query is asking about the present, the past, or both."""

    CURRENT = "current"
    HISTORICAL = "historical"
    BOTH = "both"
    UNSPECIFIED = "unspecified"
