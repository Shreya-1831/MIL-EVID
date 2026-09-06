"""Validation helpers for raw evidence records.

This module validates raw source records before they are mapped into
EvidenceDocument domain objects.

Validation is intentionally lightweight at this stage because different
sources use different field names. Source-specific mappers are
responsible for validating source-specific fields.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.exceptions import PreprocessingError


def validate_raw_record(record: Mapping[str, Any]) -> None:
    """Validate that a raw record has a usable structure.

    The function checks only generic requirements shared by all sources:

    - The record must be a mapping.
    - The record must not be empty.

    Source-specific validation belongs in individual source mappers.

    Raises:
        PreprocessingError: If the record is invalid.
    """

    if not isinstance(record, Mapping):
        raise PreprocessingError("Raw record must be a mapping")

    if not record:
        raise PreprocessingError("Raw record must not be empty")