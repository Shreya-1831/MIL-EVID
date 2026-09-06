from __future__ import annotations

import pytest

from app.core.exceptions import PreprocessingError
from app.modules.ingestion.validators import validate_raw_record


def test_validate_raw_record_accepts_valid_record() -> None:
    record = {
        "id": "doc-001",
        "text": "Some evidence text.",
    }

    validate_raw_record(record)


def test_validate_raw_record_rejects_empty_record() -> None:
    with pytest.raises(
        PreprocessingError,
        match="Raw record must not be empty",
    ):
        validate_raw_record({})


def test_validate_raw_record_rejects_non_mapping() -> None:
    with pytest.raises(
        PreprocessingError,
        match="Raw record must be a mapping",
    ):
        validate_raw_record(["not", "a", "mapping"])