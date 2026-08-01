from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from merit_assistant.api.dependencies import (
    get_document_upload_service,
)
from merit_assistant.api.main import app
from merit_assistant.api.routes.documents import upload_document
from merit_assistant.application.ports.document_storage import (
    DocumentStorageError,
)
from merit_assistant.application.services.document_upload import (
    DocumentCompensationError,
    DocumentUploadPersistenceError,
    DocumentUploadService,
    DuplicateDocumentError,
    EvaluationNotFoundError,
    OriginalFilenameTooLongError,
    StoredContentMismatchError,
)
from merit_assistant.application.services.document_validation import (
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidOriginalFilenameError,
    InvalidPdfError,
    NonSeekableDocumentError,
    UnsupportedContentTypeError,
)
from merit_assistant.config.settings import get_settings
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


def _document(*, evaluation_id: UUID | None = None) -> Document:
    document_id = uuid4()
    target_evaluation_id = evaluation_id or uuid4()

    return Document(
        id=document_id,
        evaluation_id=target_evaluation_id,
        original_filename="documento-sintetico.pdf",
        storage_key=(f"evaluations/{target_evaluation_id}/documents/{document_id}.pdf"),
        content_type="application/pdf",
        size_bytes=128,
        sha256="a" * 64,
        created_at=datetime(2026, 7, 29, 20, 0, tzinfo=UTC),
    )


