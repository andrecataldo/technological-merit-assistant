from __future__ import annotations

import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from merit_assistant.api.dependencies import (
    DatabaseSession,
    get_document_upload_service,
)
from merit_assistant.api.main import app
from merit_assistant.application.services.document_upload import (
    DocumentUploadService,
)
from merit_assistant.application.services.document_validation import (
    DocumentValidationService,
)
from merit_assistant.infrastructure.db.document_persistence import (
    SqlAlchemyDocumentPersistence,
)
from merit_assistant.infrastructure.db.models import (
    DocumentModel,
    EvaluationModel,
    EvaluationProfileModel,
)
from merit_assistant.infrastructure.db.session import get_session_factory
from merit_assistant.infrastructure.pdf.pymupdf_inspector import (
    PyMuPdfInspector,
)
from merit_assistant.infrastructure.storage.local_document_storage import (
    LocalDocumentStorage,
)

PUBLIC_FIELDS = {
    "id",
    "evaluation_id",
    "original_filename",
    "content_type",
    "size_bytes",
    "created_at",
}


@dataclass(frozen=True, slots=True)
class IntegrationHarness:
    client: TestClient
    evaluation_id: UUID
    profile_id: str
    storage_root: Path
    pdf_content: bytes


def create_synthetic_pdf() -> bytes:
    """Create a valid one-page PDF entirely in memory."""
    with pymupdf.open() as document:  # type: ignore[no-untyped-call]
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Synthetic F01.5 API integration document",
        )
        return cast(bytes, document.tobytes())


def load_documents(evaluation_id: UUID) -> list[DocumentModel]:
    session = get_session_factory()()

    try:
        statement = (
            select(DocumentModel)
            .where(DocumentModel.evaluation_id == evaluation_id)
            .order_by(DocumentModel.created_at)
        )
        return list(session.scalars(statement))
    finally:
        session.close()


def stored_pdf_paths(storage_root: Path) -> list[Path]:
    if not storage_root.exists():
        return []

    return sorted(storage_root.rglob("*.pdf"))


