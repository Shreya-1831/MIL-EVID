"""UN Peacemaker source mapper.

Expects the directory layout observed in `data/raw/un_peacemaker`:

    un_peacemaker/<country_folder>/<slug_with_optional_year>.pdf

The country is taken from the folder name (normalized via
`country_filter.normalize_country_name`), which is why this mapper —
unlike the ICRC one — is the natural place to apply MVP country
filtering: the country is known before the (potentially expensive)
PDF text extraction runs, so filtering here saves real work.

The year, when present in the filename (e.g. `1998_good_friday_
agreement.pdf`), becomes the document's `date` (January 1 of that
year — peace-agreement filenames give a year, not a full date, and
that's a truthful representation of the precision actually known).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from app.core.exceptions import UnmappableRecordError
from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.ingestion.pdf_extractor import extract_pdf_text
from app.modules.preprocessing.country_filter import (
    is_primary_country,
    normalize_country_name,
)

_YEAR_RE = re.compile(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)")


def _extract_year(filename_stem: str) -> int | None:
    match = _YEAR_RE.search(filename_stem)
    if not match:
        return None
    return int(match.group(1))


def _slug_to_title(stem: str) -> str:
    # Strip a leading year token before title-casing, e.g.
    # "1998_good_friday_agreement" -> "Good Friday Agreement".
    without_year = _YEAR_RE.sub("", stem, count=1).strip("_- ")
    cleaned = without_year.replace("_", " ").replace("-", " ").strip()
    return cleaned.title() if cleaned else stem.replace("_", " ").title()


def _build_document(pdf_path: Path, raw_data_dir: Path, country_folder: str) -> EvidenceDocument:
    text = extract_pdf_text(pdf_path)
    if not text.strip():
        raise UnmappableRecordError(f"No extractable text in {pdf_path}")

    relative_path = pdf_path.relative_to(raw_data_dir).as_posix()
    year = _extract_year(pdf_path.stem)
    country = normalize_country_name(country_folder)

    return EvidenceDocument(
        id=f"un_peacemaker::{relative_path}",
        text=text,
        source="UN Peacemaker",
        source_type=SourceType.UN_PEACEMAKER,
        perspective=Perspective.HISTORICAL,
        title=_slug_to_title(pdf_path.stem),
        date=datetime(year, 1, 1) if year else None,
        url=None,
        metadata={
            "country": country,
            "source_file": relative_path,
            **({"year": year} if year else {}),
        },
    )


def iter_un_peacemaker_documents(
    raw_data_dir: Path,
    *,
    primary_country_set: frozenset[str] = frozenset(),
    on_error: str = "skip",
) -> Iterator[EvidenceDocument]:
    """Walk `raw_data_dir/un_peacemaker` and yield one `EvidenceDocument` per PDF.

    Applies country filtering (`primary_country_set`) at the
    folder level before extracting any PDF text — an empty set means
    "no filtering," matching `country_filter.is_primary_country`'s
    convention. `on_error` behaves as in `icrc_mapper`.
    """
    un_peacemaker_dir = raw_data_dir / "un_peacemaker"
    if not un_peacemaker_dir.exists():
        return

    for country_dir in sorted(p for p in un_peacemaker_dir.iterdir() if p.is_dir()):
        if not is_primary_country(country_dir.name, primary_country_set):
            continue

        for pdf_path in sorted(country_dir.glob("*.pdf")):
            try:
                yield _build_document(pdf_path, raw_data_dir, country_dir.name)
            except UnmappableRecordError:
                if on_error == "raise":
                    raise
                continue
