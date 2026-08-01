from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import BinaryIO, Final

from merit_assistant.application.ports.pdf_inspector import PdfInspector
from merit_assistant.config.settings import Settings

PDF_CONTENT_TYPE: Final = "application/pdf"
PDF_SIGNATURE: Final = b"%PDF-"
CHUNK_SIZE: Final = 1024 * 1024


class DocumentValidationError(Exception):
    """Base error for document validation operations."""


class InvalidOriginalFilenameError(DocumentValidationError):
    """Raised when the original filename is missing or invalid."""


class UnsupportedContentTypeError(DocumentValidationError):
    """Raised when the declared content type is missing or unsupported."""


class EmptyDocumentError(DocumentValidationError):
    """Raised when the received document has no content."""


class DocumentTooLargeError(DocumentValidationError):
    """Raised when the document exceeds the configured size limit."""


class NonSeekableDocumentError(DocumentValidationError):
    """Raised when the input stream cannot be positioned safely."""


class InvalidPdfError(DocumentValidationError):
    """Raised when the content does not represent an accepted PDF."""


@dataclass(frozen=True, slots=True)
class ValidatedDocumentMetadata:
    """Validated metadata calculated from received document content."""

    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        if self.size_bytes <= 0:
            raise ValueError("size_bytes must be greater than zero")

        if len(self.sha256) != 64:
            raise ValueError("sha256 must contain exactly 64 characters")

        if any(character not in "0123456789abcdef" for character in self.sha256):
            raise ValueError("sha256 must contain only lowercase hexadecimal characters")


class DocumentValidationService:
    """Validate document metadata and binary input before storage."""

    def __init__(
        self,
        inspector: PdfInspector,
        max_size_bytes: int,
    ) -> None:
        if max_size_bytes <= 0:
            raise ValueError("max_size_bytes must be greater than zero")

        self._inspector = inspector
        self._max_size_bytes = max_size_bytes

    @classmethod
    def from_settings(
        cls,
        inspector: PdfInspector,
        settings: Settings,
    ) -> DocumentValidationService:
        """Create the service using the configured upload-size limit."""
        return cls(
            inspector=inspector,
            max_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
        )

    def validate(
        self,
        original_filename: str,
        declared_content_type: str | None,
        source: BinaryIO,
    ) -> ValidatedDocumentMetadata:
        """Validate and characterize a document without storing it."""
        filename = self._validate_original_filename(original_filename)
        content_type = self._normalize_content_type(declared_content_type)

        self._rewind_source(source)

        validation_failed = False

        try:
            content, size_bytes, content_sha256 = self._read_and_characterize(source)

            if not content.startswith(PDF_SIGNATURE):
                raise InvalidPdfError("document content does not start with a PDF signature")

            self._inspector.validate(content)

            return ValidatedDocumentMetadata(
                original_filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
                sha256=content_sha256,
            )
        except Exception:
            validation_failed = True
            raise
        finally:
            try:
                self._rewind_source(source)
            except NonSeekableDocumentError:
                if not validation_failed:
                    raise

    def _read_and_characterize(
        self,
        source: BinaryIO,
    ) -> tuple[bytes, int, str]:
        content = bytearray()
        content_hash = sha256()
        size_bytes = 0

        while True:
            remaining_bytes = self._max_size_bytes - size_bytes
            requested_bytes = min(
                CHUNK_SIZE,
                remaining_bytes + 1,
            )

            chunk = source.read(requested_bytes)

            if not chunk:
                break

            size_bytes += len(chunk)

            if size_bytes > self._max_size_bytes:
                raise DocumentTooLargeError("document exceeds the configured size limit")

            content.extend(chunk)
            content_hash.update(chunk)

        if size_bytes == 0:
            raise EmptyDocumentError("document content must not be empty")

        return bytes(content), size_bytes, content_hash.hexdigest()

    @staticmethod
    def _validate_original_filename(original_filename: str) -> str:
        filename = original_filename.strip()

        if not filename:
            raise InvalidOriginalFilenameError("original filename must not be empty")

        if "\x00" in filename:
            raise InvalidOriginalFilenameError("original filename contains an invalid character")

        if "/" in filename or "\\" in filename:
            raise InvalidOriginalFilenameError("original filename must not contain path separators")

        if filename in {".", ".."}:
            raise InvalidOriginalFilenameError("original filename is invalid")

        if not filename.lower().endswith(".pdf"):
            raise InvalidOriginalFilenameError("original filename must use the .pdf extension")

        return filename

    @staticmethod
    def _normalize_content_type(
        declared_content_type: str | None,
    ) -> str:
        if declared_content_type is None:
            raise UnsupportedContentTypeError("declared content type is required")

        content_type = declared_content_type.strip()

        if not content_type:
            raise UnsupportedContentTypeError("declared content type is required")

        media_type = content_type.split(";", maxsplit=1)[0].strip().lower()

        if media_type != PDF_CONTENT_TYPE:
            raise UnsupportedContentTypeError("declared content type must be application/pdf")

        return PDF_CONTENT_TYPE

    @staticmethod
    def _rewind_source(source: BinaryIO) -> None:
        try:
            if not source.seekable():
                raise NonSeekableDocumentError("document source must be seekable")

            source.seek(0)

            if source.tell() != 0:
                raise NonSeekableDocumentError(
                    "document source could not be positioned at the beginning"
                )
        except NonSeekableDocumentError:
            raise
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise NonSeekableDocumentError("document source must support seek and tell") from exc
