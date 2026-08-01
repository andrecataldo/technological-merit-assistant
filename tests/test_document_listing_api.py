from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import merit_assistant.api.dependencies as dependencies_module
from merit_assistant.api.dependencies import (
    get_document_listing_service,
)
from merit_assistant.api.main import app
from merit_assistant.api.routes.documents import (
    list_documents,
)
from merit_assistant.application.services.document_listing import (
    DocumentListingEvaluationNotFoundError,
    DocumentListingPersistenceError,
    DocumentListingService,
)
from merit_assistant.domain.entities import Document
from merit_assistant.infrastructure.db.document_persistence import (
    SqlAlchemyDocumentPersistence,
)

PUBLIC_FIELDS = {
    "id",
    "evaluation_id",
    "original_filename",
    "content_type",
    "size_bytes",
    "created_at",
}

INTERNAL_DETAIL = "INTERNAL_SECRET storage_key sha256 /private/evaluations/document.pdf constraint"


def make_document(
    *,
    evaluation_id: UUID,
    original_filename: str,
    created_at: datetime,
) -> Document:
    document_id = uuid4()

    return Document(
        id=document_id,
        evaluation_id=evaluation_id,
        original_filename=original_filename,
        storage_key=(f"evaluations/{evaluation_id}/documents/{document_id}.pdf"),
        content_type="application/pdf",
        size_bytes=2048,
        sha256="a" * 64,
        created_at=created_at,
    )


class FakeDocumentListingService:
    def __init__(
        self,
        *,
        result: Sequence[Document] = (),
        error: Exception | None = None,
    ) -> None:
        self.result = tuple(result)
        self.error = error
        self.calls: list[UUID] = []

    def list_for_evaluation(
        self,
        evaluation_id: UUID,
    ) -> Sequence[Document]:
        self.calls.append(evaluation_id)

        if self.error is not None:
            raise self.error

        return self.result


@contextmanager
def client_for(
    service: FakeDocumentListingService,
) -> Iterator[TestClient]:
    previous_overrides = app.dependency_overrides.copy()

    def override_service() -> FakeDocumentListingService:
        return service

    app.dependency_overrides[get_document_listing_service] = override_service

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def test_endpoint_maps_documents_and_preserves_order() -> None:
    evaluation_id = uuid4()

    first_document = make_document(
        evaluation_id=evaluation_id,
        original_filename="primeiro.pdf",
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
        original_filename="segundo.pdf",
        created_at=datetime(
            2026,
            7,
            30,
            19,
            0,
            tzinfo=UTC,
        ),
    )

    service = FakeDocumentListingService(
        result=(
            first_document,
            second_document,
        )
    )

    response = list_documents(
        evaluation_id=evaluation_id,
        service=service,
    )

    assert service.calls == [evaluation_id]
    assert [item.id for item in response] == [
        first_document.id,
        second_document.id,
    ]

    for item in response:
        assert set(item.model_dump()) == PUBLIC_FIELDS


def test_existing_evaluation_without_documents_returns_empty_list() -> None:
    evaluation_id = uuid4()
    service = FakeDocumentListingService()

    with client_for(service) as client:
        response = client.get(f"/evaluations/{evaluation_id}/documents")

    assert response.status_code == 200
    assert response.json() == []
    assert service.calls == [evaluation_id]


def test_http_response_contains_only_public_fields_in_order() -> None:
    evaluation_id = uuid4()

    first_document = make_document(
        evaluation_id=evaluation_id,
        original_filename="primeiro.pdf",
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
        original_filename="segundo.pdf",
        created_at=datetime(
            2026,
            7,
            30,
            19,
            0,
            tzinfo=UTC,
        ),
    )

    service = FakeDocumentListingService(
        result=(
            first_document,
            second_document,
        )
    )

    with client_for(service) as client:
        response = client.get(f"/evaluations/{evaluation_id}/documents")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    payload = response.json()

    assert [item["id"] for item in payload] == [
        str(first_document.id),
        str(second_document.id),
    ]

    for item in payload:
        assert set(item) == PUBLIC_FIELDS

        for forbidden_field in (
            "storage_key",
            "sha256",
            "path",
            "content",
        ):
            assert forbidden_field not in item

    assert service.calls == [evaluation_id]


