from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint

from merit_assistant.domain.entities import Document
from merit_assistant.infrastructure.db.models import DocumentModel

VALID_SHA256 = "a" * 64


def make_document(
    *,
    size_bytes: int = 1024,
    sha256: str = VALID_SHA256,
    storage_key: str = "evaluations/documents/document.pdf",
) -> Document:
    return Document(
        id=uuid4(),
        evaluation_id=uuid4(),
        original_filename="synthetic-project.pdf",
        storage_key=storage_key,
        content_type="application/pdf",
        size_bytes=size_bytes,
        sha256=sha256,
        created_at=datetime.now(UTC),
    )


def test_document_accepts_valid_metadata() -> None:
    document = make_document()

    assert document.original_filename == "synthetic-project.pdf"
    assert document.storage_key == "evaluations/documents/document.pdf"
    assert document.content_type == "application/pdf"
    assert document.size_bytes == 1024
    assert document.sha256 == VALID_SHA256


@pytest.mark.parametrize("size_bytes", [0, -1])
def test_document_rejects_non_positive_size(size_bytes: int) -> None:
    with pytest.raises(ValueError, match="size_bytes must be greater than zero"):
        make_document(size_bytes=size_bytes)


@pytest.mark.parametrize("sha256", ["", "a" * 63, "a" * 65])
def test_document_rejects_invalid_sha256_length(sha256: str) -> None:
    with pytest.raises(ValueError, match="sha256 must contain exactly 64 characters"):
        make_document(sha256=sha256)


def test_document_rejects_absolute_storage_key() -> None:
    with pytest.raises(ValueError, match="storage_key must be a relative path"):
        make_document(storage_key="/data/private/document.pdf")


@pytest.mark.parametrize(
    "storage_key",
    [
        "../document.pdf",
        "evaluations/../document.pdf",
        "evaluations/documents/../../document.pdf",
    ],
)
def test_document_rejects_parent_directory_segments(storage_key: str) -> None:
    with pytest.raises(
        ValueError,
        match="storage_key must not contain parent directory segments",
    ):
        make_document(storage_key=storage_key)


def test_document_model_declares_expected_columns() -> None:
    table = DocumentModel.__table__

    assert set(table.columns.keys()) == {
        "id",
        "evaluation_id",
        "original_filename",
        "storage_key",
        "content_type",
        "size_bytes",
        "sha256",
        "created_at",
    }


def test_document_model_declares_required_columns() -> None:
    table = DocumentModel.__table__

    for column_name in (
        "evaluation_id",
        "original_filename",
        "storage_key",
        "content_type",
        "size_bytes",
        "sha256",
        "created_at",
    ):
        assert table.c[column_name].nullable is False


def test_document_model_declares_expected_string_lengths() -> None:
    table = DocumentModel.__table__

    assert table.c.original_filename.type.length == 255
    assert table.c.content_type.type.length == 100
    assert table.c.sha256.type.length == 64


def test_document_model_references_evaluation_with_cascade() -> None:
    foreign_key = next(iter(DocumentModel.__table__.c.evaluation_id.foreign_keys))

    assert foreign_key.target_fullname == "evaluations.id"
    assert foreign_key.ondelete == "CASCADE"
    assert foreign_key.constraint.name == "fk_documents_evaluation_id"


def test_document_model_declares_unique_constraints() -> None:
    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in DocumentModel.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert unique_constraints["uq_documents_evaluation_sha256"] == (
        "evaluation_id",
        "sha256",
    )
    assert unique_constraints["uq_documents_storage_key"] == ("storage_key",)


def test_document_model_declares_check_constraints() -> None:
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in DocumentModel.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert check_constraints["ck_documents_size_bytes_positive"] == "size_bytes > 0"
    assert check_constraints["ck_documents_sha256_length"] == "char_length(sha256) = 64"


def test_document_model_indexes_evaluation_id() -> None:
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in DocumentModel.__table__.indexes
    }

    assert indexes["ix_documents_evaluation_id"] == ("evaluation_id",)
