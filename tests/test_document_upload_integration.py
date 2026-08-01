from __future__ import annotations

import shutil
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pymupdf
import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from merit_assistant.application.ports.document_persistence import (
    DocumentPersistenceError,
    DuplicateDocumentPersistenceError,
    EvaluationReferencePersistenceError,
)
from merit_assistant.application.services.document_upload import (
    DocumentUploadPersistenceError,
    DocumentUploadService,
)
from merit_assistant.application.services.document_validation import (
    DocumentValidationService,
)
from merit_assistant.domain.entities import Document
from merit_assistant.infrastructure.db.document_persistence import (
    SqlAlchemyDocumentPersistence,
)
from merit_assistant.infrastructure.db.models import (
    DocumentModel,
    EvaluationModel,
    EvaluationProfileModel,
)
from merit_assistant.infrastructure.db.session import (
    get_session_factory,
)
from merit_assistant.infrastructure.pdf.pymupdf_inspector import (
    PyMuPdfInspector,
)
from merit_assistant.infrastructure.storage.local_document_storage import (
    LocalDocumentStorage,
)


@pytest.fixture
def integration_db_session() -> Iterator[Session]:
    session = get_session_factory()()

    try:
        yield session
    finally:
        try:
            session.rollback()

            synthetic_profile_ids = list(
                session.scalars(
                    select(EvaluationProfileModel.id).where(
                        EvaluationProfileModel.id.like("f01-4-integration-%")
                    )
                )
            )

            if synthetic_profile_ids:
                synthetic_evaluation_ids = list(
                    session.scalars(
                        select(EvaluationModel.id).where(
                            EvaluationModel.profile_id.in_(synthetic_profile_ids)
                        )
                    )
                )

                if synthetic_evaluation_ids:
                    session.execute(
                        delete(DocumentModel).where(
                            DocumentModel.evaluation_id.in_(synthetic_evaluation_ids)
                        )
                    )
                    session.execute(
                        delete(EvaluationModel).where(
                            EvaluationModel.id.in_(synthetic_evaluation_ids)
                        )
                    )

                session.execute(
                    delete(EvaluationProfileModel).where(
                        EvaluationProfileModel.id.in_(synthetic_profile_ids)
                    )
                )
                session.commit()
        finally:
            session.close()


def create_synthetic_pdf() -> bytes:
    """Create a one-page synthetic PDF entirely in memory."""
    with pymupdf.open() as document:  # type: ignore[no-untyped-call]
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Synthetic F01.4 integration document",
        )
        return cast(bytes, document.tobytes())


def create_profile_and_evaluations(
    session: Session,
    *,
    evaluation_count: int,
) -> tuple[str, list[UUID]]:
    profile_id = f"f01-4-integration-{uuid4().hex}"
    evaluation_ids = [uuid4() for _ in range(evaluation_count)]

    session.add(
        EvaluationProfileModel(
            id=profile_id,
            name="Synthetic F01.4 integration profile",
            version="1.0",
            status="active",
        )
    )

    # Make the parent row visible before inserting evaluations that
    # reference it. The models intentionally have no ORM relationship.
    session.flush()

    for index, evaluation_id in enumerate(evaluation_ids, start=1):
        session.add(
            EvaluationModel(
                id=evaluation_id,
                title=f"Synthetic integration evaluation {index}",
                profile_id=profile_id,
                created_at=datetime(2026, 7, 28, 18, index, tzinfo=UTC),
            )
        )

    session.commit()

    return profile_id, evaluation_ids


def cleanup_synthetic_data(
    session: Session,
    *,
    evaluation_ids: list[UUID],
    profile_id: str,
) -> None:
    session.rollback()

    session.execute(delete(DocumentModel).where(DocumentModel.evaluation_id.in_(evaluation_ids)))
    session.execute(delete(EvaluationModel).where(EvaluationModel.id.in_(evaluation_ids)))
    session.execute(delete(EvaluationProfileModel).where(EvaluationProfileModel.id == profile_id))

    session.commit()


def make_document(
    *,
    evaluation_id: UUID,
    document_id: UUID,
    content_sha256: str,
    suffix: str,
) -> Document:
    return Document(
        id=document_id,
        evaluation_id=evaluation_id,
        original_filename=f"synthetic-{suffix}.pdf",
        storage_key=(f"evaluations/{evaluation_id}/documents/{document_id}.pdf"),
        content_type="application/pdf",
        size_bytes=2048,
        sha256=content_sha256,
        created_at=datetime(2026, 7, 28, 19, 0, tzinfo=UTC),
    )