def test_invalid_evaluation_uuid_returns_422_without_service_call() -> None:
    service = FakeDocumentListingService()

    with client_for(service) as client:
        response = client.get("/evaluations/not-a-uuid/documents")

    assert response.status_code == 422
    assert service.calls == []


def test_missing_evaluation_returns_sanitized_404() -> None:
    service = FakeDocumentListingService(
        error=DocumentListingEvaluationNotFoundError(INTERNAL_DETAIL)
    )

    with client_for(service) as client:
        response = client.get(f"/evaluations/{uuid4()}/documents")

    assert response.status_code == 404
    assert response.json() == {"detail": "Evaluation not found."}
    assert len(service.calls) == 1
    assert "INTERNAL_SECRET" not in response.text
    assert "storage_key" not in response.text
    assert "sha256" not in response.text
    assert "/private/" not in response.text
    assert "constraint" not in response.text


def test_persistence_failure_returns_sanitized_500() -> None:
    service = FakeDocumentListingService(error=DocumentListingPersistenceError(INTERNAL_DETAIL))

    with client_for(service) as client:
        response = client.get(f"/evaluations/{uuid4()}/documents")

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to list documents."}
    assert len(service.calls) == 1
    assert "INTERNAL_SECRET" not in response.text
    assert "storage_key" not in response.text
    assert "sha256" not in response.text
    assert "/private/" not in response.text
    assert "constraint" not in response.text


def test_unknown_exception_is_not_captured_generically() -> None:
    evaluation_id = uuid4()
    service = FakeDocumentListingService(error=RuntimeError("synthetic unknown listing failure"))

    with pytest.raises(
        RuntimeError,
        match="synthetic unknown listing failure",
    ):
        list_documents(
            evaluation_id=evaluation_id,
            service=service,
        )

    assert service.calls == [evaluation_id]


def test_listing_dependency_is_created_per_call_without_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_settings() -> None:
        raise AssertionError("A listagem não deve consultar settings.")

    monkeypatch.setattr(
        dependencies_module,
        "get_settings",
        forbidden_settings,
    )

    session = MagicMock(spec=Session)

    first = get_document_listing_service(session)
    second = get_document_listing_service(session)

    assert isinstance(first, DocumentListingService)
    assert isinstance(second, DocumentListingService)
    assert first is not second

    first_persistence = first._persistence
    second_persistence = second._persistence

    assert isinstance(
        first_persistence,
        SqlAlchemyDocumentPersistence,
    )
    assert isinstance(
        second_persistence,
        SqlAlchemyDocumentPersistence,
    )
    assert first_persistence is not second_persistence
    assert first_persistence._session is session
    assert second_persistence._session is session

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_not_called()


def test_openapi_declares_safe_get_and_preserves_post() -> None:
    schema = app.openapi()
    path = "/evaluations/{evaluation_id}/documents"

    operations = schema["paths"][path]
    get_operation = operations["get"]
    post_operation = operations["post"]

    assert set(operations) == {"get", "post"}

    assert "requestBody" not in get_operation
    assert "200" in get_operation["responses"]

    get_schema = get_operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert get_schema["type"] == "array"
    assert get_schema["items"]["$ref"] == ("#/components/schemas/DocumentUploadResponse")

    assert "requestBody" in post_operation
    assert "201" in post_operation["responses"]
    assert "multipart/form-data" in post_operation["requestBody"]["content"]

    public_schema = schema["components"]["schemas"]["DocumentUploadResponse"]

    assert set(public_schema["properties"]) == PUBLIC_FIELDS
    assert "storage_key" not in public_schema["properties"]
    assert "sha256" not in public_schema["properties"]
