from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from typing import BinaryIO, cast
from uuid import UUID, uuid4

import pytest

from merit_assistant.application.ports.document_persistence import (
    DocumentPersistenceError,
    DuplicateDocumentPersistenceError,
    EvaluationReferencePersistenceError,
)
from merit_assistant.application.ports.document_storage import (
    DocumentStorageError,
)
from merit_assistant.application.services.document_upload import (
    DocumentCompensationError,
    DocumentUploadError,
    DocumentUploadPersistenceError,
    DocumentUploadService,
    DuplicateDocumentError,
    EvaluationNotFoundError,
    OriginalFilenameTooLongError,
    StoredContentMismatchError,
    _VerifyingReader,
)
from merit_assistant.application.services.document_validation import (
    DocumentValidationService,
    InvalidPdfError,
    NonSeekableDocumentError,
    ValidatedDocumentMetadata,
)
from merit_assistant.domain.entities import Document


class TrackingSource(BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.read_sizes: list[int | None] = []
        self.seek_calls = 0

    def read(self, size: int | None = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        self.seek_calls += 1
        return super().seek(offset, whence)


class ExpectedReadError(Exception):
    """Synthetic error used to prove propagation from the original stream."""


class FailingSource(BytesIO):
    def read(self, size: int | None = -1) -> bytes:
        del size
        raise ExpectedReadError("synthetic read failure")


def make_reader(source: BinaryIO) -> _VerifyingReader:
    return _VerifyingReader(source)


def test_reader_integral_read_produces_expected_size_and_sha256() -> None:
    content = b"%PDF-1.7\nsynthetic document content\n%%EOF"
    source = BytesIO(content)
    reader = make_reader(source)

    consumed = reader.read()
    eof = reader.read()

    assert consumed == content
    assert eof == b""
    assert reader.size_bytes == len(content)
    assert reader.sha256 == sha256(content).hexdigest()
    assert reader.eof_reached is True


def test_reader_multiple_reads_produce_the_same_sha256() -> None:
    content = b"%PDF-1.7\nmultiple chunks\n%%EOF"
    source = BytesIO(content)
    reader = make_reader(source)

    chunks = [
        reader.read(3),
        reader.read(5),
        reader.read(7),
        reader.read(),
    ]

    assert b"".join(chunks) == content
    assert reader.size_bytes == len(content)
    assert reader.sha256 == sha256(content).hexdigest()
    assert reader.eof_reached is False

    assert reader.read() == b""
    assert reader.eof_reached is True


def test_reader_partial_read_does_not_mark_eof() -> None:
    source = BytesIO(b"abcdef")
    reader = make_reader(source)

    assert reader.read(3) == b"abc"
    assert reader.size_bytes == 3
    assert reader.sha256 == sha256(b"abc").hexdigest()
    assert reader.eof_reached is False


def test_reader_marks_eof_only_after_empty_bytes() -> None:
    source = BytesIO(b"x")
    reader = make_reader(source)

    assert reader.read(1) == b"x"
    assert reader.eof_reached is False

    assert reader.read(1) == b""
    assert reader.eof_reached is True


def test_reader_delegates_requested_sizes_without_seeking() -> None:
    source = TrackingSource(b"abcdefgh")
    reader = make_reader(source)

    assert reader.read(2) == b"ab"
    assert reader.read(3) == b"cde"
    assert reader.read() == b"fgh"
    assert reader.read() == b""

    assert source.read_sizes == [2, 3, -1, -1]
    assert source.seek_calls == 0


def test_reader_close_does_not_close_original_stream() -> None:
    source = BytesIO(b"synthetic")
    reader = make_reader(source)

    reader.close()

    assert reader.closed is True
    assert source.closed is False


def test_reader_does_not_accumulate_document_content() -> None:
    content = b"%PDF-1.7\n" + (b"x" * 4096) + b"\n%%EOF"
    source = BytesIO(content)
    reader = make_reader(source)

    while reader.read(128):
        pass

    observed_values = tuple(vars(reader).values())

    assert content not in observed_values
    assert not hasattr(reader, "_content")
    assert not hasattr(reader, "_chunks")
    assert reader.size_bytes == len(content)


def test_reader_propagates_original_stream_error() -> None:
    source = FailingSource()
    reader = make_reader(source)

    with pytest.raises(
        ExpectedReadError,
        match="synthetic read failure",
    ):
        reader.read(32)

    assert reader.size_bytes == 0
    assert reader.sha256 == sha256().hexdigest()
    assert reader.eof_reached is False


@pytest.mark.parametrize(
    "exception_type",
    [
        EvaluationNotFoundError,
        DuplicateDocumentError,
        OriginalFilenameTooLongError,
        StoredContentMismatchError,
        DocumentUploadPersistenceError,
        DocumentCompensationError,
    ],
)
def test_exception_hierarchy_uses_document_upload_error(
    exception_type: type[DocumentUploadError],
) -> None:
    assert issubclass(exception_type, DocumentUploadError)


@pytest.mark.parametrize(
    "exception_type",
    [
        EvaluationNotFoundError,
        DuplicateDocumentError,
        OriginalFilenameTooLongError,
        StoredContentMismatchError,
        DocumentUploadPersistenceError,
        DocumentCompensationError,
    ],
)
def test_exception_message_does_not_expose_document_content(
    exception_type: type[DocumentUploadError],
) -> None:
    document_content = "%PDF-1.7 confidential synthetic content"
    complete_sha256 = "a" * 64
    error = exception_type("document upload operation failed")

    message = str(error)

    assert document_content not in message
    assert complete_sha256 not in message


class FakeUploadValidator:
    def __init__(
        self,
        metadata: ValidatedDocumentMetadata,
        events: list[str],
        error: Exception | None = None,
    ) -> None:
        self.metadata = metadata
        self.events = events
        self.error = error
        self.calls = 0

    def validate(
        self,
        original_filename: str,
        declared_content_type: str | None,
        source: BinaryIO,
    ) -> ValidatedDocumentMetadata:
        del original_filename
        del declared_content_type

        self.calls += 1
        self.events.append("validate")

        if self.error is not None:
            raise self.error

        source.seek(0)
        return self.metadata


class FakeUploadStorage:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.store_calls = 0
        self.delete_calls = 0
        self.received_evaluation_ids: list[UUID] = []
        self.received_document_ids: list[UUID] = []
        self.received_positions: list[int] = []

    def store(
        self,
        evaluation_id: UUID,
        document_id: UUID,
        source: BinaryIO,
    ) -> str:
        self.store_calls += 1
        self.events.append("store")
        self.received_evaluation_ids.append(evaluation_id)
        self.received_document_ids.append(document_id)
        self.received_positions.append(source.tell())

        while source.read(4):
            pass

        return f"evaluations/{evaluation_id}/documents/{document_id}.pdf"

    def open_binary(self, storage_key: str) -> BinaryIO:
        del storage_key
        return BytesIO()

    def delete(self, storage_key: str) -> bool:
        del storage_key
        self.delete_calls += 1
        self.events.append("delete")
        return True


class FakeUploadPersistence:
    def __init__(
        self,
        events: list[str],
        *,
        existing_evaluations: set[UUID] | None = None,
        existing_documents: set[tuple[UUID, str]] | None = None,
    ) -> None:
        self.events = events
        self.existing_evaluations = set(existing_evaluations or ())
        self.existing_documents = set(existing_documents or ())
        self.added_documents: list[Document] = []

        self.evaluation_exists_calls = 0
        self.duplicate_lookup_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    def evaluation_exists(self, evaluation_id: UUID) -> bool:
        self.evaluation_exists_calls += 1
        self.events.append("evaluation_exists")
        return evaluation_id in self.existing_evaluations

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256_value: str,
    ) -> bool:
        self.duplicate_lookup_calls += 1
        self.events.append("duplicate_lookup")
        return (
            evaluation_id,
            sha256_value,
        ) in self.existing_documents

    def add(self, document: Document) -> None:
        self.events.append("add")
        self.added_documents.append(document)

    def commit(self) -> None:
        self.events.append("commit")
        self.commit_calls += 1

    def rollback(self) -> None:
        self.events.append("rollback")
        self.rollback_calls += 1


def make_validated_metadata(
    content: bytes,
    *,
    original_filename: str = "synthetic-document.pdf",
) -> ValidatedDocumentMetadata:
    return ValidatedDocumentMetadata(
        original_filename=original_filename,
        content_type="application/pdf",
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
    )


def make_upload_service(
    *,
    validator: FakeUploadValidator,
    storage: FakeUploadStorage,
    persistence: FakeUploadPersistence,
    events: list[str],
    document_id: UUID,
    created_at: datetime,
) -> DocumentUploadService:
    def id_factory() -> UUID:
        events.append("id_factory")
        return document_id

    def clock() -> datetime:
        events.append("clock")
        return created_at

    return DocumentUploadService(
        validator=cast(DocumentValidationService, validator),
        storage=storage,
        persistence=persistence,
        id_factory=id_factory,
        clock=clock,
    )


def test_upload_success_preserves_values_and_call_order() -> None:
    content = b"%PDF-1.7\nsynthetic nominal content\n%%EOF"
    evaluation_id = uuid4()
    document_id = uuid4()
    created_at = datetime(2026, 7, 28, 20, 0, tzinfo=UTC)
    events: list[str] = []

    metadata = make_validated_metadata(content)
    validator = FakeUploadValidator(metadata, events)
    storage = FakeUploadStorage(events)
    persistence = FakeUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=document_id,
        created_at=created_at,
    )

    source = BytesIO(content)
    source.seek(5)

    document = service.upload(
        evaluation_id=evaluation_id,
        original_filename="synthetic-document.pdf",
        declared_content_type="application/pdf",
        source=source,
    )

    assert events == [
        "evaluation_exists",
        "validate",
        "duplicate_lookup",
        "id_factory",
        "clock",
        "store",
        "add",
        "commit",
    ]
    assert validator.calls == 1
    assert storage.store_calls == 1
    assert storage.received_evaluation_ids == [evaluation_id]
    assert storage.received_document_ids == [document_id]
    assert storage.received_positions == [0]
    assert storage.delete_calls == 0

    assert document.id == document_id
    assert document.evaluation_id == evaluation_id
    assert document.original_filename == metadata.original_filename
    assert document.content_type == metadata.content_type
    assert document.size_bytes == metadata.size_bytes
    assert document.sha256 == metadata.sha256
    assert document.created_at == created_at
    assert document.storage_key == (f"evaluations/{evaluation_id}/documents/{document_id}.pdf")

    assert persistence.added_documents == [document]
    assert persistence.commit_calls == 1
    assert persistence.rollback_calls == 0
    assert source.closed is False
    assert source.tell() == 0


