"""ICRC source mapper.

Expects the directory layout observed in this project's `data/raw/icrc`:

    icrc/customary_ihl/rule_<NN>_<slug>/rule_<NN>_{Rules,Practice}.pdf
    icrc/ihl_treaties/<treaty_slug>.pdf

Every ICRC document becomes one `EvidenceDocument` per PDF (not
per-rule-folder) — a "Rules" PDF and its companion "Practice" PDF for
the same rule are distinct pieces of evidence with different content
(the rule statement vs. state-practice examples supporting it), and
keeping them separate lets retrieval and citation point to the right
one. Chunking (a later pipeline stage) splits each further if needed.

ICRC IHL is a global legal source, not tied to a specific country, so
it is never subject to `country_filter` — see `build_icrc_documents`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from app.core.exceptions import UnmappableRecordError
from app.domain.enums import Perspective, SourceType
from app.domain.models.evidence import EvidenceDocument
from app.modules.ingestion.pdf_extractor import extract_pdf_text

_RULE_DIR_RE = re.compile(r"^rule_(\d+)_(.+)$")
_RULE_FILE_RE = re.compile(r"^rule_(\d+)_(Rules|Practice)$", re.IGNORECASE)


def _slug_to_title(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").strip().title()


def _build_customary_ihl_document(pdf_path: Path, raw_data_dir: Path) -> EvidenceDocument:
    rule_dir_match = _RULE_DIR_RE.match(pdf_path.parent.name)
    file_match = _RULE_FILE_RE.match(pdf_path.stem)

    if not rule_dir_match or not file_match:
        raise UnmappableRecordError(
            f"ICRC customary IHL path does not match expected naming: {pdf_path}"
        )

    rule_number = rule_dir_match.group(1)
    rule_slug = rule_dir_match.group(2)
    document_kind = file_match.group(2).lower()  # "rules" or "practice"

    text = extract_pdf_text(pdf_path)
    if not text.strip():
        raise UnmappableRecordError(f"No extractable text in {pdf_path}")

    relative_path = pdf_path.relative_to(raw_data_dir).as_posix()
    title = f"Rule {rule_number}: {_slug_to_title(rule_slug)} ({document_kind.title()})"

    return EvidenceDocument(
        id=f"icrc::{relative_path}",
        text=text,
        source="ICRC Customary IHL",
        source_type=SourceType.ICRC_IHL,
        perspective=Perspective.LEGAL,
        title=title,
        date=None,  # Customary IHL rules are not dated documents.
        url=None,
        metadata={
            "rule_number": rule_number,
            "rule_slug": rule_slug,
            "document_kind": document_kind,
            "source_file": relative_path,
        },
    )


def _build_treaty_document(pdf_path: Path, raw_data_dir: Path) -> EvidenceDocument:
    text = extract_pdf_text(pdf_path)
    if not text.strip():
        raise UnmappableRecordError(f"No extractable text in {pdf_path}")

    relative_path = pdf_path.relative_to(raw_data_dir).as_posix()

    return EvidenceDocument(
        id=f"icrc::{relative_path}",
        text=text,
        source="ICRC IHL Treaty",
        source_type=SourceType.ICRC_IHL,
        perspective=Perspective.LEGAL,
        title=_slug_to_title(pdf_path.stem),
        date=None,
        url=None,
        metadata={
            "document_kind": "treaty",
            "source_file": relative_path,
        },
    )


def iter_icrc_documents(
    raw_data_dir: Path,
    *,
    on_error: str = "skip",
) -> Iterator[EvidenceDocument]:
    """Walk `raw_data_dir/icrc` and yield one `EvidenceDocument` per PDF.

    `on_error` controls behavior for individual unmappable/corrupt
    files: `"skip"` (default) logs nothing here and simply omits the
    file — callers that want visibility should wrap this generator
    and log; `"raise"` propagates the underlying `IngestionError`,
    useful for a strict validation run over a small known-good corpus.
    """
    icrc_dir = raw_data_dir / "icrc"
    if not icrc_dir.exists():
        return

    customary_dir = icrc_dir / "customary_ihl"
    if customary_dir.exists():
        for pdf_path in sorted(customary_dir.rglob("*.pdf")):
            try:
                yield _build_customary_ihl_document(pdf_path, raw_data_dir)
            except UnmappableRecordError:
                if on_error == "raise":
                    raise
                continue

    treaties_dir = icrc_dir / "ihl_treaties"
    if treaties_dir.exists():
        for pdf_path in sorted(treaties_dir.glob("*.pdf")):
            try:
                yield _build_treaty_document(pdf_path, raw_data_dir)
            except UnmappableRecordError:
                if on_error == "raise":
                    raise
                continue
