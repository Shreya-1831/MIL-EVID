"""PDF text extraction with local OCR fallback.

Uses pypdf for normal text-based PDFs.
Falls back to PyMuPDF + RapidOCR for scanned/image-only PDFs.

No Tesseract, Poppler, API, or cloud service is required.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pymupdf
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from rapidocr_onnxruntime import RapidOCR

from app.core.exceptions import CorruptSourceFileError


_OCR_ENGINE: RapidOCR | None = None


def _get_ocr_engine() -> RapidOCR:
    """Create the OCR engine once and reuse it."""
    global _OCR_ENGINE

    if _OCR_ENGINE is None:
        _OCR_ENGINE = RapidOCR()

    return _OCR_ENGINE


def _extract_with_pypdf(path: Path) -> list[str]:
    """Extract text from a PDF using its existing text layer."""
    try:
        reader = PdfReader(str(path))
    except (PdfReadError, OSError) as exc:
        raise CorruptSourceFileError(
            f"Could not open PDF at {path}: {exc}"
        ) from exc

    pages: list[str] = []

    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            pages.append("")

    return pages


def _extract_page_with_ocr(
    page: pymupdf.Page,
    ocr_engine: RapidOCR,
) -> str:
    """Render one PDF page and extract text with RapidOCR."""
    try:
        pixmap = page.get_pixmap(
            dpi=200,
            alpha=False,
        )

        image_bytes = pixmap.tobytes("png")

        image = cv2.imdecode(
            np.frombuffer(image_bytes, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise ValueError("Could not decode rendered PDF page.")

        result, _ = ocr_engine(image)

    except Exception as exc:  # noqa: BLE001
        raise CorruptSourceFileError(
            f"OCR failed for PDF page: {exc}"
        ) from exc

    if not result:
        return ""

    texts: list[str] = []

    for item in result:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            text = str(item[1]).strip()

            if text:
                texts.append(text)

    return "\n".join(texts)


def _extract_with_ocr(path: Path) -> list[str]:
    """Extract text from scanned PDF pages using local RapidOCR."""
    try:
        pdf = pymupdf.open(str(path))
    except Exception as exc:  # noqa: BLE001
        raise CorruptSourceFileError(
            f"Could not open PDF for OCR at {path}: {exc}"
        ) from exc

    try:
        ocr_engine = _get_ocr_engine()

        pages: list[str] = []

        for page in pdf:
            pages.append(
                _extract_page_with_ocr(
                    page,
                    ocr_engine,
                )
            )

        return pages

    finally:
        pdf.close()


def extract_pdf_pages(path: Path) -> list[str]:
    """Extract PDF text page-by-page.

    Normal PDFs use pypdf.
    Scanned/image-only PDFs automatically fall back to
    local PyMuPDF + RapidOCR.
    """
    pages = _extract_with_pypdf(path)

    if any(page.strip() for page in pages):
        return pages

    return _extract_with_ocr(path)


def extract_pdf_text(
    path: Path,
    *,
    page_separator: str = "\n\n",
) -> str:
    """Extract and join all available PDF text.

    Empty pages are excluded from the final text.
    """
    pages = [
        page.strip()
        for page in extract_pdf_pages(path)
        if page.strip()
    ]

    return page_separator.join(pages)