def test_evaluation_not_found_rejects_before_validation() -> None:
    content = b"%PDF-1.7\nsynthetic\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []

    validator = FakeUploadValidator(
        make_validated_metadata(content),
        events,
    )
    storage = FakeUploadStorage(events)
    persistence = FakeUploadPersistence(events)
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(
        EvaluationNotFoundError,
        match="target evaluation does not exist",
    ):
        service.upload(
            evaluation_id=evaluation_id,
            original_filename="synthetic-document.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(content),
        )

    assert events == ["evaluation_exists"]
    assert validator.calls == 0
    assert persistence.duplicate_lookup_calls == 0
    assert storage.store_calls == 0
    assert persistence.commit_calls == 0


def test_validation_error_is_propagated_before_storage() -> None:
    content = b"not-a-pdf"
    evaluation_id = uuid4()
    events: list[str] = []

    validator = FakeUploadValidator(
        make_validated_metadata(b"%PDF-1.7\nvalid\n%%EOF"),
        events,
        error=InvalidPdfError("synthetic invalid PDF"),
    )
    storage = FakeUploadStorage(events)
    persistence = FakeUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(
        InvalidPdfError,
        match="synthetic invalid PDF",
    ):
        service.upload(
            evaluation_id=evaluation_id,
            original_filename="synthetic-document.pdf",
            declared_content_type="application/pdf",
            source=BytesIO(content),
        )

    assert events == ["evaluation_exists", "validate"]
    assert persistence.duplicate_lookup_calls == 0
    assert storage.store_calls == 0
    assert persistence.commit_calls == 0


