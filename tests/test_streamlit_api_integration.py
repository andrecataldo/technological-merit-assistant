from __future__ import annotations

import shutil
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from merit_assistant.api.dependencies import (  # noqa: E402
    DatabaseSession,
    get_document_upload_service,
)
from merit_assistant.api.main import (  # noqa: E402
    app,
    configured_profile,
)
from merit_assistant.application.services.document_upload import (  # noqa: E402
    DocumentUploadService,
)
from merit_assistant.application.services.document_validation import (  # noqa: E402
    DocumentValidationService,
)
from merit_assistant.infrastructure.db.document_persistence import (  # noqa: E402
    SqlAlchemyDocumentPersistence,
)
from merit_assistant.infrastructure.db.models import (  # noqa: E402
    DocumentModel,
    EvaluationModel,
    EvaluationProfileModel,
)
from merit_assistant.infrastructure.db.session import (  # noqa: E402
    get_session_factory,
)
from merit_assistant.infrastructure.pdf.pymupdf_inspector import (  # noqa: E402
    PyMuPdfInspector,
)
from merit_assistant.infrastructure.storage.local_document_storage import (  # noqa: E402
    LocalDocumentStorage,
)
from ui.api_client import (  # noqa: E402
    ApiOperationError,
    MeritAssistantApiClient,
)

PUBLIC_DOCUMENT_FIELDS = {
    "id",
    "evaluation_id",
    "original_filename",
    "content_type",
    "size_bytes",
    "created_at",
}


@dataclass(slots=True)
class IntegrationHarness:
    client: MeritAssistantApiClient
    storage_root: Path
    pdf_content: bytes
    profile_id: str
    title_prefix: str


def create_synthetic_pdf() -> bytes:
    """Create a valid one-page PDF entirely in memory."""

    with pymupdf.open() as document:  # type: ignore[no-untyped-call]
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Synthetic F01.7 Streamlit API integration document",
        )
        return cast(bytes, document.tobytes())


def private_file_snapshot(private_root: Path) -> frozenset[str]:
    if not private_root.exists():
        return frozenset()

    return frozenset(
        path.relative_to(private_root).as_posix()
        for path in private_root.rglob("*")
        if path.is_file()
    )


def evaluation_ids_for_prefix(title_prefix: str) -> list[UUID]:
    session = get_session_factory()()

    try:
        statement = select(EvaluationModel.id).where(EvaluationModel.title.startswith(title_prefix))
        return list(session.scalars(statement))
    finally:
        session.close()


def document_count(evaluation_id: UUID) -> int:
    session = get_session_factory()()

    try:
        statement = select(DocumentModel.id).where(DocumentModel.evaluation_id == evaluation_id)
        return len(list(session.scalars(statement)))
    finally:
        session.close()


