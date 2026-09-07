"""
Local file-based storage for chunk text.

Chunk text is stored locally as JSONL.
PostgreSQL stores metadata only.

Storage is source-based:
    data/processed/chunks/
        ucdp_ged.jsonl
        ucdp_dyadic.jsonl
        sipri.jsonl
        ...

Writes are atomic.

Write modes:

1. replace_chunks()
   Replaces the complete source file.
   Use when rebuilding a source from scratch.

2. append_chunks()
   Appends a processed batch without checking existing records.
   Use when raw append behavior is explicitly required.

3. append_unique_chunks()
   Appends only chunks whose IDs are not already stored.
   Use for idempotent large-scale ingestion.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from pathlib import Path

from app.core.exceptions import RepositoryError
from app.domain.models.evidence import EvidenceDocument


_UNSAFE_FILENAME_CHARS = re.compile(r"[^a-z0-9_-]+")


def source_to_filename(source: str) -> str:
    """Convert a source name into a safe deterministic filename."""
    slug = source.strip().lower().replace(" ", "_")
    slug = _UNSAFE_FILENAME_CHARS.sub("", slug)
    return slug or "unknown_source"


def _store_path(chunk_store_dir: Path, source: str) -> Path:
    """Return the JSONL path for a source."""
    return chunk_store_dir / f"{source_to_filename(source)}.jsonl"


def _validate_chunks(
    chunks: Sequence[EvidenceDocument],
) -> str:
    """Validate a chunk batch and return its source."""
    if not chunks:
        raise RepositoryError(
            "Chunk storage requires at least one chunk."
        )

    sources = {chunk.source for chunk in chunks}

    if len(sources) != 1:
        raise RepositoryError(
            "All chunks in one storage operation must belong "
            f"to the same source: {sorted(sources)}"
        )

    return next(iter(sources))


def replace_chunks(
    chunks: Sequence[EvidenceDocument],
    *,
    chunk_store_dir: Path,
) -> Path:
    """Replace the complete JSONL file for one source."""
    source = _validate_chunks(chunks)

    chunk_store_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_path = _store_path(
        chunk_store_dir,
        source,
    )

    tmp_path = target_path.with_suffix(".jsonl.tmp")

    try:
        with tmp_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            for chunk in chunks:
                file.write(chunk.model_dump_json())
                file.write("\n")

        tmp_path.replace(target_path)

    except OSError as exc:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

        raise RepositoryError(
            f"Failed to replace chunk store "
            f"for source '{source}': {exc}"
        ) from exc

    return target_path


def append_chunks(
    chunks: Sequence[EvidenceDocument],
    *,
    chunk_store_dir: Path,
) -> Path:
    """Append one processed batch without duplicate checking."""
    source = _validate_chunks(chunks)

    chunk_store_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_path = _store_path(
        chunk_store_dir,
        source,
    )

    try:
        with target_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            for chunk in chunks:
                file.write(chunk.model_dump_json())
                file.write("\n")

    except OSError as exc:
        raise RepositoryError(
            f"Failed to append chunks "
            f"for source '{source}': {exc}"
        ) from exc

    return target_path


def append_unique_chunks(
    chunks: Sequence[EvidenceDocument],
    *,
    chunk_store_dir: Path,
) -> tuple[Path, int]:
    """Append only chunks whose IDs are not already stored.

    Existing chunk IDs are loaded once for the source, then used
    to filter the incoming batch. This keeps repeated ingestion
    runs idempotent without scanning the file for every chunk.
    """
    source = _validate_chunks(chunks)

    chunk_store_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_path = _store_path(
        chunk_store_dir,
        source,
    )

    existing_ids: set[str] = set()

    if target_path.exists():
        for existing_chunk in read_chunks(target_path):
            existing_ids.add(existing_chunk.id)

    new_chunks: list[EvidenceDocument] = []
    seen_ids: set[str] = set()

    for chunk in chunks:
        if chunk.id in existing_ids or chunk.id in seen_ids:
            continue

        new_chunks.append(chunk)
        seen_ids.add(chunk.id)

    if not new_chunks:
        return target_path, 0

    try:
        with target_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            for chunk in new_chunks:
                file.write(chunk.model_dump_json())
                file.write("\n")

    except OSError as exc:
        raise RepositoryError(
            f"Failed to append unique chunks "
            f"for source '{source}': {exc}"
        ) from exc

    return target_path, len(new_chunks)


def write_chunks(
    chunks: Sequence[EvidenceDocument],
    *,
    chunk_store_dir: Path,
) -> Path:
    """Backward-compatible alias for complete source replacement."""
    return replace_chunks(
        chunks,
        chunk_store_dir=chunk_store_dir,
    )


def read_chunks(
    path: Path,
) -> Iterator[EvidenceDocument]:
    """Stream evidence chunks from a JSONL file."""
    if not path.exists():
        return

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line_number, line in enumerate(
                file,
                start=1,
            ):
                line = line.strip()

                if not line:
                    continue

                try:
                    yield EvidenceDocument.model_validate_json(line)

                except ValueError as exc:
                    raise RepositoryError(
                        "Corrupt chunk record at "
                        f"{path}:{line_number}: {exc}"
                    ) from exc

    except OSError as exc:
        raise RepositoryError(
            f"Failed to read chunk store '{path}': {exc}"
        ) from exc


def iter_all_chunks(
    chunk_store_dir: Path,
) -> Iterator[EvidenceDocument]:
    """Stream all chunks across all source files."""
    if not chunk_store_dir.exists():
        return

    for path in sorted(chunk_store_dir.glob("*.jsonl")):
        yield from read_chunks(path)


def list_store_files(
    chunk_store_dir: Path,
) -> tuple[Path, ...]:
    """Return all JSONL store files in deterministic order."""
    if not chunk_store_dir.exists():
        return ()

    return tuple(sorted(chunk_store_dir.glob("*.jsonl")))


def count_chunks(
    chunk_store_dir: Path,
) -> dict[str, int]:
    """Count stored chunks for every source."""
    counts: dict[str, int] = {}

    for path in list_store_files(chunk_store_dir):
        counts[path.stem] = sum(
            1
            for _ in read_chunks(path)
        )

    return counts

def get_chunks_by_id(
    chunk_ids: Sequence[str],
    *,
    chunk_store_dir: Path,
) -> dict[str, EvidenceDocument]:
    """Return requested chunks from the local JSONL chunk store.

    The store remains the source of truth for full chunk text.

    This function scans the local store once for the requested batch
    and stops as soon as all requested IDs have been found.
    """

    requested = {
        chunk_id
        for chunk_id in chunk_ids
        if isinstance(chunk_id, str) and chunk_id
    }

    if not requested:
        return {}

    found: dict[str, EvidenceDocument] = {}

    for chunk in iter_all_chunks(chunk_store_dir):
        if chunk.id in requested:
            found[chunk.id] = chunk

            if len(found) == len(requested):
                break

    return found