class FakeDocumentUploadService:
    def __init__(
        self,
        *,
        result: Document | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or _document()
        self.error = error
        self.calls: list[dict[str, object]] = []

    def upload(
        self,
        evaluation_id: UUID,
        original_filename: str,
        declared_content_type: str | None,
        source: BinaryIO,
    ) -> Document:
        self.calls.append(
            {
                "evaluation_id": evaluation_id,
                "original_filename": original_filename,
                "declared_content_type": declared_content_type,
                "source": source,
            }
        )

        if self.error is not None:
            raise self.error

        return self.result


class ReadForbiddenStream(BytesIO):
    def read(self, size: int = -1) -> bytes:
        raise AssertionError("A camada HTTP não deve ler o stream do upload.")


def _upload_file(
    stream: BinaryIO,
    *,
    filename: str | None = "documento-sintetico.pdf",
) -> UploadFile:
    return UploadFile(
        file=stream,
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )


@contextmanager
def _client_for(
    service: FakeDocumentUploadService,
) -> Iterator[TestClient]:
    previous_overrides = app.dependency_overrides.copy()

    def override_service() -> FakeDocumentUploadService:
        return service

    app.dependency_overrides[get_document_upload_service] = override_service

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def test_endpoint_passes_original_stream_without_reading_or_closing() -> None:
    evaluation_id = uuid4()
    stream = ReadForbiddenStream(b"conteudo-sintetico")
    upload_file = _upload_file(stream)
    document = _document(evaluation_id=evaluation_id)
    service = FakeDocumentUploadService(result=document)

    response = upload_document(
        evaluation_id=evaluation_id,
        file=upload_file,
        service=service,
    )

    assert len(service.calls) == 1
    assert service.calls[0] == {
        "evaluation_id": evaluation_id,
        "original_filename": "documento-sintetico.pdf",
        "declared_content_type": "application/pdf",
        "source": stream,
    }
    assert set(response.model_dump()) == PUBLIC_FIELDS
    assert not stream.closed


@pytest.mark.parametrize("filename", [None, "", "   "])
def test_endpoint_rejects_missing_filename_before_service(
    filename: str | None,
) -> None:
    stream = BytesIO(b"conteudo-sintetico")
    upload_file = _upload_file(stream, filename=filename)
    service = FakeDocumentUploadService()

    with pytest.raises(HTTPException) as captured:
        upload_document(
            evaluation_id=uuid4(),
            file=upload_file,
            service=service,
        )

    assert captured.value.status_code == 422
    assert captured.value.detail == "Nome de arquivo inválido."
    assert service.calls == []
    assert not stream.closed


def test_successful_http_upload_returns_only_public_fields() -> None:
    evaluation_id = uuid4()
    document = _document(evaluation_id=evaluation_id)
    service = FakeDocumentUploadService(result=document)

    with _client_for(service) as client:
        response = client.post(
            f"/evaluations/{evaluation_id}/documents",
            files={
                "file": (
                    "documento-sintetico.pdf",
                    b"conteudo-nao-lido-pelo-endpoint",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")

    payload = response.json()

    assert set(payload) == PUBLIC_FIELDS
    assert payload["id"] == str(document.id)
    assert payload["evaluation_id"] == str(evaluation_id)
    assert payload["original_filename"] == document.original_filename
    assert payload["content_type"] == "application/pdf"
    assert payload["size_bytes"] == document.size_bytes
    assert "storage_key" not in payload
    assert "sha256" not in payload

    assert len(service.calls) == 1
    assert service.calls[0]["evaluation_id"] == evaluation_id
    assert service.calls[0]["original_filename"] == "documento-sintetico.pdf"
    assert service.calls[0]["declared_content_type"] == "application/pdf"


def test_missing_multipart_field_returns_422_without_service_call() -> None:
    service = FakeDocumentUploadService()

    with _client_for(service) as client:
        response = client.post(f"/evaluations/{uuid4()}/documents")

    assert response.status_code == 422
    assert service.calls == []


def test_invalid_evaluation_uuid_returns_422_without_service_call() -> None:
    service = FakeDocumentUploadService()

    with _client_for(service) as client:
        response = client.post(
            "/evaluations/not-a-uuid/documents",
            files={
                "file": (
                    "documento.pdf",
                    b"conteudo",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 422
    assert service.calls == []


def test_whitespace_http_filename_is_rejected_before_service() -> None:
    service = FakeDocumentUploadService()

    with _client_for(service) as client:
        response = client.post(
            f"/evaluations/{uuid4()}/documents",
            files={
                "file": (
                    "   ",
                    b"conteudo",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Nome de arquivo inválido."}
    assert service.calls == []


@pytest.mark.parametrize(
    ("error_type", "expected_status", "expected_detail"),
    [
        pytest.param(
            InvalidOriginalFilenameError,
            422,
            "Nome de arquivo inválido.",
            id="invalid-filename",
        ),
        pytest.param(
            OriginalFilenameTooLongError,
            422,
            "Nome de arquivo inválido.",
            id="filename-too-long",
        ),
        pytest.param(
            EmptyDocumentError,
            422,
            "O documento está vazio.",
            id="empty-document",
        ),
        pytest.param(
            InvalidPdfError,
            422,
            "O arquivo enviado não é um PDF válido.",
            id="invalid-pdf",
        ),
        pytest.param(
            NonSeekableDocumentError,
            422,
            "Não foi possível processar o arquivo enviado.",
            id="non-seekable",
        ),
        pytest.param(
            UnsupportedContentTypeError,
            415,
            "Tipo de conteúdo não suportado.",
            id="unsupported-content-type",
        ),
        pytest.param(
            DocumentTooLargeError,
            413,
            "O documento excede o limite permitido.",
            id="too-large",
        ),
        pytest.param(
            EvaluationNotFoundError,
            404,
            "Avaliação não encontrada.",
            id="evaluation-not-found",
        ),
        pytest.param(
            DuplicateDocumentError,
            409,
            "Documento já associado à avaliação.",
            id="duplicate",
        ),
        pytest.param(
            StoredContentMismatchError,
            500,
            "Não foi possível concluir o upload do documento.",
            id="stored-content-mismatch",
        ),
        pytest.param(
            DocumentUploadPersistenceError,
            500,
            "Não foi possível concluir o upload do documento.",
            id="persistence",
        ),
        pytest.param(
            DocumentCompensationError,
            500,
            "Não foi possível concluir o upload do documento.",
            id="compensation",
        ),
        pytest.param(
            DocumentStorageError,
            500,
            "Não foi possível concluir o upload do documento.",
            id="storage",
        ),
        pytest.param(
            OSError,
            500,
            "Não foi possível concluir o upload do documento.",
            id="operating-system",
        ),
    ],
)
def test_known_errors_are_translated_and_sanitized(
    error_type: type[Exception],
    expected_status: int,
    expected_detail: str,
) -> None:
    service = FakeDocumentUploadService(error=error_type(INTERNAL_DETAIL))

    with _client_for(service) as client:
        response = client.post(
            f"/evaluations/{uuid4()}/documents",
            files={
                "file": (
                    "documento.pdf",
                    b"conteudo",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert len(service.calls) == 1

    response_text = response.text

    for forbidden_value in (
        "INTERNAL_SECRET",
        "storage_key",
        "sha256",
        "/private/",
        "constraint",
    ):
        assert forbidden_value not in response_text


def test_unknown_exception_is_not_captured_generically() -> None:
    service = FakeDocumentUploadService(error=RuntimeError("erro inesperado"))
    stream = BytesIO(b"conteudo")

    with pytest.raises(RuntimeError, match="erro inesperado"):
        upload_document(
            evaluation_id=uuid4(),
            file=_upload_file(stream),
            service=service,
        )

    assert len(service.calls) == 1
    assert not stream.closed


def test_service_dependency_is_created_per_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary_root = tmp_path / "private"
    monkeypatch.setenv("PRIVATE_DATA_DIR", str(temporary_root))
    get_settings.cache_clear()

    try:
        session = MagicMock(spec=Session)

        first = get_document_upload_service(session)
        second = get_document_upload_service(session)

        assert isinstance(first, DocumentUploadService)
        assert isinstance(second, DocumentUploadService)
        assert first is not second

        persistence = first._persistence

        assert isinstance(
            persistence,
            SqlAlchemyDocumentPersistence,
        )
        assert persistence._session is session

        session.commit.assert_not_called()
        session.rollback.assert_not_called()
        session.close.assert_not_called()
    finally:
        get_settings.cache_clear()


def test_openapi_declares_multipart_post_and_public_schema() -> None:
    schema = app.openapi()
    path = "/evaluations/{evaluation_id}/documents"

    operation = schema["paths"][path]["post"]
    request_content = operation["requestBody"]["content"]
    response_schema = schema["components"]["schemas"]["DocumentUploadResponse"]

    assert set(schema["paths"][path]) == {"get", "post"}
    assert "multipart/form-data" in request_content
    assert "201" in operation["responses"]
    assert set(response_schema["properties"]) == PUBLIC_FIELDS
    assert "storage_key" not in response_schema["properties"]
    assert "sha256" not in response_schema["properties"]
