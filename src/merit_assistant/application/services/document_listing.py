from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from merit_assistant.application.ports.document_persistence import (
    DocumentPersistence,
    DocumentPersistenceError,
)
from merit_assistant.domain.entities import Document


class DocumentListingError(Exception):
    """Base error for document listing operations."""


class DocumentListingEvaluationNotFoundError(DocumentListingError):
    """Raised when the target evaluation does not exist."""


class DocumentListingPersistenceError(DocumentListingError):
    """Raised when persistence fails during document listing."""


class DocumentListingService:
    """List document metadata associated with one evaluation."""

    def __init__(
        self,
        persistence: DocumentPersistence,
    ) -> None:
        self._persistence = persistence

    def list_for_evaluation(
        self,
        evaluation_id: UUID,
    ) -> Sequence[Document]:
        """Return documents for an existing evaluation."""

        try:
            evaluation_exists = self._persistence.evaluation_exists(evaluation_id)
        except DocumentPersistenceError as exc:
            raise DocumentListingPersistenceError(
                "document listing persistence operation failed"
            ) from exc

        if not evaluation_exists:
            raise DocumentListingEvaluationNotFoundError("target evaluation does not exist")

        try:
            return self._persistence.list_by_evaluation(evaluation_id)
        except DocumentPersistenceError as exc:
            raise DocumentListingPersistenceError(
                "document listing persistence operation failed"
            ) from exc