class FailingCommitPersistence:
    """Delegate to PostgreSQL but fail deterministically at commit."""

    def __init__(
        self,
        delegate: SqlAlchemyDocumentPersistence,
    ) -> None:
        self._delegate = delegate
        self.commit_calls = 0
        self.rollback_calls = 0

    def evaluation_exists(self, evaluation_id: UUID) -> bool:
        return self._delegate.evaluation_exists(evaluation_id)

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        content_sha256: str,
    ) -> bool:
        return self._delegate.exists_by_evaluation_and_sha256(
            evaluation_id,
            content_sha256,
        )

    def list_by_evaluation(
        self,
        evaluation_id: UUID,
    ) -> Sequence[Document]:
        return self._delegate.list_by_evaluation(
            evaluation_id
        )

    def add(self, document: Document) -> None:
        self._delegate.add(document)

    def commit(self) -> None:
        self.commit_calls += 1

        raise DocumentPersistenceError("synthetic controlled commit failure")

    def rollback(self) -> None:
        self.rollback_calls += 1
        self._delegate.rollback()


def test_sqlalchemy_document_persistence_against_real_postgresql(
    integration_db_session: Session,
) -> None:
    profile_id, evaluation_ids = create_profile_and_evaluations(
        integration_db_session,
        evaluation_count=2,
    )
    first_evaluation_id, second_evaluation_id = evaluation_ids
    persistence = SqlAlchemyDocumentPersistence(integration_db_session)

    try:
        assert persistence.evaluation_exists(first_evaluation_id)
        assert persistence.evaluation_exists(second_evaluation_id)
        assert not persistence.evaluation_exists(uuid4())

        shared_sha256 = "a" * 64

        assert not persistence.exists_by_evaluation_and_sha256(
            first_evaluation_id,
            shared_sha256,
        )

        first_document = make_document(
            evaluation_id=first_evaluation_id,
            document_id=uuid4(),
            content_sha256=shared_sha256,
            suffix="first",
        )

        persistence.add(first_document)
        persistence.commit()

        assert persistence.exists_by_evaluation_and_sha256(
            first_evaluation_id,
            shared_sha256,
        )

        stored_document = integration_db_session.get(
            DocumentModel,
            first_document.id,
        )

        assert stored_document is not None
        assert stored_document.id == first_document.id
        assert stored_document.evaluation_id == first_document.evaluation_id
        assert stored_document.original_filename == first_document.original_filename
        assert stored_document.storage_key == first_document.storage_key
        assert stored_document.content_type == first_document.content_type
        assert stored_document.size_bytes == first_document.size_bytes
        assert stored_document.sha256 == first_document.sha256
        assert stored_document.created_at == first_document.created_at

        second_document = make_document(
            evaluation_id=second_evaluation_id,
            document_id=uuid4(),
            content_sha256=shared_sha256,
            suffix="second-evaluation",
        )

        persistence.add(second_document)
        persistence.commit()

        assert persistence.exists_by_evaluation_and_sha256(
            second_evaluation_id,
            shared_sha256,
        )

        duplicate_document = make_document(
            evaluation_id=first_evaluation_id,
            document_id=uuid4(),
            content_sha256=shared_sha256,
            suffix="duplicate",
        )

        persistence.add(duplicate_document)

        with pytest.raises(DuplicateDocumentPersistenceError):
            persistence.commit()

        persistence.rollback()

        assert (
            integration_db_session.get(
                DocumentModel,
                duplicate_document.id,
            )
            is None
        )

        invalid_reference_document = make_document(
            evaluation_id=uuid4(),
            document_id=uuid4(),
            content_sha256="b" * 64,
            suffix="invalid-evaluation",
        )

        persistence.add(invalid_reference_document)

        with pytest.raises(EvaluationReferencePersistenceError):
            persistence.commit()

        persistence.rollback()

        assert integration_db_session.scalar(text("SELECT 1")) == 1
    finally:
        cleanup_synthetic_data(
            integration_db_session,
            evaluation_ids=evaluation_ids,
            profile_id=profile_id,
        )


