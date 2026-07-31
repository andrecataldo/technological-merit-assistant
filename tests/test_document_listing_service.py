from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from merit_assistant.application.ports.document_persistence import (
    DocumentPersistence,
    DocumentPersistenceError,
)
from merit_assistant.application.services.document_listing import (
    DocumentListingError,
    DocumentListingEvaluationNotFoundError,
    DocumentListingPersistenceError,
    DocumentListingService,
)
from merit_assistant.domain.entities import Document


class FakeDocumentPersistence:
    def __init__(
        self,
        *,
        existing_evaluations: set[UUID] | None = None,
        documents: dict[UUID, tuple[Document, ...]] | None = None,
        evaluation_error: Exception | None = None,
        listing_error: Exception | None = None,
    ) -> None:
        self.existing_evaluations = set(existing_evaluations or ())
        self.documents = dict(documents or {})
        self.evaluation_error = evaluation_error
        self.listing_error = listing_error

        self.evaluation_exists_ids: list[UUID] = []
        self.list_by_evaluation_ids: list[UUID] = []
        self.added_documents: list[Document] = []

        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def evaluation_exists(
        self,
        evaluation_id: UUID,
    ) -> bool:
        self.evaluation_exists_ids.append(evaluation_id)

        if self.evaluation_error is not None:
            raise self.evaluation_error

        return evaluation_id in self.existing_evaluations

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256: str,
    ) -> bool:
        del evaluation_id
        del sha256
        return False

    def list_by_evaluation(
        self,
        evaluation_id: UUID,
    ) -> tuple[Document, ...]:
        self.list_by_evaluation_ids.append(evaluation_id)

        if self.listing_error is not None:
            raise self.listing_error

        return self.documents.get(evaluation_id, ())

    def add(self, document: Document) -> None:
        self.added_documents.append(document)

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1


def make_service(
    persistence: FakeDocumentPersistence,
) -> DocumentListingService:
    return DocumentListingService(
        persistence=cast(
            DocumentPersistence,
            persistence,
        )
    )


def make_document(
    *,
    evaluation_id: UUID,
    created_at: datetime,
) -> Document:
    document_id = uuid4()

    return Document(
        id=document_id,
        evaluation_id=evaluation_id,
        original_filename="synthetic-document.pdf",
        storage_key=(f"evaluations/{evaluation_id}/documents/{document_id}.pdf"),
        content_type="application/pdf",
        size_bytes=2048,
        sha256="a" * 64,
        created_at=created_at,
    )


@pytest.mark.parametrize(
    "error_type",
    [
        DocumentListingEvaluationNotFoundError,
        DocumentListingPersistenceError,
    ],
)
def test_listing_errors_share_the_approved_base_type(
    error_type: type[DocumentListingError],
) -> None:
    assert issubclass(
        error_type,
        DocumentListingError,
    )


def test_missing_evaluation_raises_before_listing() -> None:
    evaluation_id = uuid4()
    persistence = FakeDocumentPersistence()
    service = make_service(persistence)

    with pytest.raises(
        DocumentListingEvaluationNotFoundError,
        match="target evaluation does not exist",
    ):
        service.list_for_evaluation(evaluation_id)

    assert persistence.evaluation_exists_ids == [evaluation_id]
    assert persistence.list_by_evaluation_ids == []


def test_existing_evaluation_without_documents_returns_empty_tuple() -> None:
    evaluation_id = uuid4()
    persistence = FakeDocumentPersistence(
        existing_evaluations={evaluation_id},
    )
    service = make_service(persistence)

    result = service.list_for_evaluation(evaluation_id)

    assert result == ()
    assert persistence.evaluation_exists_ids == [evaluation_id]
    assert persistence.list_by_evaluation_ids == [evaluation_id]


def test_documents_are_returned_in_persistence_order() -> None:
    evaluation_id = uuid4()

    first_document = make_document(
        evaluation_id=evaluation_id,
        created_at=datetime(
            2026,
            7,
            30,
            18,
            0,
            tzinfo=UTC,
        ),
    )
    second_document = make_document(
        evaluation_id=evaluation_id,
        created_at=datetime(
            2026,
            7,
            30,
            19,
            0,
            tzinfo=UTC,
        ),
    )

    persistence = FakeDocumentPersistence(
        existing_evaluations={evaluation_id},
        documents={
            evaluation_id: (
                first_document,
                second_document,
            )
        },
    )
    service = make_service(persistence)

    result = service.list_for_evaluation(evaluation_id)

    assert result == (
        first_document,
        second_document,
    )
    assert persistence.evaluation_exists_ids == [evaluation_id]
    assert persistence.list_by_evaluation_ids == [evaluation_id]


def test_evaluation_lookup_error_is_translated_and_preserves_cause() -> None:
    evaluation_id = uuid4()
    original_error = DocumentPersistenceError("synthetic evaluation lookup failure")
    persistence = FakeDocumentPersistence(
        evaluation_error=original_error,
    )
    service = make_service(persistence)

    with pytest.raises(
        DocumentListingPersistenceError,
        match="document listing persistence operation failed",
    ) as exc_info:
        service.list_for_evaluation(evaluation_id)

    assert exc_info.value.__cause__ is original_error
    assert persistence.evaluation_exists_ids == [evaluation_id]
    assert persistence.list_by_evaluation_ids == []


def test_document_query_error_is_translated_and_preserves_cause() -> None:
    evaluation_id = uuid4()
    original_error = DocumentPersistenceError("synthetic document listing failure")
    persistence = FakeDocumentPersistence(
        existing_evaluations={evaluation_id},
        listing_error=original_error,
    )
    service = make_service(persistence)

    with pytest.raises(
        DocumentListingPersistenceError,
        match="document listing persistence operation failed",
    ) as exc_info:
        service.list_for_evaluation(evaluation_id)

    assert exc_info.value.__cause__ is original_error
    assert persistence.evaluation_exists_ids == [evaluation_id]
    assert persistence.list_by_evaluation_ids == [evaluation_id]


def test_unknown_evaluation_lookup_error_is_not_hidden() -> None:
    evaluation_id = uuid4()
    persistence = FakeDocumentPersistence(
        evaluation_error=RuntimeError("synthetic unknown evaluation error"),
    )
    service = make_service(persistence)

    with pytest.raises(
        RuntimeError,
        match="synthetic unknown evaluation error",
    ):
        service.list_for_evaluation(evaluation_id)


def test_unknown_document_query_error_is_not_hidden() -> None:
    evaluation_id = uuid4()
    persistence = FakeDocumentPersistence(
        existing_evaluations={evaluation_id},
        listing_error=RuntimeError("synthetic unknown listing error"),
    )
    service = make_service(persistence)

    with pytest.raises(
        RuntimeError,
        match="synthetic unknown listing error",
    ):
        service.list_for_evaluation(evaluation_id)


def test_service_does_not_control_persistence_transaction() -> None:
    evaluation_id = uuid4()
    persistence = FakeDocumentPersistence(
        existing_evaluations={evaluation_id},
    )
    service = make_service(persistence)

    service.list_for_evaluation(evaluation_id)

    assert persistence.commit_calls == 0
    assert persistence.rollback_calls == 0
    assert persistence.close_calls == 0
    assert persistence.added_documents == []
