from __future__ import annotations

from typing import NoReturn
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from merit_assistant.application.ports.document_persistence import (
    DocumentPersistenceError,
    DuplicateDocumentPersistenceError,
    EvaluationReferencePersistenceError,
)
from merit_assistant.domain.entities import Document
from merit_assistant.infrastructure.db.models import (
    DocumentModel,
    EvaluationModel,
)

DUPLICATE_DOCUMENT_CONSTRAINT = "uq_documents_evaluation_sha256"
EVALUATION_REFERENCE_CONSTRAINT = "fk_documents_evaluation_id"


class SqlAlchemyDocumentPersistence:
    """Persist document metadata using an injected SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def evaluation_exists(self, evaluation_id: UUID) -> bool:
        """Return whether the referenced evaluation exists."""
        statement = select(EvaluationModel.id).where(EvaluationModel.id == evaluation_id).limit(1)

        try:
            return self._session.scalar(statement) is not None
        except SQLAlchemyError as exc:
            self._raise_translated_error(exc)

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256: str,
    ) -> bool:
        """Return whether the hash already exists in the evaluation."""
        statement = (
            select(DocumentModel.id)
            .where(
                DocumentModel.evaluation_id == evaluation_id,
                DocumentModel.sha256 == sha256,
            )
            .limit(1)
        )

        try:
            return self._session.scalar(statement) is not None
        except SQLAlchemyError as exc:
            self._raise_translated_error(exc)

    def add(self, document: Document) -> None:
        """Add document metadata to the current transaction."""
        model = DocumentModel(
            id=document.id,
            evaluation_id=document.evaluation_id,
            original_filename=document.original_filename,
            storage_key=document.storage_key,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            sha256=document.sha256,
            created_at=document.created_at,
        )

        try:
            self._session.add(model)
        except SQLAlchemyError as exc:
            self._raise_translated_error(exc)

    def commit(self) -> None:
        """Commit the current transaction without automatic rollback."""
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._raise_translated_error(exc)

    def rollback(self) -> None:
        """Roll back the current transaction."""
        try:
            self._session.rollback()
        except SQLAlchemyError as exc:
            self._raise_translated_error(exc)

    @classmethod
    def _raise_translated_error(
        cls,
        error: SQLAlchemyError,
    ) -> NoReturn:
        if isinstance(error, IntegrityError):
            constraint_name = cls._constraint_name(error)

            if constraint_name == DUPLICATE_DOCUMENT_CONSTRAINT:
                raise DuplicateDocumentPersistenceError(
                    "document already exists in the evaluation"
                ) from error

            if constraint_name == EVALUATION_REFERENCE_CONSTRAINT:
                raise EvaluationReferencePersistenceError(
                    "referenced evaluation does not exist"
                ) from error

        raise DocumentPersistenceError("document persistence operation failed") from error

    @staticmethod
    def _constraint_name(error: IntegrityError) -> str | None:
        diagnostic = getattr(error.orig, "diag", None)
        constraint_name = getattr(
            diagnostic,
            "constraint_name",
            None,
        )

        if isinstance(constraint_name, str):
            return constraint_name

        return None