def test_filename_longer_than_255_is_rejected_before_duplicate_lookup() -> None:
    content = b"%PDF-1.7\nsynthetic\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []

    metadata = make_validated_metadata(
        content,
        original_filename=("a" * 252) + ".pdf",
    )
    validator = FakeUploadValidator(metadata, events)
    storage = FakeUploadStorage(events)
    persistence = FakeUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(
        OriginalFilenameTooLongError,
        match="exceeds the persistence limit",
    ):
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type="application/pdf",
            source=BytesIO(content),
        )

    assert len(metadata.original_filename) == 256
    assert events == ["evaluation_exists", "validate"]
    assert persistence.duplicate_lookup_calls == 0
    assert storage.store_calls == 0
    assert persistence.commit_calls == 0


def test_known_duplicate_is_rejected_before_uuid_and_storage() -> None:
    content = b"%PDF-1.7\nsynthetic duplicate\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []

    metadata = make_validated_metadata(content)
    validator = FakeUploadValidator(metadata, events)
    storage = FakeUploadStorage(events)
    persistence = FakeUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
        existing_documents={(evaluation_id, metadata.sha256)},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(
        DuplicateDocumentError,
        match="already exists",
    ):
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=BytesIO(content),
        )

    assert events == [
        "evaluation_exists",
        "validate",
        "duplicate_lookup",
    ]
    assert storage.store_calls == 0
    assert persistence.commit_calls == 0


