from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

import merit_assistant.api.dependencies as dependencies_module
from merit_assistant.api.main import app
from merit_assistant.infrastructure.db.models import (
    DocumentModel,
    EvaluationModel,
    EvaluationProfileModel,
)
from merit_assistant.infrastructure.db.session import (
    get_session_factory,
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
    profile_id: str
    first_evaluation_id: UUID
    second_evaluation_id: UUID
    private_root: Path
    private_files_before: frozenset[str]


def private_file_snapshot(
    private_root: Path,
) -> frozenset[str]:
    if not private_root.exists():
        return frozenset()

    return frozenset(
        path.relative_to(private_root).as_posix()
        for path in private_root.rglob("*")
        if path.is_file()
    )


def make_document(
    *,
    document_id: UUID,
    evaluation_id: UUID,
    filename: str,
    sha256_value: str,
    created_at: datetime,
) -> DocumentModel:
    return DocumentModel(
        id=document_id,
        evaluation_id=evaluation_id,
        original_filename=filename,
        storage_key=(f"synthetic/f01-6/{evaluation_id}/{document_id}.pdf"),
        content_type="application/pdf",
        size_bytes=2048,
        sha256=sha256_value,
        created_at=created_at,
    )


def persist_documents(
    *documents: DocumentModel,
) -> None:
    session = get_session_factory()()

    try:
        session.add_all(documents)
        session.commit()
    finally:
        session.close()


@pytest.fixture
def integration_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[IntegrationHarness]:
    session_factory = get_session_factory()
    setup_session = session_factory()

    profile_id = f"f01-6-listing-integration-{uuid4().hex}"
    first_evaluation_id = uuid4()
    second_evaluation_id = uuid4()

    repository_root = Path(__file__).resolve().parents[1]
    private_root = repository_root / "data" / "private"
    private_files_before = private_file_snapshot(private_root)

    previous_overrides = app.dependency_overrides.copy()

    def forbidden_settings() -> None:
        raise AssertionError("A listagem integrada não deve consultar settings.")

    monkeypatch.setattr(
        dependencies_module,
        "get_settings",
        forbidden_settings,
    )

    try:
        setup_session.add(
            EvaluationProfileModel(
                id=profile_id,
                name=("Synthetic F01.6 listing integration profile"),
                version="1.0",
                status="active",
            )
        )
        setup_session.flush()

        setup_session.add_all(
            [
                EvaluationModel(
                    id=first_evaluation_id,
                    title=("Synthetic F01.6 first integration evaluation"),
                    profile_id=profile_id,
                    created_at=datetime(
                        2026,
                        7,
                        30,
                        20,
                        0,
                        tzinfo=UTC,
                    ),
                ),
                EvaluationModel(
                    id=second_evaluation_id,
                    title=("Synthetic F01.6 second integration evaluation"),
                    profile_id=profile_id,
                    created_at=datetime(
                        2026,
                        7,
                        30,
                        20,
                        1,
                        tzinfo=UTC,
                    ),
                ),
            ]
        )
        setup_session.commit()

        # A integração deve usar as dependências reais.
        app.dependency_overrides.clear()

        with TestClient(app) as client:
            yield IntegrationHarness(
                client=client,
                profile_id=profile_id,
                first_evaluation_id=first_evaluation_id,
                second_evaluation_id=second_evaluation_id,
                private_root=private_root,
                private_files_before=private_files_before,
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

        setup_session.rollback()
        setup_session.close()

        cleanup_session = session_factory()

        try:
            evaluation_ids = (
                first_evaluation_id,
                second_evaluation_id,
            )

            cleanup_session.execute(
                delete(DocumentModel).where(DocumentModel.evaluation_id.in_(evaluation_ids))
            )
            cleanup_session.execute(
                delete(EvaluationModel).where(EvaluationModel.id.in_(evaluation_ids))
            )
            cleanup_session.execute(
                delete(EvaluationProfileModel).where(EvaluationProfileModel.id == profile_id)
            )
            cleanup_session.commit()
        finally:
            cleanup_session.close()

        verification_session = session_factory()

        try:
            remaining_documents = list(
                verification_session.scalars(
                    select(DocumentModel.id).where(
                        DocumentModel.evaluation_id.in_(
                            (
                                first_evaluation_id,
                                second_evaluation_id,
                            )
                        )
                    )
                )
            )
            remaining_evaluations = list(
                verification_session.scalars(
                    select(EvaluationModel.id).where(
                        EvaluationModel.id.in_(
                            (
                                first_evaluation_id,
                                second_evaluation_id,
                            )
                        )
                    )
                )
            )

            assert remaining_documents == []
            assert remaining_evaluations == []
            assert (
                verification_session.get(
                    EvaluationProfileModel,
                    profile_id,
                )
                is None
            )
        finally:
            verification_session.close()

        assert private_file_snapshot(private_root) == private_files_before


def test_missing_evaluation_returns_404(
    integration_harness: IntegrationHarness,
) -> None:
    response = integration_harness.client.get(f"/evaluations/{uuid4()}/documents")

    assert response.status_code == 404
    assert response.json() == {"detail": "Evaluation not found."}


def test_existing_evaluation_without_documents_returns_empty_list(
    integration_harness: IntegrationHarness,
) -> None:
    response = integration_harness.client.get(
        f"/evaluations/{integration_harness.first_evaluation_id}/documents"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_documents_are_isolated_by_evaluation(
    integration_harness: IntegrationHarness,
) -> None:
    first_document = make_document(
        document_id=uuid4(),
        evaluation_id=(integration_harness.first_evaluation_id),
        filename="first-evaluation.pdf",
        sha256_value="a" * 64,
        created_at=datetime(
            2026,
            7,
            30,
            20,
            10,
            tzinfo=UTC,
        ),
    )
    second_document = make_document(
        document_id=uuid4(),
        evaluation_id=(integration_harness.second_evaluation_id),
        filename="second-evaluation.pdf",
        sha256_value="b" * 64,
        created_at=datetime(
            2026,
            7,
            30,
            20,
            11,
            tzinfo=UTC,
        ),
    )

    persist_documents(
        first_document,
        second_document,
    )

    first_response = integration_harness.client.get(
        f"/evaluations/{integration_harness.first_evaluation_id}/documents"
    )
    second_response = integration_harness.client.get(
        f"/evaluations/{integration_harness.second_evaluation_id}/documents"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_payload = first_response.json()
    second_payload = second_response.json()

    assert len(first_payload) == 1
    assert len(second_payload) == 1

    assert first_payload[0]["id"] == str(first_document.id)
    assert second_payload[0]["id"] == str(second_document.id)

    assert first_payload[0]["evaluation_id"] == str(integration_harness.first_evaluation_id)
    assert second_payload[0]["evaluation_id"] == str(integration_harness.second_evaluation_id)


def test_documents_are_ordered_and_expose_only_public_fields(
    integration_harness: IntegrationHarness,
) -> None:
    evaluation_id = integration_harness.first_evaluation_id
    ordered_ids = sorted([uuid4(), uuid4()])
    lower_id, higher_id = ordered_ids

    earlier_document = make_document(
        document_id=uuid4(),
        evaluation_id=evaluation_id,
        filename="earlier.pdf",
        sha256_value="c" * 64,
        created_at=datetime(
            2026,
            7,
            30,
            20,
            20,
            tzinfo=UTC,
        ),
    )
    lower_uuid_document = make_document(
        document_id=lower_id,
        evaluation_id=evaluation_id,
        filename="same-time-lower-uuid.pdf",
        sha256_value="d" * 64,
        created_at=datetime(
            2026,
            7,
            30,
            20,
            21,
            tzinfo=UTC,
        ),
    )
    higher_uuid_document = make_document(
        document_id=higher_id,
        evaluation_id=evaluation_id,
        filename="same-time-higher-uuid.pdf",
        sha256_value="e" * 64,
        created_at=datetime(
            2026,
            7,
            30,
            20,
            21,
            tzinfo=UTC,
        ),
    )

    # Inserção deliberadamente fora da ordem esperada.
    persist_documents(
        higher_uuid_document,
        earlier_document,
        lower_uuid_document,
    )

    response = integration_harness.client.get(f"/evaluations/{evaluation_id}/documents")

    assert response.status_code == 200

    payload = response.json()

    assert [item["id"] for item in payload] == [
        str(earlier_document.id),
        str(lower_uuid_document.id),
        str(higher_uuid_document.id),
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
