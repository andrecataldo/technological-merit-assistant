from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from merit_assistant.application.ports.document_persistence import (
    DocumentPersistenceError,
    DuplicateDocumentPersistenceError,
    EvaluationReferencePersistenceError,
)
from merit_assistant.domain.entities import Document
from merit_assistant.infrastructure.db.document_persistence import (
    DUPLICATE_DOCUMENT_CONSTRAINT,
    EVALUATION_REFERENCE_CONSTRAINT,
    SqlAlchemyDocumentPersistence,
)
from merit_assistant.infrastructure.db.models import DocumentModel


@dataclass(frozen=True, slots=True)
class FakeDiagnostic:
    constraint_name: str | None


class FakeDatabaseError(Exception):
    diag: FakeDiagnostic

    def __init__(self, constraint_name: str | None) -> None:
        super().__init__("synthetic database failure")
        self.diag = FakeDiagnostic(constraint_name)


class FakeScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = list(values)

    def all(self) -> list[object]:
        return list(self._values)


class FakeSession:
    def __init__(self) -> None:
        self.scalar_results: list[object | None] = []
        self.scalar_statements: list[object] = []
        self.scalars_results: list[list[object]] = []
        self.scalars_statements: list[object] = []
        self.added_objects: list[object] = []

        self.scalar_error: SQLAlchemyError | None = None
        self.scalars_error: SQLAlchemyError | None = None
        self.add_error: SQLAlchemyError | None = None
        self.commit_error: SQLAlchemyError | None = None
        self.rollback_error: SQLAlchemyError | None = None

        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def scalar(self, statement: object) -> object | None:
        self.scalar_statements.append(statement)

        if self.scalar_error is not None:
            raise self.scalar_error

        if not self.scalar_results:
            return None

        return self.scalar_results.pop(0)

    def scalars(self, statement: object) -> FakeScalarResult:
        self.scalars_statements.append(statement)

        if self.scalars_error is not None:
            raise self.scalars_error

        if not self.scalars_results:
            return FakeScalarResult([])

        return FakeScalarResult(self.scalars_results.pop(0))

    def add(self, instance: object) -> None:
        if self.add_error is not None:
            raise self.add_error

        self.added_objects.append(instance)

    def commit(self) -> None:
        self.commit_calls += 1

        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self) -> None:
        self.rollback_calls += 1

        if self.rollback_error is not None:
            raise self.rollback_error

    def close(self) -> None:
        self.close_calls += 1


def make_persistence(
    fake_session: FakeSession,
) -> SqlAlchemyDocumentPersistence:
    return SqlAlchemyDocumentPersistence(cast(Session, fake_session))


def make_document(
    *,
    evaluation_id: UUID | None = None,
) -> Document:
    resolved_evaluation_id = evaluation_id or uuid4()
    document_id = uuid4()

    return Document(
        id=document_id,
        evaluation_id=resolved_evaluation_id,
        original_filename="synthetic-document.pdf",
        storage_key=(f"evaluations/{resolved_evaluation_id}/documents/{document_id}.pdf"),
        content_type="application/pdf",
        size_bytes=2048,
        sha256="a" * 64,
        created_at=datetime(2026, 7, 28, 18, 0, tzinfo=UTC),
    )


def make_model(document: Document) -> DocumentModel:
    return DocumentModel(
        id=document.id,
        evaluation_id=document.evaluation_id,
        original_filename=document.original_filename,
        storage_key=document.storage_key,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        sha256=document.sha256,
        created_at=document.created_at,
    )


def make_integrity_error(
    constraint_name: str | None,
) -> IntegrityError:
    original_error = FakeDatabaseError(constraint_name)

    return IntegrityError(
        statement="INSERT INTO documents (...) VALUES (...)",
        params={},
        orig=original_error,
    )


@pytest.mark.parametrize(
    ("scalar_result", "expected"),
    [
        (uuid4(), True),
        (None, False),
    ],
)
def test_evaluation_exists_returns_expected_boolean(
    scalar_result: object | None,
    expected: bool,
) -> None:
    fake_session = FakeSession()
    fake_session.scalar_results.append(scalar_result)
    persistence = make_persistence(fake_session)
    evaluation_id = uuid4()

    result = persistence.evaluation_exists(evaluation_id)

    assert result is expected
    assert len(fake_session.scalar_statements) == 1

    sql = str(fake_session.scalar_statements[0])

    assert "FROM evaluations" in sql
    assert "evaluations.id =" in sql


def test_document_lookup_is_scoped_to_evaluation_and_sha256() -> None:
    fake_session = FakeSession()
    fake_session.scalar_results.append(uuid4())
    persistence = make_persistence(fake_session)

    result = persistence.exists_by_evaluation_and_sha256(
        uuid4(),
        "b" * 64,
    )

    assert result is True
    assert len(fake_session.scalar_statements) == 1

    sql = str(fake_session.scalar_statements[0])

    assert "FROM documents" in sql
    assert "documents.evaluation_id =" in sql
    assert "documents.sha256 =" in sql


