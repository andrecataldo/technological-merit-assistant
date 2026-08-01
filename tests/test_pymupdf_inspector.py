from __future__ import annotations

import base64
from typing import cast

import pymupdf
import pytest

from merit_assistant.application.ports.pdf_inspector import PdfInspector
from merit_assistant.application.services.document_validation import (
    InvalidPdfError,
)
from merit_assistant.infrastructure.pdf.pymupdf_inspector import (
    PyMuPdfInspector,
)


def create_synthetic_pdf() -> bytes:
    """Create a one-page synthetic PDF entirely in memory."""
    with pymupdf.open() as document:  # type: ignore[no-untyped-call]
        document.new_page()
        return cast(bytes, document.tobytes())


def create_zero_page_pdf() -> bytes:
    """Create a structurally valid synthetic PDF with an empty page tree."""
    parts = [b"%PDF-1.4\n"]
    offsets = [0]

    objects = [
        (b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"),
        (b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"),
    ]

    for pdf_object in objects:
        offsets.append(sum(len(part) for part in parts))
        parts.append(pdf_object)

    xref_offset = sum(len(part) for part in parts)

    parts.append(b"xref\n0 3\n")
    parts.append(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        parts.append(f"{offset:010d} 00000 n \n".encode())

    parts.append(b"trailer\n<< /Size 3 /Root 1 0 R >>\n")
    parts.append(f"startxref\n{xref_offset}\n%%EOF\n".encode())

    return b"".join(parts)


def create_synthetic_png() -> bytes:
    """Return a synthetic one-pixel PNG recognized by PyMuPDF."""
    encoded = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
        "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    return base64.b64decode(encoded)


def test_pymupdf_inspector_satisfies_pdf_inspector_contract() -> None:
    inspector: PdfInspector = PyMuPdfInspector()

    assert isinstance(inspector, PyMuPdfInspector)


def test_pymupdf_inspector_accepts_valid_synthetic_pdf() -> None:
    inspector = PyMuPdfInspector()

    inspector.validate(create_synthetic_pdf())


def test_pymupdf_inspector_rejects_arbitrary_content() -> None:
    inspector = PyMuPdfInspector()

    with pytest.raises(
        InvalidPdfError,
        match="invalid structure",
    ):
        inspector.validate(b"synthetic invalid content")


def test_pymupdf_inspector_rejects_false_pdf_signature() -> None:
    inspector = PyMuPdfInspector()

    with pytest.raises(
        InvalidPdfError,
        match="invalid structure",
    ):
        inspector.validate(b"%PDF-not-a-valid-document")


def test_pymupdf_inspector_rejects_recognized_non_pdf_content() -> None:
    inspector = PyMuPdfInspector()

    with pytest.raises(
        InvalidPdfError,
        match="not a PDF",
    ):
        inspector.validate(create_synthetic_png())


def test_pymupdf_inspector_rejects_pdf_without_pages() -> None:
    inspector = PyMuPdfInspector()

    with pytest.raises(
        InvalidPdfError,
        match="at least one page",
    ):
        inspector.validate(create_zero_page_pdf())
