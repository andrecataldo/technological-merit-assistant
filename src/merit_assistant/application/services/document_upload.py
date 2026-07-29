from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from io import RawIOBase
from typing import BinaryIO, Final, NoReturn, cast
from uuid import UUID, uuid4

from merit_assistant.application.ports.document_persistence import (
    DocumentPersistence,
    DocumentPersistenceError,
    DuplicateDocumentPersistenceError,
    EvaluationReferencePersistenceError,
)
from merit_assistant.application.ports.document_storage import (
    DocumentStorage,
)
from merit_assistant.application.services.document_validation import (
    DocumentValidationService,
    NonSeekableDocumentError,
    ValidatedDocumentMetadata,
)
from merit_assistant.domain.entities import Document

MAX_ORIGINAL_FILENAME_LENGTH: Final = 255


class DocumentUploadError(Exception):
    """Base error for secure document-upload orchestration."""


class EvaluationNotFoundError(DocumentUploadError):
    """Raised when the target evaluation does not exist."""


class DuplicateDocumentError(DocumentUploadError):
    """Raised when the document already exists in the evaluation."""


class OriginalFilenameTooLongError(DocumentUploadError):
    """Raised when the validated filename exceeds the persistence limit."""


class StoredContentMismatchError(DocumentUploadError):
    """Raised when stored bytes differ from validated document metadata."""


class DocumentUploadPersistenceError(DocumentUploadError):
    """Raised when document metadata cannot be persisted."""


