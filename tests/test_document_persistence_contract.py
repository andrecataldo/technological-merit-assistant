from __future__ import annotations

import ast
import inspect
from datetime import UTC, datetime
from uuid import UUID, uuid4

import merit_assistant.application.ports.document_persistence as persistence_module
from merit_assistant.application.ports.document_persistence import (
    DocumentPersistence,
    DocumentPersistenceError,
    DuplicateDocumentPersistenceError,
    EvaluationReferencePersistenceError,
)
from merit_assistant.domain.entities import Document


class FakeDocumentPersistence:
    """Typed fake used to verify structural compatibility with the port."""

    def __init__(
        self,
        *,
        existing_evaluations: set[UUID] | None = None,
        existing_documents: set[tuple[UUID, str]] | None = None,
    ) -> None:
        self.existing_evaluations = set(existing_evaluations or ())
        self.existing_documents = set(existing_documents or ())
        self.added_documents: list[Document] = []
        self.commit_calls = 0
        self.rollback_calls = 0

    def evaluation_exists(self, evaluation_id: UUID) -> bool:
        return evaluation_id in self.existing_evaluations

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256: str,
    ) -> bool:
        return (evaluation_id, sha256) in self.existing_documents

    def add(self, document: Document) -> None:
        self.added_documents.append(document)

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


def require_document_persistence(
    persistence: DocumentPersistence,
) -> DocumentPersistence:
    """Require structural compatibility during static analysis."""
    return persistence


def make_document(
    *,
    evaluation_id: UUID,
    sha256: str,
) -> Document:
    document_id = uuid4()

    return Document(
        id=document_id,
        evaluation_id=evaluation_id,
        original_filename="synthetic-document.pdf",
        storage_key=(f"evaluations/{evaluation_id}/documents/{document_id}.pdf"),
        content_type="application/pdf",
        size_bytes=1024,
        sha256=sha256,
        created_at=datetime.now(UTC),
    )


def test_persistence_errors_share_the_approved_base_type() -> None:
    for error_type in (
        DuplicateDocumentPersistenceError,
        EvaluationReferencePersistenceError,
    ):
        assert issubclass(error_type, DocumentPersistenceError)


def test_contract_exposes_only_the_approved_operations() -> None:
    operations = {
        name
        for name, member in vars(DocumentPersistence).items()
        if not name.startswith("_") and callable(member)
    }

    assert operations == {
        "evaluation_exists",
        "exists_by_evaluation_and_sha256",
        "add",
        "commit",
        "rollback",
    }


def test_port_module_does_not_import_sqlalchemy() -> None:
    syntax_tree = ast.parse(inspect.getsource(persistence_module))
    imported_roots: set[str] = set()

    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)

        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", maxsplit=1)[0])

    assert "sqlalchemy" not in imported_roots


def test_fake_implementation_satisfies_and_executes_the_contract() -> None:
    evaluation_id = uuid4()
    different_evaluation_id = uuid4()
    sha256 = "a" * 64
    document = make_document(
        evaluation_id=evaluation_id,
        sha256=sha256,
    )

    fake = FakeDocumentPersistence(
        existing_evaluations={evaluation_id},
        existing_documents={(evaluation_id, sha256)},
    )

    persistence = require_document_persistence(fake)

    assert persistence.evaluation_exists(evaluation_id)
    assert not persistence.evaluation_exists(different_evaluation_id)
    assert persistence.exists_by_evaluation_and_sha256(
        evaluation_id,
        sha256,
    )
    assert not persistence.exists_by_evaluation_and_sha256(
        different_evaluation_id,
        sha256,
    )

    persistence.add(document)
    persistence.commit()
    persistence.rollback()

    assert fake.added_documents == [document]
    assert fake.commit_calls == 1
    assert fake.rollback_calls == 1