def test_document_upload_nominal_with_real_components(
    integration_db_session: Session,
    tmp_path: Path,
) -> None:
    profile_id, evaluation_ids = create_profile_and_evaluations(
        integration_db_session,
        evaluation_count=1,
    )
    evaluation_id = evaluation_ids[0]

    repository_root = Path(__file__).resolve().parents[1]
    storage_root = tmp_path / "private-document-storage"

    assert not storage_root.resolve().is_relative_to(repository_root)

    storage = LocalDocumentStorage(storage_root)
    persistence = SqlAlchemyDocumentPersistence(integration_db_session)
    validator = DocumentValidationService(
        inspector=PyMuPdfInspector(),
        max_size_bytes=5 * 1024 * 1024,
    )

    content = create_synthetic_pdf()
    content_sha256 = sha256(content).hexdigest()
    source = BytesIO(content)
    document_id = uuid4()
    created_at = datetime(
        2026,
        7,
        28,
        20,
        0,
        tzinfo=UTC,
    )

    service = DocumentUploadService(
        validator=validator,
        storage=storage,
        persistence=persistence,
        id_factory=lambda: document_id,
        clock=lambda: created_at,
    )

    stored_key: str | None = None

    try:
        document = service.upload(
            evaluation_id=evaluation_id,
            original_filename="synthetic-integration.pdf",
            declared_content_type="application/pdf",
            source=source,
        )
        stored_key = document.storage_key

        expected_storage_key = LocalDocumentStorage.build_storage_key(
            evaluation_id,
            document_id,
        )
        stored_path = storage_root.joinpath(*expected_storage_key.split("/"))

        assert document.id == document_id
        assert document.evaluation_id == evaluation_id
        assert document.original_filename == "synthetic-integration.pdf"
        assert document.storage_key == expected_storage_key
        assert document.content_type == "application/pdf"
        assert document.size_bytes == len(content)
        assert document.sha256 == content_sha256
        assert document.created_at == created_at

        assert stored_path.is_file()
        assert stored_path.read_bytes() == content
        assert not list(storage_root.rglob("*.tmp"))

        stored_document = integration_db_session.get(
            DocumentModel,
            document_id,
        )

        assert stored_document is not None
        assert stored_document.id == document.id
        assert stored_document.evaluation_id == document.evaluation_id
        assert stored_document.original_filename == document.original_filename
        assert stored_document.storage_key == document.storage_key
        assert stored_document.content_type == document.content_type
        assert stored_document.size_bytes == document.size_bytes
        assert stored_document.sha256 == document.sha256
        assert stored_document.created_at == document.created_at

        assert source.closed is False
        assert source.tell() == 0
    finally:
        if stored_key is not None:
            storage.delete(stored_key)

        cleanup_synthetic_data(
            integration_db_session,
            evaluation_ids=evaluation_ids,
            profile_id=profile_id,
        )
        shutil.rmtree(storage_root, ignore_errors=True)


def test_commit_failure_compensates_database_and_storage(
    integration_db_session: Session,
    tmp_path: Path,
) -> None:
    profile_id, evaluation_ids = create_profile_and_evaluations(
        integration_db_session,
        evaluation_count=1,
    )
    evaluation_id = evaluation_ids[0]

    repository_root = Path(__file__).resolve().parents[1]
    storage_root = tmp_path / "compensation-storage"

    assert not storage_root.resolve().is_relative_to(repository_root)

    storage = LocalDocumentStorage(storage_root)
    concrete_persistence = SqlAlchemyDocumentPersistence(integration_db_session)
    failing_persistence = FailingCommitPersistence(concrete_persistence)
    validator = DocumentValidationService(
        inspector=PyMuPdfInspector(),
        max_size_bytes=5 * 1024 * 1024,
    )

    content = create_synthetic_pdf()
    source = BytesIO(content)
    document_id = uuid4()
    expected_storage_key = LocalDocumentStorage.build_storage_key(
        evaluation_id,
        document_id,
    )
    expected_storage_path = storage_root.joinpath(*expected_storage_key.split("/"))

    service = DocumentUploadService(
        validator=validator,
        storage=storage,
        persistence=failing_persistence,
        id_factory=lambda: document_id,
        clock=lambda: datetime(
            2026,
            7,
            28,
            21,
            0,
            tzinfo=UTC,
        ),
    )

    try:
        with pytest.raises(DocumentUploadPersistenceError) as exc_info:
            service.upload(
                evaluation_id=evaluation_id,
                original_filename=("synthetic-compensation.pdf"),
                declared_content_type="application/pdf",
                source=source,
            )

        assert isinstance(
            exc_info.value.__cause__,
            DocumentPersistenceError,
        )
        assert failing_persistence.commit_calls == 1
        assert failing_persistence.rollback_calls == 1

        assert (
            integration_db_session.get(
                DocumentModel,
                document_id,
            )
            is None
        )

        assert not expected_storage_path.exists()

        residual_files = [path for path in storage_root.rglob("*") if path.is_file()]

        assert residual_files == []
        assert not list(storage_root.rglob("*.tmp"))
        assert source.closed is False
        assert source.tell() == 0

        assert integration_db_session.scalar(text("SELECT 1")) == 1
    finally:
        cleanup_synthetic_data(
            integration_db_session,
            evaluation_ids=evaluation_ids,
            profile_id=profile_id,
        )
        shutil.rmtree(storage_root, ignore_errors=True)
