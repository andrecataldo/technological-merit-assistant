from __future__ import annotations

from typing import BinaryIO, Protocol
from uuid import UUID


class DocumentStorageError(Exception):
    """Base error for document storage operations."""


class UnsafeStoragePathError(DocumentStorageError):
    """Raised when a storage key points outside the configured private root."""


class DocumentAlreadyExistsError(DocumentStorageError):
    """Raised when the destination document already exists."""


class DocumentStorage(Protocol):
    """Contract for storing documents independently from the storage backend."""

    def store(
        self,
        evaluation_id: UUID,
        document_id: UUID,
        source: BinaryIO,
    ) -> str:
        """Store binary content and return its relative storage key."""
        ...

    def open_binary(self, storage_key: str) -> BinaryIO:
        """Open a stored document for binary reading."""
        ...

    def delete(self, storage_key: str) -> bool:
        """Delete a stored document, returning whether a file was removed."""
        ...