def test_same_sha256_in_different_evaluation_is_not_duplicate() -> None:
    content = b"%PDF-1.7\nsame content, different evaluation\n%%EOF"
    evaluation_id = uuid4()
    other_evaluation_id = uuid4()
    events: list[str] = []

    metadata = make_validated_metadata(content)
    validator = FakeUploadValidator(metadata, events)
    storage = FakeUploadStorage(events)
    persistence = FakeUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
        existing_documents={
            (other_evaluation_id, metadata.sha256),
        },
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    document = service.upload(
        evaluation_id=evaluation_id,
        original_filename=metadata.original_filename,
        declared_content_type=metadata.content_type,
        source=BytesIO(content),
    )

    assert document.evaluation_id == evaluation_id
    assert persistence.commit_calls == 1
    assert storage.store_calls == 1


def test_naive_timezone_is_rejected_before_storage() -> None:
    content = b"%PDF-1.7\nsynthetic timezone\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []

    metadata = make_validated_metadata(content)
    validator = FakeUploadValidator(metadata, events)
    storage = FakeUploadStorage(events)
    persistence = FakeUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, 20, 0),
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=BytesIO(content),
        )

    assert events == [
        "evaluation_exists",
        "validate",
        "duplicate_lookup",
        "id_factory",
        "clock",
    ]
    assert storage.store_calls == 0
    assert persistence.commit_calls == 0


class ConfigurableUploadStorage(FakeUploadStorage):
    def __init__(
        self,
        events: list[str],
        *,
        consume_to_eof: bool = True,
        store_error: Exception | None = None,
        delete_error: Exception | None = None,
        delete_result: bool = True,
    ) -> None:
        super().__init__(events)
        self.consume_to_eof = consume_to_eof
        self.store_error = store_error
        self.delete_error = delete_error
        self.delete_result = delete_result

    def store(
        self,
        evaluation_id: UUID,
        document_id: UUID,
        source: BinaryIO,
    ) -> str:
        self.store_calls += 1
        self.events.append("store")
        self.received_evaluation_ids.append(evaluation_id)
        self.received_document_ids.append(document_id)
        self.received_positions.append(source.tell())

        if self.store_error is not None:
            raise self.store_error

        if self.consume_to_eof:
            while source.read(4):
                pass
        else:
            source.read()

        return f"evaluations/{evaluation_id}/documents/{document_id}.pdf"

    def delete(self, storage_key: str) -> bool:
        del storage_key

        self.delete_calls += 1
        self.events.append("delete")

        if self.delete_error is not None:
            raise self.delete_error

        return self.delete_result


