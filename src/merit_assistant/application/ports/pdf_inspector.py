from __future__ import annotations

from typing import Protocol


class PdfInspector(Protocol):
    """Contract for validating the structural integrity of PDF content."""

    def validate(self, content: bytes) -> None:
        """Validate that the content represents an accepted PDF document."""
        ...
