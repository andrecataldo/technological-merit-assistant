from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from io import BytesIO
from typing import cast

import pymupdf
import pytest

from merit_assistant.application.services.document_validation import (
    DocumentTooLargeError,
    DocumentValidationError,
    DocumentValidationService,
    EmptyDocumentError,
    InvalidOriginalFilenameError,
    InvalidPdfError,
    NonSeekableDocumentError,
    UnsupportedContentTypeError,
    ValidatedDocumentMetadata,
)

VALID_SHA256 = "a" * 64


class NoOpPdfInspector:
    def validate(self, content: bytes) -> None:
        """Accept any content for service-level unit tests."""


class NonSeekableBytesIO(BytesIO):
    def seekable(self) -> bool:
        return False


def validation_service(
    max_size_bytes: int = 1024,
) -> DocumentValidationService:
    return DocumentValidationService(
        inspector=NoOpPdfInspector(),
        max_size_bytes=max_size_bytes,
    )


def valid_metadata() -> ValidatedDocumentMetadata:
    return ValidatedDocumentMetadata(
        original_filename="synthetic.pdf",
        content_type="application/pdf",
        size_bytes=128,
        sha256=VALID_SHA256,
    )


def test_validated_metadata_contains_only_approved_fields() -> None:
    field_names = tuple(field.name for field in fields(ValidatedDocumentMetadata))

    assert field_names == (
        "original_filename",
        "content_type",
        "size_bytes",
        "sha256",
    )


def test_validated_metadata_is_immutable() -> None:
    metadata = valid_metadata()

    with pytest.raises(FrozenInstanceError):
        metadata.__setattr__("size_bytes", 256)


def test_validated_metadata_uses_slots() -> None:
    metadata = valid_metadata()

    assert not hasattr(metadata, "__dict__")


def test_validated_metadata_accepts_valid_values() -> None:
    metadata = valid_metadata()

    assert metadata.original_filename == "synthetic.pdf"
    assert metadata.content_type == "application/pdf"
    assert metadata.size_bytes == 128
    assert metadata.sha256 == VALID_SHA256


@pytest.mark.parametrize("size_bytes", [0, -1])
def test_validated_metadata_rejects_nonpositive_size(
    size_bytes: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="size_bytes must be greater than zero",
    ):
        ValidatedDocumentMetadata(
            original_filename="synthetic.pdf",
            content_type="application/pdf",
            size_bytes=size_bytes,
            sha256=VALID_SHA256,
        )


@pytest.mark.parametrize(
    "sha256",
    [
        "",
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "g" * 64,
        ("a" * 63) + " ",
    ],
)
def test_validated_metadata_rejects_invalid_sha256(
    sha256: str,
) -> None:
    with pytest.raises(ValueError, match="sha256"):
        ValidatedDocumentMetadata(
            original_filename="synthetic.pdf",
            content_type="application/pdf",
            size_bytes=128,
            sha256=sha256,
        )


@pytest.mark.parametrize(
    "error_type",
    [
        InvalidOriginalFilenameError,
        UnsupportedContentTypeError,
        EmptyDocumentError,
        DocumentTooLargeError,
        NonSeekableDocumentError,
        InvalidPdfError,
    ],
)
def test_validation_errors_share_common_base(
    error_type: type[DocumentValidationError],
) -> None:
    assert issubclass(error_type, DocumentValidationError)


@pytest.mark.parametrize("max_size_bytes", [0, -1])
def test_service_rejects_nonpositive_size_limit(
    max_size_bytes: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_size_bytes must be greater than zero",
    ):
        validation_service(max_size_bytes=max_size_bytes)


def test_filename_validation_accepts_pdf_and_trims_external_spaces() -> None:
    service = validation_service()

    filename = service._validate_original_filename("  synthetic report.pdf  ")

    assert filename == "synthetic report.pdf"


def test_filename_validation_accepts_uppercase_pdf_extension() -> None:
    service = validation_service()

    filename = service._validate_original_filename("synthetic.PDF")

    assert filename == "synthetic.PDF"


@pytest.mark.parametrize(
    "original_filename",
    [
        "",
        "   ",
        ".",
        "..",
        "synthetic.txt",
        "/tmp/synthetic.pdf",
        "folder/synthetic.pdf",
        r"folder\synthetic.pdf",
        "synthetic.pdf\x00",
    ],
)
def test_filename_validation_rejects_invalid_values(
    original_filename: str,
) -> None:
    service = validation_service()

    with pytest.raises(InvalidOriginalFilenameError):
        service._validate_original_filename(original_filename)


def test_content_type_validation_accepts_application_pdf() -> None:
    service = validation_service()

    content_type = service._normalize_content_type("application/pdf")

    assert content_type == "application/pdf"


def test_content_type_validation_normalizes_case_spaces_and_parameters() -> None:
    service = validation_service()

    content_type = service._normalize_content_type("  APPLICATION/PDF ; charset=binary  ")

    assert content_type == "application/pdf"