@pytest.fixture
def integration_harness(
    tmp_path: Path,
) -> Iterator[IntegrationHarness]:
    session_factory = get_session_factory()
    profile_id = configured_profile().id
    title_prefix = f"F01.7 UI integration {uuid4().hex}"
    storage_root = tmp_path / "private-document-storage"
    pdf_content = create_synthetic_pdf()

    repository_root = Path(__file__).resolve().parents[1]
    private_root = repository_root / "data" / "private"
    private_files_before = private_file_snapshot(private_root)

    assert not storage_root.resolve().is_relative_to(repository_root)

    inspection_session = session_factory()

    try:
        profile_was_present = (
            inspection_session.get(
                EvaluationProfileModel,
                profile_id,
            )
            is not None
        )
    finally:
        inspection_session.close()

    previous_overrides = app.dependency_overrides.copy()

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

    try:
        with TestClient(
            app,
            base_url="http://localhost:8000",
            follow_redirects=False,
        ) as transport:
            client = MeritAssistantApiClient(
                "http://localhost:8000",
                http_client=transport,
            )
            yield IntegrationHarness(
                client=client,
                storage_root=storage_root,
                pdf_content=pdf_content,
                profile_id=profile_id,
                title_prefix=title_prefix,
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

        cleanup_session = session_factory()

        try:
            evaluation_ids = list(
                cleanup_session.scalars(
                    select(EvaluationModel.id).where(EvaluationModel.title.startswith(title_prefix))
                )
            )

            if evaluation_ids:
                cleanup_session.execute(
                    delete(DocumentModel).where(DocumentModel.evaluation_id.in_(evaluation_ids))
                )
                cleanup_session.execute(
                    delete(EvaluationModel).where(EvaluationModel.id.in_(evaluation_ids))
                )

            if not profile_was_present:
                cleanup_session.execute(
                    delete(EvaluationProfileModel).where(EvaluationProfileModel.id == profile_id)
                )

            cleanup_session.commit()
        finally:
            cleanup_session.close()

        shutil.rmtree(storage_root, ignore_errors=True)

        verification_session = session_factory()

        try:
            remaining_evaluations = list(
                verification_session.scalars(
                    select(EvaluationModel.id).where(EvaluationModel.title.startswith(title_prefix))
                )
            )
            assert remaining_evaluations == []

            profile_is_present = (
                verification_session.get(
                    EvaluationProfileModel,
                    profile_id,
                )
                is not None
            )
            assert profile_is_present is profile_was_present
        finally:
            verification_session.close()

        assert not storage_root.exists()
        assert private_file_snapshot(private_root) == private_files_before


def test_ui_client_completes_the_real_document_journey(
    integration_harness: IntegrationHarness,
) -> None:
    harness = integration_harness
    client = harness.client

    health = client.health()
    profiles = client.list_profiles()

    assert health.status == "ok"
    assert health.external_processing_enabled is False
    assert [profile.id for profile in profiles] == [harness.profile_id]

    first_evaluation = client.create_evaluation(
        title=f"{harness.title_prefix} first",
        profile_id=harness.profile_id,
    )
    second_evaluation = client.create_evaluation(
        title=f"{harness.title_prefix} second",
        profile_id=harness.profile_id,
    )

    evaluations = client.list_evaluations()
    evaluation_ids = {evaluation.id for evaluation in evaluations}

    assert first_evaluation.id in evaluation_ids
    assert second_evaluation.id in evaluation_ids
    assert client.list_documents(first_evaluation.id) == []
    assert client.list_documents(second_evaluation.id) == []

    filename = "f01-7-ui-integration.pdf"
    uploaded = client.upload_document(
        evaluation_id=first_evaluation.id,
        filename=filename,
        content_type="application/pdf",
        source=BytesIO(harness.pdf_content),
    )

    assert set(uploaded.model_dump()) == PUBLIC_DOCUMENT_FIELDS
    assert uploaded.evaluation_id == first_evaluation.id
    assert uploaded.original_filename == filename
    assert uploaded.content_type == "application/pdf"
    assert uploaded.size_bytes == len(harness.pdf_content)

    listed = client.list_documents(first_evaluation.id)

    assert listed == [uploaded]
    assert set(listed[0].model_dump()) == PUBLIC_DOCUMENT_FIELDS
    assert client.list_documents(second_evaluation.id) == []
    assert document_count(first_evaluation.id) == 1
    assert document_count(second_evaluation.id) == 0

    stored_files = sorted(harness.storage_root.rglob("*.pdf"))

    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == harness.pdf_content
    assert list(harness.storage_root.rglob("*.tmp")) == []

    with pytest.raises(ApiOperationError) as captured:
        client.upload_document(
            evaluation_id=first_evaluation.id,
            filename=filename,
            content_type="application/pdf",
            source=BytesIO(harness.pdf_content),
        )

    assert captured.value.public_message == ("Documento já associado à avaliação.")
    assert str(captured.value) == "Documento já associado à avaliação."
    assert "constraint" not in str(captured.value).lower()
    assert "storage" not in str(captured.value).lower()
    assert document_count(first_evaluation.id) == 1
    assert len(list(harness.storage_root.rglob("*.pdf"))) == 1


def test_ui_client_maps_missing_evaluation_to_a_safe_message(
    integration_harness: IntegrationHarness,
) -> None:
    missing_evaluation_id = uuid4()

    with pytest.raises(ApiOperationError) as captured:
        integration_harness.client.list_documents(missing_evaluation_id)

    assert captured.value.public_message == "Avaliação não encontrada."
    assert str(captured.value) == "Avaliação não encontrada."
    assert str(missing_evaluation_id) not in str(captured.value)
    assert evaluation_ids_for_prefix(integration_harness.title_prefix) == []