class ConfigurableUploadPersistence(FakeUploadPersistence):
    def __init__(
        self,
        events: list[str],
        *,
        existing_evaluations: set[UUID] | None = None,
        existing_documents: set[tuple[UUID, str]] | None = None,
        evaluation_exists_error: Exception | None = None,
        duplicate_lookup_error: Exception | None = None,
        add_error: Exception | None = None,
        commit_error: Exception | None = None,
        rollback_error: Exception | None = None,
    ) -> None:
        super().__init__(
            events,
            existing_evaluations=existing_evaluations,
            existing_documents=existing_documents,
        )
        self.evaluation_exists_error = evaluation_exists_error
        self.duplicate_lookup_error = duplicate_lookup_error
        self.add_error = add_error
        self.commit_error = commit_error
        self.rollback_error = rollback_error

    def evaluation_exists(self, evaluation_id: UUID) -> bool:
        if self.evaluation_exists_error is None:
            return super().evaluation_exists(evaluation_id)

        self.evaluation_exists_calls += 1
        self.events.append("evaluation_exists")
        raise self.evaluation_exists_error

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256_value: str,
    ) -> bool:
        if self.duplicate_lookup_error is None:
            return super().exists_by_evaluation_and_sha256(
                evaluation_id,
                sha256_value,
            )

        self.duplicate_lookup_calls += 1
        self.events.append("duplicate_lookup")
        raise self.duplicate_lookup_error

    def add(self, document: Document) -> None:
        self.events.append("add")

        if self.add_error is not None:
            raise self.add_error

        self.added_documents.append(document)

    def commit(self) -> None:
        self.events.append("commit")
        self.commit_calls += 1

        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self) -> None:
        self.events.append("rollback")
        self.rollback_calls += 1

        if self.rollback_error is not None:
            raise self.rollback_error


class ReplacingUploadValidator(FakeUploadValidator):
    def __init__(
        self,
        metadata: ValidatedDocumentMetadata,
        events: list[str],
        replacement_content: bytes,
    ) -> None:
        super().__init__(metadata, events)
        self.replacement_content = replacement_content

    def validate(
        self,
        original_filename: str,
        declared_content_type: str | None,
        source: BinaryIO,
    ) -> ValidatedDocumentMetadata:
        metadata = super().validate(
            original_filename,
            declared_content_type,
            source,
        )

        source.seek(0)
        source.truncate(0)
        source.write(self.replacement_content)
        source.seek(0)

        return metadata


class FailingRewindSource(BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.seek_calls = 0

    def seek(self, offset: int, whence: int = 0) -> int:
        self.seek_calls += 1

        if self.seek_calls >= 2:
            raise OSError("synthetic rewind failure")

        return super().seek(offset, whence)


@pytest.mark.parametrize(
    ("mismatch_kind", "consume_to_eof"),
    [
        ("missing-eof", False),
        ("hash", True),
        ("size", True),
    ],
    ids=["missing-eof", "hash-mismatch", "size-mismatch"],
)
def test_stored_content_mismatch_triggers_compensation(
    mismatch_kind: str,
    consume_to_eof: bool,
) -> None:
    content = b"%PDF-1.7\nsynthetic mismatch content\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)

    if mismatch_kind == "missing-eof":
        validator: FakeUploadValidator = FakeUploadValidator(
            metadata,
            events,
        )
    else:
        replacement_content = b"x" * len(content) if mismatch_kind == "hash" else b"short"

        if mismatch_kind == "hash":
            assert len(replacement_content) == len(content)
            assert sha256(replacement_content).hexdigest() != metadata.sha256

        validator = ReplacingUploadValidator(
            metadata,
            events,
            replacement_content,
        )

    storage = ConfigurableUploadStorage(
        events,
        consume_to_eof=consume_to_eof,
    )
    persistence = ConfigurableUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )
    source = BytesIO(content)

    with pytest.raises(StoredContentMismatchError):
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=source,
        )

    assert persistence.rollback_calls == 1
    assert storage.delete_calls == 1
    assert persistence.added_documents == []
    assert persistence.commit_calls == 0
    assert source.closed is False
    assert source.tell() == 0