@pytest.fixture
def integration_harness(
    tmp_path: Path,
) -> Iterator[IntegrationHarness]:
    session_factory = get_session_factory()
    setup_session = session_factory()

    profile_id = f"f01-5-api-integration-{uuid4().hex}"
    evaluation_id = uuid4()
    storage_root = tmp_path / "private-document-storage"
    pdf_content = create_synthetic_pdf()

    repository_root = Path(__file__).resolve().parents[1]

    assert not storage_root.resolve().is_relative_to(repository_root)

    previous_overrides = app.dependency_overrides.copy()

    try:
        setup_session.add(
            EvaluationProfileModel(
                id=profile_id,
                name="Synthetic F01.5 API integration profile",
                version="1.0",
                status="active",
            )
        )

        # The models intentionally have no ORM relationship. Flush the
        # parent row before inserting the evaluation that references it.
        setup_session.flush()

        setup_session.add(
            EvaluationModel(
                id=evaluation_id,
                title="Synthetic F01.5 API integration evaluation",
                profile_id=profile_id,
                created_at=datetime(2026, 7, 29, 20, 0, tzinfo=UTC),
            )
        )

        setup_session.commit()

        def override_document_upload_service(
            session: DatabaseSession,
        ) -> DocumentUploadService:
            validator = DocumentValidationService(
                inspector=PyMuPdfInspector(),
                max_size_bytes=5 * 1024 * 1024,
            )
            storage = LocalDocumentStorage(storage_root)
            persistence = SqlAlchemyDocumentPersistence(session)

            return DocumentUploadService(
                validator=validator,
                storage=storage,
                persistence=persistence,
            )

        app.dependency_overrides[get_document_upload_service] = override_document_upload_service

        with TestClient(app) as client:
            yield IntegrationHarness(
                client=client,
                evaluation_id=evaluation_id,
                profile_id=profile_id,
                storage_root=storage_root,
                pdf_content=pdf_content,
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

        setup_session.rollback()
        setup_session.close()

        cleanup_session = session_factory()

        try:
            cleanup_session.rollback()

            cleanup_session.execute(
                delete(DocumentModel).where(DocumentModel.evaluation_id == evaluation_id)
            )
            cleanup_session.execute(
                delete(EvaluationModel).where(EvaluationModel.id == evaluation_id)
            )
            cleanup_session.execute(
                delete(EvaluationProfileModel).where(EvaluationProfileModel.id == profile_id)
            )

            cleanup_session.commit()
        finally:
            cleanup_session.close()

        shutil.rmtree(storage_root, ignore_errors=True)

        verification_session = session_factory()

        try:
            assert (
                verification_session.get(
                    EvaluationModel,
                    evaluation_id,
                )
                is None
            )
            assert (
                verification_session.get(
                    EvaluationProfileModel,
                    profile_id,
                )
                is None
            )

            remaining_documents = list(
                verification_session.scalars(
                    select(DocumentModel.id).where(DocumentModel.evaluation_id == evaluation_id)
                )
            )

            assert remaining_documents == []
        finally:
            verification_session.close()

        assert not storage_root.exists()


def test_nominal_upload_persists_document_and_file(
    integration_harness: IntegrationHarness,
) -> None:
    harness = integration_harness
    filename = "synthetic-integration.pdf"

    response = harness.client.post(
        f"/evaluations/{harness.evaluation_id}/documents",
        files={
            "file": (
                filename,
                harness.pdf_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")

    payload = response.json()

    assert set(payload) == PUBLIC_FIELDS
    assert payload["evaluation_id"] == str(harness.evaluation_id)
    assert payload["original_filename"] == filename
    assert payload["content_type"] == "application/pdf"
    assert payload["size_bytes"] == len(harness.pdf_content)
    assert datetime.fromisoformat(payload["created_at"]).tzinfo is not None
    assert "storage_key" not in payload
    assert "sha256" not in payload

    document_id = UUID(payload["id"])
    documents = load_documents(harness.evaluation_id)

    assert len(documents) == 1

    stored_document = documents[0]
    expected_sha256 = sha256(harness.pdf_content).hexdigest()
    expected_storage_key = LocalDocumentStorage.build_storage_key(
        harness.evaluation_id,
        document_id,
    )

    assert stored_document.id == document_id
    assert stored_document.evaluation_id == harness.evaluation_id
    assert stored_document.original_filename == filename
    assert stored_document.content_type == "application/pdf"
    assert stored_document.size_bytes == len(harness.pdf_content)
    assert stored_document.sha256 == expected_sha256
    assert stored_document.storage_key == expected_storage_key

    stored_path = harness.storage_root.joinpath(*expected_storage_key.split("/"))

    assert stored_path.is_file()
    assert stored_path.name == f"{document_id}.pdf"
    assert stored_path.read_bytes() == harness.pdf_content
    assert stored_pdf_paths(harness.storage_root) == [stored_path]
    assert list(harness.storage_root.rglob("*.tmp")) == []

    for forbidden_value in (
        stored_document.storage_key,
        stored_document.sha256,
        str(harness.storage_root),
    ):
        assert forbidden_value not in response.text


def test_duplicate_upload_returns_409_and_preserves_single_copy(
    integration_harness: IntegrationHarness,
) -> None:
    harness = integration_harness
    request_files = {
        "file": (
            "duplicate-synthetic.pdf",
            harness.pdf_content,
            "application/pdf",
        )
    }

    first_response = harness.client.post(
        f"/evaluations/{harness.evaluation_id}/documents",
        files=request_files,
    )
    second_response = harness.client.post(
        f"/evaluations/{harness.evaluation_id}/documents",
        files=request_files,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "Documento já associado à avaliação."}

    documents = load_documents(harness.evaluation_id)
    stored_files = stored_pdf_paths(harness.storage_root)

    assert len(documents) == 1
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == harness.pdf_content
    assert list(harness.storage_root.rglob("*.tmp")) == []

    for forbidden_value in (
        documents[0].sha256,
        documents[0].storage_key,
        "uq_documents_evaluation_sha256",
        "constraint",
    ):
        assert forbidden_value not in second_response.text


def test_missing_evaluation_returns_404_without_side_effects(
    integration_harness: IntegrationHarness,
) -> None:
    harness = integration_harness
    missing_evaluation_id = uuid4()

    response = harness.client.post(
        f"/evaluations/{missing_evaluation_id}/documents",
        files={
            "file": (
                "missing-evaluation.pdf",
                harness.pdf_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Avaliação não encontrada."}
    assert load_documents(missing_evaluation_id) == []
    assert load_documents(harness.evaluation_id) == []
    assert stored_pdf_paths(harness.storage_root) == []
    assert list(harness.storage_root.rglob("*.tmp")) == []


def test_invalid_pdf_returns_422_without_side_effects(
    integration_harness: IntegrationHarness,
) -> None:
    harness = integration_harness
    invalid_content = b"synthetic content that is not a PDF"

    response = harness.client.post(
        f"/evaluations/{harness.evaluation_id}/documents",
        files={
            "file": (
                "invalid-synthetic.pdf",
                invalid_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "O arquivo enviado não é um PDF válido."}
    assert load_documents(harness.evaluation_id) == []
    assert stored_pdf_paths(harness.storage_root) == []
    assert invalid_content.decode() not in response.text
    assert list(harness.storage_root.rglob("*.tmp")) == []


def test_unsupported_content_type_returns_415_without_side_effects(
    integration_harness: IntegrationHarness,
) -> None:
    harness = integration_harness

    response = harness.client.post(
        f"/evaluations/{harness.evaluation_id}/documents",
        files={
            "file": (
                "synthetic-content-type.pdf",
                harness.pdf_content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 415
    assert response.json() == {"detail": "Tipo de conteúdo não suportado."}
    assert load_documents(harness.evaluation_id) == []
    assert stored_pdf_paths(harness.storage_root) == []
    assert list(harness.storage_root.rglob("*.tmp")) == []
