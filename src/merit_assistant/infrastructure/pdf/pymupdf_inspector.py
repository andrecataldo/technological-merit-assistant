from __future__ import annotations

import pymupdf

from merit_assistant.application.services.document_validation import (
    InvalidPdfError,
)


class PyMuPdfInspector:
    """Validate PDF structure using the local PyMuPDF parser."""

    def validate(self, content: bytes) -> None:
        """Validate that content is a readable PDF containing at least one page."""
        try:
            with pymupdf.open(  # type: ignore[no-untyped-call]
                stream=content,
                filetype="pdf",
            ) as document:
                if not document.is_pdf:
                    raise InvalidPdfError("document content is not a PDF")

                if document.page_count < 1:
                    raise InvalidPdfError("PDF document must contain at least one page")
        except InvalidPdfError:
            raise
        except pymupdf.FileDataError as exc:
            raise InvalidPdfError("PDF document has an invalid structure") from exc