def test_add_persistence_error_is_translated_and_compensated() -> None:
    content = b"%PDF-1.7\nsynthetic add failure\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)
    original_error = DocumentPersistenceError("synthetic add failure")

    validator = FakeUploadValidator(metadata, events)
    storage = ConfigurableUploadStorage(events)
    persistence = ConfigurableUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
        add_error=original_error,
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(DocumentUploadPersistenceError) as exc_info:
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=BytesIO(content),
        )

    assert exc_info.value.__cause__ is original_error
    assert persistence.rollback_calls == 1
    assert storage.delete_calls == 1
    assert persistence.commit_calls == 0


@pytest.mark.parametrize(
    ("persistence_error", "expected_error"),
    [
        (
            DuplicateDocumentPersistenceError("synthetic concurrent duplicate"),
            DuplicateDocumentError,
        ),
        (
            EvaluationReferencePersistenceError("synthetic concurrent evaluation removal"),
            EvaluationNotFoundError,
        ),
        (
            DocumentPersistenceError("synthetic generic commit failure"),
            DocumentUploadPersistenceError,
        ),
    ],
)
def test_commit_persistence_error_is_translated_and_compensated(
    persistence_error: DocumentPersistenceError,
    expected_error: type[DocumentUploadError],
) -> None:
    content = b"%PDF-1.7\nsynthetic commit failure\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)

    validator = FakeUploadValidator(metadata, events)
    storage = ConfigurableUploadStorage(events)
    persistence = ConfigurableUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
        commit_error=persistence_error,
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(expected_error) as exc_info:
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=BytesIO(content),
        )

    assert exc_info.value.__cause__ is persistence_error
    assert persistence.commit_calls == 1
    assert persistence.rollback_calls == 1
    assert storage.delete_calls == 1


@pytest.mark.parametrize(
    ("rollback_error", "delete_error", "delete_result"),
    [
        (
            DocumentPersistenceError("synthetic rollback failure"),
            None,
            True,
        ),
        (
            None,
            DocumentStorageError("synthetic delete failure"),
            True,
        ),
        (
            None,
            None,
            False,
        ),
        (
            DocumentPersistenceError("synthetic rollback failure"),
            DocumentStorageError("synthetic delete failure"),
            False,
        ),
    ],
    ids=[
        "rollback-failure",
        "delete-exception",
        "delete-false",
        "both-actions-fail",
    ],
)
def test_compensation_failure_returns_structured_error(
    rollback_error: Exception | None,
    delete_error: Exception | None,
    delete_result: bool,
) -> None:
    content = b"%PDF-1.7\nsynthetic compensation failure\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)
    original_error = DocumentPersistenceError("synthetic commit failure")

    validator = FakeUploadValidator(metadata, events)
    storage = ConfigurableUploadStorage(
        events,
        delete_error=delete_error,
        delete_result=delete_result,
    )
    persistence = ConfigurableUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
        commit_error=original_error,
        rollback_error=rollback_error,
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(DocumentCompensationError) as exc_info:
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=BytesIO(content),
        )

    error = exc_info.value

    assert error.__cause__ is original_error
    assert error.rollback_error is rollback_error
    assert error.delete_error is delete_error
    assert error.delete_result is (None if delete_error is not None else delete_result)
    assert persistence.rollback_calls == 1
    assert storage.delete_calls == 1
    assert str(error) == "document upload compensation failed"
    assert "synthetic" not in str(error)
    assert "evaluations/" not in str(error)
    assert ".pdf" not in str(error)


