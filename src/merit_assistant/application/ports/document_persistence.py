from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from merit_assistant.domain.entities import Document


class DocumentPersistenceError(Exception):
    """Base error for document persistence operations."""


class DuplicateDocumentPersistenceError(DocumentPersistenceError):
    """Raised when a document already exists in the same evaluation."""


class EvaluationReferencePersistenceError(DocumentPersistenceError):
    """Raised when the referenced evaluation does not exist."""


class DocumentPersistence(Protocol):
    """Contract for document metadata persistence."""

    def evaluation_exists(self, evaluation_id: UUID) -> bool:
        """Return whether the target evaluation exists."""
        ...

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256: str,
    ) -> bool:
        """Return whether the document hash exists in the evaluation."""
        ...

    def list_by_evaluation(
        self,
        evaluation_id: UUID,
    ) -> Sequence[Document]:
        """Return documents for one evaluation in deterministic order."""
        ...

    def add(self, document: Document) -> None:
        """Add document metadata to the current transaction."""
        ...

    def commit(self) -> None:
        """Commit the current persistence transaction."""
        ...

    def rollback(self) -> None:
        """Roll back the current persistence transaction."""
        ...