@pytest.mark.parametrize(
    "declared_content_type",
    [
        None,
        "",
        "   ",
        "text/plain",
        "application/json",
    ],
)
def test_content_type_validation_rejects_unsupported_values(
    declared_content_type: str | None,
) -> None:
    service = validation_service()

    with pytest.raises(UnsupportedContentTypeError):
        service._normalize_content_type(declared_content_type)


def test_rewind_source_positions_stream_at_zero() -> None:
    service = validation_service()
    source = BytesIO(b"synthetic content")
    source.seek(5)

    service._rewind_source(source)

    assert source.tell() == 0


def test_rewind_source_rejects_nonseekable_stream() -> None:
    service = validation_service()
    source = NonSeekableBytesIO(b"synthetic content")

    with pytest.raises(
        NonSeekableDocumentError,
        match="must be seekable",
    ):
        service._rewind_source(source)


def test_rewind_source_does_not_close_stream() -> None:
    service = validation_service()
    source = BytesIO(b"synthetic content")

    service._rewind_source(source)

    assert not source.closed


class RecordingBytesIO(BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.read_sizes: list[int | None] = []

    def read(self, size: int | None = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)


class FailingReadBytesIO(BytesIO):
    def read(self, size: int | None = -1) -> bytes:
        raise OSError("synthetic read failure")


def test_validate_returns_characterized_metadata() -> None:
    content = b"%PDF-synthetic-content"
    service = validation_service(max_size_bytes=len(content))
    source = BytesIO(content)

    metadata = service.validate(
        original_filename="  synthetic.PDF  ",
        declared_content_type="APPLICATION/PDF; charset=binary",
        source=source,
    )

    assert metadata.original_filename == "synthetic.PDF"
    assert metadata.content_type == "application/pdf"
    assert metadata.size_bytes == len(content)


def test_validate_calculates_sha256_from_exact_received_bytes() -> None:
    import hashlib

    content = b"%PDF-synthetic-content-for-sha256"
    service = validation_service(max_size_bytes=len(content))

    metadata = service.validate(
        original_filename="synthetic.pdf",
        declared_content_type="application/pdf",
        source=BytesIO(content),
    )

    assert metadata.sha256 == hashlib.sha256(content).hexdigest()


def test_validate_accepts_document_exactly_at_size_limit() -> None:
    content = b"%PDF-"
    service = validation_service(max_size_bytes=len(content))

    metadata = service.validate(
        original_filename="synthetic.pdf",
        declared_content_type="application/pdf",
        source=BytesIO(content),
    )

    assert metadata.size_bytes == len(content)


def test_validate_rejects_document_one_byte_above_limit() -> None:
    content = b"%PDF-X"
    service = validation_service(max_size_bytes=len(content) - 1)

    with pytest.raises(
        DocumentTooLargeError,
        match="exceeds the configured size limit",
    ):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(content),
        )


def test_validate_rejects_empty_document() -> None:
    service = validation_service()

    with pytest.raises(
        EmptyDocumentError,
        match="must not be empty",
    ):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(),
        )


def test_validate_rejects_missing_pdf_signature() -> None:
    content = b"synthetic non-PDF content"
    service = validation_service(max_size_bytes=len(content))

    with pytest.raises(
        InvalidPdfError,
        match="PDF signature",
    ):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(content),
        )


def test_validate_reads_source_in_controlled_chunks() -> None:
    chunk_size = 1024 * 1024
    content = b"%PDF-" + (b"x" * (chunk_size + 10 - 5))
    source = RecordingBytesIO(content)
    service = validation_service(max_size_bytes=len(content))

    metadata = service.validate(
        original_filename="synthetic.pdf",
        declared_content_type="application/pdf",
        source=source,
    )

    assert metadata.size_bytes == len(content)
    assert source.read_sizes == [
        chunk_size,
        11,
        1,
    ]


def test_validate_stops_reading_after_first_excess_byte() -> None:
    content = b"%PDF-" + (b"x" * 95)
    source = RecordingBytesIO(content)
    service = validation_service(max_size_bytes=10)

    with pytest.raises(DocumentTooLargeError):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=source,
        )

    assert source.read_sizes == [11]


def test_validate_rewinds_source_and_keeps_it_open_after_success() -> None:
    content = b"%PDF-synthetic-content"
    source = BytesIO(content)
    source.seek(8)
    service = validation_service(max_size_bytes=len(content))

    service.validate(
        original_filename="synthetic.pdf",
        declared_content_type="application/pdf",
        source=source,
    )

    assert source.tell() == 0
    assert not source.closed


def test_validate_rewinds_source_after_validation_error() -> None:
    source = BytesIO(b"not-a-pdf")
    source.seek(4)
    service = validation_service(max_size_bytes=100)

    with pytest.raises(InvalidPdfError):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=source,
        )

    assert source.tell() == 0
    assert not source.closed