def test_list_by_evaluation_returns_empty_tuple() -> None:
    fake_session = FakeSession()
    fake_session.scalars_results.append([])
    persistence = make_persistence(fake_session)
    evaluation_id = uuid4()

    result = persistence.list_by_evaluation(evaluation_id)

    assert result == ()
    assert len(fake_session.scalars_statements) == 1
    assert fake_session.commit_calls == 0
    assert fake_session.rollback_calls == 0
    assert fake_session.close_calls == 0


def test_list_by_evaluation_filters_orders_and_maps_all_fields() -> None:
    fake_session = FakeSession()
    persistence = make_persistence(fake_session)
    evaluation_id = uuid4()

    first_document = make_document(
        evaluation_id=evaluation_id,
    )
    second_document = make_document(
        evaluation_id=evaluation_id,
    )

    fake_session.scalars_results.append(
        [
            make_model(first_document),
            make_model(second_document),
        ]
    )

    result = persistence.list_by_evaluation(evaluation_id)

    assert result == (
        first_document,
        second_document,
    )
    assert len(fake_session.scalars_statements) == 1

    sql = " ".join(str(fake_session.scalars_statements[0]).split())

    assert "FROM documents" in sql
    assert "documents.evaluation_id =" in sql
    assert ("ORDER BY documents.created_at ASC, documents.id ASC") in sql

    assert fake_session.commit_calls == 0
    assert fake_session.rollback_calls == 0
    assert fake_session.close_calls == 0


def test_list_query_error_is_translated_and_preserves_cause() -> None:
    fake_session = FakeSession()
    original_error = SQLAlchemyError("synthetic list query failure")
    fake_session.scalars_error = original_error
    persistence = make_persistence(fake_session)

    with pytest.raises(DocumentPersistenceError) as exc_info:
        persistence.list_by_evaluation(uuid4())

    assert str(exc_info.value) == ("document persistence operation failed")
    assert exc_info.value.__cause__ is original_error
    assert fake_session.commit_calls == 0
    assert fake_session.rollback_calls == 0
    assert fake_session.close_calls == 0


def test_add_maps_every_document_field_without_changes() -> None:
    fake_session = FakeSession()
    persistence = make_persistence(fake_session)
    document = make_document()

    persistence.add(document)

    assert len(fake_session.added_objects) == 1

    model = fake_session.added_objects[0]

    assert isinstance(model, DocumentModel)
    assert model.id == document.id
    assert model.evaluation_id == document.evaluation_id
    assert model.original_filename == document.original_filename
    assert model.storage_key == document.storage_key
    assert model.content_type == document.content_type
    assert model.size_bytes == document.size_bytes
    assert model.sha256 == document.sha256
    assert model.created_at == document.created_at


def test_commit_and_rollback_delegate_without_closing_session() -> None:
    fake_session = FakeSession()
    persistence = make_persistence(fake_session)

    persistence.commit()
    persistence.rollback()

    assert fake_session.commit_calls == 1
    assert fake_session.rollback_calls == 1
    assert fake_session.close_calls == 0


def test_duplicate_constraint_is_translated() -> None:
    fake_session = FakeSession()
    original_error = make_integrity_error(DUPLICATE_DOCUMENT_CONSTRAINT)
    fake_session.commit_error = original_error
    persistence = make_persistence(fake_session)

    with pytest.raises(DuplicateDocumentPersistenceError) as exc_info:
        persistence.commit()

    assert exc_info.value.__cause__ is original_error


def test_evaluation_foreign_key_is_translated() -> None:
    fake_session = FakeSession()
    original_error = make_integrity_error(EVALUATION_REFERENCE_CONSTRAINT)
    fake_session.commit_error = original_error
    persistence = make_persistence(fake_session)

    with pytest.raises(EvaluationReferencePersistenceError) as exc_info:
        persistence.commit()

    assert exc_info.value.__cause__ is original_error


def test_unknown_integrity_constraint_uses_base_error() -> None:
    fake_session = FakeSession()
    original_error = make_integrity_error("synthetic_unknown_constraint")
    fake_session.commit_error = original_error
    persistence = make_persistence(fake_session)

    with pytest.raises(DocumentPersistenceError) as exc_info:
        persistence.commit()

    assert type(exc_info.value) is DocumentPersistenceError
    assert exc_info.value.__cause__ is original_error


def test_generic_sqlalchemy_add_error_is_translated() -> None:
    fake_session = FakeSession()
    original_error = SQLAlchemyError("synthetic add failure")
    fake_session.add_error = original_error
    persistence = make_persistence(fake_session)

    with pytest.raises(DocumentPersistenceError) as exc_info:
        persistence.add(make_document())

    assert type(exc_info.value) is DocumentPersistenceError
    assert exc_info.value.__cause__ is original_error


def test_query_error_is_translated_without_exposing_query_data() -> None:
    fake_session = FakeSession()
    original_error = SQLAlchemyError("synthetic query failure")
    fake_session.scalar_error = original_error
    persistence = make_persistence(fake_session)

    with pytest.raises(DocumentPersistenceError) as exc_info:
        persistence.evaluation_exists(uuid4())

    assert str(exc_info.value) == ("document persistence operation failed")
    assert exc_info.value.__cause__ is original_error