def test_storage_error_does_not_trigger_service_compensation() -> None:
    content = b"%PDF-1.7\nsynthetic storage failure\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)
    original_error = DocumentStorageError("synthetic storage failure")

    validator = FakeUploadValidator(metadata, events)
    storage = ConfigurableUploadStorage(
        events,
        store_error=original_error,
    )
    persistence = ConfigurableUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(DocumentStorageError) as exc_info:
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=BytesIO(content),
        )

    assert exc_info.value is original_error
    assert persistence.rollback_calls == 0
    assert storage.delete_calls == 0
    assert persistence.added_documents == []
    assert persistence.commit_calls == 0


def test_evaluation_lookup_persistence_error_is_translated_without_compensation() -> None:
    content = b"%PDF-1.7\nsynthetic lookup failure\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)
    original_error = DocumentPersistenceError("synthetic evaluation lookup failure")

    validator = FakeUploadValidator(metadata, events)
    storage = ConfigurableUploadStorage(events)
    persistence = ConfigurableUploadPersistence(
        events,
        evaluation_exists_error=original_error,
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(DocumentUploadPersistenceError) as exc_info:
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=BytesIO(content),
        )

    assert exc_info.value.__cause__ is original_error
    assert storage.store_calls == 0
    assert persistence.rollback_calls == 0


def test_duplicate_lookup_error_is_translated_without_compensation() -> None:
    content = b"%PDF-1.7\nsynthetic duplicate lookup\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)
    original_error = DuplicateDocumentPersistenceError("synthetic duplicate lookup failure")

    validator = FakeUploadValidator(metadata, events)
    storage = ConfigurableUploadStorage(events)
    persistence = ConfigurableUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
        duplicate_lookup_error=original_error,
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    with pytest.raises(DuplicateDocumentError) as exc_info:
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=BytesIO(content),
        )

    assert exc_info.value.__cause__ is original_error
    assert storage.store_calls == 0
    assert persistence.rollback_calls == 0


def test_rewind_failure_after_storage_is_compensated() -> None:
    content = b"%PDF-1.7\nsynthetic rewind failure\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)

    validator = FakeUploadValidator(metadata, events)
    storage = ConfigurableUploadStorage(events)
    persistence = ConfigurableUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )
    source = FailingRewindSource(content)

    with pytest.raises(NonSeekableDocumentError):
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=source,
        )

    assert persistence.rollback_calls == 1
    assert storage.delete_calls == 1
    assert source.closed is False


class InvalidStorageKeyUploadStorage(ConfigurableUploadStorage):
    def store(
        self,
        evaluation_id: UUID,
        document_id: UUID,
        source: BinaryIO,
    ) -> str:
        super().store(
            evaluation_id=evaluation_id,
            document_id=document_id,
            source=source,
        )

        return "../outside-private-storage.pdf"


def test_entity_creation_failure_triggers_compensation() -> None:
    content = b"%PDF-1.7\nsynthetic entity creation failure\n%%EOF"
    evaluation_id = uuid4()
    events: list[str] = []
    metadata = make_validated_metadata(content)

    validator = FakeUploadValidator(metadata, events)
    storage = InvalidStorageKeyUploadStorage(events)
    persistence = ConfigurableUploadPersistence(
        events,
        existing_evaluations={evaluation_id},
    )
    service = make_upload_service(
        validator=validator,
        storage=storage,
        persistence=persistence,
        events=events,
        document_id=uuid4(),
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )
    source = BytesIO(content)

    with pytest.raises(
        ValueError,
        match="parent directory segments",
    ):
        service.upload(
            evaluation_id=evaluation_id,
            original_filename=metadata.original_filename,
            declared_content_type=metadata.content_type,
            source=source,
        )

    assert storage.store_calls == 1
    assert persistence.rollback_calls == 1
    assert storage.delete_calls == 1
    assert persistence.added_documents == []
    assert persistence.commit_calls == 0
    assert source.closed is False
    assert source.tell() == 0