def test_validate_propagates_read_failure_and_rewinds_source() -> None:
    source = FailingReadBytesIO(b"%PDF-synthetic")
    source.seek(3)
    service = validation_service(max_size_bytes=100)

    with pytest.raises(
        OSError,
        match="synthetic read failure",
    ):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=source,
        )

    assert source.tell() == 0
    assert not source.closed


class RecordingPdfInspector:
    def __init__(
        self,
        error: Exception | None = None,
    ) -> None:
        self.received_contents: list[bytes] = []
        self._error = error

    def validate(self, content: bytes) -> None:
        self.received_contents.append(content)

        if self._error is not None:
            raise self._error


def create_valid_pdf_for_service() -> bytes:
    """Create a valid one-page PDF entirely in memory."""
    with pymupdf.open() as document:  # type: ignore[no-untyped-call]
        document.new_page()
        return cast(bytes, document.tobytes())


def test_service_from_settings_converts_megabytes_to_bytes() -> None:
    from merit_assistant.config.settings import Settings

    inspector = RecordingPdfInspector()
    settings = Settings(max_upload_size_mb=2)

    service = DocumentValidationService.from_settings(
        inspector=inspector,
        settings=settings,
    )

    assert service._max_size_bytes == 2 * 1024 * 1024


def test_validate_calls_inspector_once_with_exact_content() -> None:
    content = b"%PDF-synthetic-content"
    inspector = RecordingPdfInspector()
    service = DocumentValidationService(
        inspector=inspector,
        max_size_bytes=len(content),
    )

    service.validate(
        original_filename="synthetic.pdf",
        declared_content_type="application/pdf",
        source=BytesIO(content),
    )

    assert inspector.received_contents == [content]


def test_invalid_filename_does_not_call_inspector() -> None:
    inspector = RecordingPdfInspector()
    service = DocumentValidationService(
        inspector=inspector,
        max_size_bytes=100,
    )

    with pytest.raises(InvalidOriginalFilenameError):
        service.validate(
            original_filename="../synthetic.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(b"%PDF-synthetic"),
        )

    assert inspector.received_contents == []


def test_invalid_content_type_does_not_call_inspector() -> None:
    inspector = RecordingPdfInspector()
    service = DocumentValidationService(
        inspector=inspector,
        max_size_bytes=100,
    )

    with pytest.raises(UnsupportedContentTypeError):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="text/plain",
            source=BytesIO(b"%PDF-synthetic"),
        )

    assert inspector.received_contents == []


def test_empty_document_does_not_call_inspector() -> None:
    inspector = RecordingPdfInspector()
    service = DocumentValidationService(
        inspector=inspector,
        max_size_bytes=100,
    )

    with pytest.raises(EmptyDocumentError):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(),
        )

    assert inspector.received_contents == []


def test_document_above_limit_does_not_call_inspector() -> None:
    inspector = RecordingPdfInspector()
    service = DocumentValidationService(
        inspector=inspector,
        max_size_bytes=5,
    )

    with pytest.raises(DocumentTooLargeError):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(b"%PDF-X"),
        )

    assert inspector.received_contents == []


def test_invalid_signature_does_not_call_inspector() -> None:
    content = b"not-a-PDF"
    inspector = RecordingPdfInspector()
    service = DocumentValidationService(
        inspector=inspector,
        max_size_bytes=len(content),
    )

    with pytest.raises(InvalidPdfError, match="PDF signature"):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(content),
        )

    assert inspector.received_contents == []


def test_structural_validation_error_rewinds_source() -> None:
    content = b"%PDF-synthetic-invalid-structure"
    inspector = RecordingPdfInspector(error=InvalidPdfError("synthetic structural failure"))
    service = DocumentValidationService(
        inspector=inspector,
        max_size_bytes=len(content),
    )
    source = BytesIO(content)
    source.seek(8)

    with pytest.raises(
        InvalidPdfError,
        match="synthetic structural failure",
    ):
        service.validate(
            original_filename="synthetic.pdf",
            declared_content_type="application/pdf",
            source=source,
        )

    assert inspector.received_contents == [content]
    assert source.tell() == 0
    assert not source.closed


def test_service_accepts_pdf_with_real_pymupdf_inspector() -> None:
    from merit_assistant.infrastructure.pdf.pymupdf_inspector import (
        PyMuPdfInspector,
    )

    content = create_valid_pdf_for_service()
    service = DocumentValidationService(
        inspector=PyMuPdfInspector(),
        max_size_bytes=len(content),
    )
    source = BytesIO(content)

    metadata = service.validate(
        original_filename="synthetic.pdf",
        declared_content_type="application/pdf",
        source=source,
    )

    assert metadata.size_bytes == len(content)
    assert metadata.content_type == "application/pdf"
    assert source.tell() == 0
    assert not source.closed