class DocumentCompensationError(DocumentUploadError):
    """Raised when upload compensation cannot be completed safely."""

    def __init__(
        self,
        message: str = "document upload compensation failed",
        *,
        rollback_error: Exception | None = None,
        delete_error: Exception | None = None,
        delete_result: bool | None = None,
        restore_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.rollback_error = rollback_error
        self.delete_error = delete_error
        self.delete_result = delete_result
        self.restore_error = restore_error

        self.rollback_succeeded = rollback_error is None
        self.delete_succeeded = delete_error is None and delete_result is True
        self.source_restored = restore_error is None


@dataclass(frozen=True, slots=True)
class _CompensationResult:
    rollback_error: Exception | None
    delete_error: Exception | None
    delete_result: bool | None
    restore_error: Exception | None

    @property
    def failed(self) -> bool:
        return (
            self.rollback_error is not None
            or self.delete_error is not None
            or self.delete_result is not True
        )


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(UTC)


class _VerifyingReader(RawIOBase):
    """Observe bytes consumed by storage without buffering document content."""

    def __init__(self, source: BinaryIO) -> None:
        super().__init__()
        self._source = source
        self._content_hash = sha256()
        self._size_bytes = 0
        self._eof_reached = False

    @property
    def size_bytes(self) -> int:
        """Return the number of bytes consumed from the original stream."""
        return self._size_bytes

    @property
    def sha256(self) -> str:
        """Return the SHA-256 of bytes consumed from the original stream."""
        return self._content_hash.hexdigest()

    @property
    def eof_reached(self) -> bool:
        """Return whether the original stream returned an empty byte string."""
        return self._eof_reached

    def readable(self) -> bool:
        """Report that this wrapper supports binary reads."""
        return True

    def tell(self) -> int:
        """Return the current position of the original stream."""
        return self._source.tell()

    def read(self, size: int = -1) -> bytes:
        """Delegate reading and observe only the returned bytes."""
        chunk = self._source.read(size)

        if chunk == b"":
            self._eof_reached = True
            return chunk

        self._size_bytes += len(chunk)
        self._content_hash.update(chunk)

        return chunk


class DocumentUploadService:
    """Orchestrate secure validation, storage and metadata persistence."""

    def __init__(
        self,
        validator: DocumentValidationService,
        storage: DocumentStorage,
        persistence: DocumentPersistence,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._validator = validator
        self._storage = storage
        self._persistence = persistence
        self._id_factory = id_factory
        self._clock = clock

    def upload(
        self,
        evaluation_id: UUID,
        original_filename: str,
        declared_content_type: str | None,
        source: BinaryIO,
    ) -> Document:
        """Validate, store and persist one document."""

        if not self._evaluation_exists(evaluation_id):
            raise EvaluationNotFoundError("target evaluation does not exist")

        metadata = self._validator.validate(
            original_filename=original_filename,
            declared_content_type=declared_content_type,
            source=source,
        )

        self._validate_filename_length(metadata)

        if self._document_exists(
            evaluation_id=evaluation_id,
            content_sha256=metadata.sha256,
        ):
            raise DuplicateDocumentError("document already exists in the evaluation")

        document_id = self._id_factory()
        created_at = self._created_at_utc()

        self._assert_source_at_start(source)

        verifying_reader = _VerifyingReader(source)

        storage_key = self._storage.store(
            evaluation_id=evaluation_id,
            document_id=document_id,
            source=cast(BinaryIO, verifying_reader),
        )

        try:
            self._validate_stored_content(
                verifying_reader=verifying_reader,
                metadata=metadata,
            )

            self._rewind_source(source)

            document = Document(
                id=document_id,
                evaluation_id=evaluation_id,
                original_filename=metadata.original_filename,
                storage_key=storage_key,
                content_type=metadata.content_type,
                size_bytes=metadata.size_bytes,
                sha256=metadata.sha256,
                created_at=created_at,
            )

            self._persistence.add(document)
            self._persistence.commit()
        except Exception as exc:
            self._raise_after_compensation(
                original_error=exc,
                storage_key=storage_key,
                source=source,
            )

        return document

    def _evaluation_exists(self, evaluation_id: UUID) -> bool:
        try:
            return self._persistence.evaluation_exists(evaluation_id)
        except DocumentPersistenceError as exc:
            self._raise_translated_persistence_error(exc)

    def _document_exists(
        self,
        evaluation_id: UUID,
        content_sha256: str,
    ) -> bool:
        try:
            return self._persistence.exists_by_evaluation_and_sha256(
                evaluation_id,
                content_sha256,
            )
        except DocumentPersistenceError as exc:
            self._raise_translated_persistence_error(exc)

    @staticmethod
    def _validate_filename_length(
        metadata: ValidatedDocumentMetadata,
    ) -> None:
        if len(metadata.original_filename) > MAX_ORIGINAL_FILENAME_LENGTH:
            raise OriginalFilenameTooLongError(
                "validated original filename exceeds the persistence limit"
            )

    def _created_at_utc(self) -> datetime:
        created_at = self._clock()

        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")

        return created_at.astimezone(UTC)

    @staticmethod
    def _assert_source_at_start(source: BinaryIO) -> None:
        try:
            if source.tell() != 0:
                raise NonSeekableDocumentError(
                    "validated document source is not positioned at the beginning"
                )
        except NonSeekableDocumentError:
            raise
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise NonSeekableDocumentError("document source must support tell") from exc

    @staticmethod
    def _validate_stored_content(
        verifying_reader: _VerifyingReader,
        metadata: ValidatedDocumentMetadata,
    ) -> None:
        content_matches = (
            verifying_reader.eof_reached
            and verifying_reader.size_bytes == metadata.size_bytes
            and verifying_reader.sha256 == metadata.sha256
        )

        if not content_matches:
            raise StoredContentMismatchError("stored content does not match validated metadata")

    @staticmethod
    def _rewind_source(source: BinaryIO) -> None:
        try:
            source.seek(0)

            if source.tell() != 0:
                raise NonSeekableDocumentError(
                    "document source could not be restored to the beginning"
                )
        except NonSeekableDocumentError:
            raise
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise NonSeekableDocumentError("document source could not be restored") from exc

    def _raise_after_compensation(
        self,
        *,
        original_error: Exception,
        storage_key: str,
        source: BinaryIO,
    ) -> NoReturn:
        result = self._compensate(
            storage_key=storage_key,
            source=source,
        )

        if result.failed:
            compensation_error = DocumentCompensationError(
                rollback_error=result.rollback_error,
                delete_error=result.delete_error,
                delete_result=result.delete_result,
                restore_error=result.restore_error,
            )
            raise compensation_error from original_error

        if isinstance(original_error, DocumentPersistenceError):
            self._raise_translated_persistence_error(original_error)

        raise original_error

    def _compensate(
        self,
        *,
        storage_key: str,
        source: BinaryIO,
    ) -> _CompensationResult:
        rollback_error: Exception | None = None
        delete_error: Exception | None = None
        delete_result: bool | None = None
        restore_error: Exception | None = None

        try:
            self._persistence.rollback()
        except Exception as exc:
            rollback_error = exc

        try:
            delete_result = self._storage.delete(storage_key)
        except Exception as exc:
            delete_error = exc

        try:
            self._rewind_source(source)
        except Exception as exc:
            restore_error = exc

        return _CompensationResult(
            rollback_error=rollback_error,
            delete_error=delete_error,
            delete_result=delete_result,
            restore_error=restore_error,
        )

    @staticmethod
    def _raise_translated_persistence_error(
        error: DocumentPersistenceError,
    ) -> NoReturn:
        if isinstance(
            error,
            DuplicateDocumentPersistenceError,
        ):
            raise DuplicateDocumentError("document already exists in the evaluation") from error

        if isinstance(
            error,
            EvaluationReferencePersistenceError,
        ):
            raise EvaluationNotFoundError("target evaluation does not exist") from error

        raise DocumentUploadPersistenceError("document metadata persistence failed") from error
