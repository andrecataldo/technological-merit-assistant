from io import BytesIO
from pathlib import Path, PurePosixPath
from stat import S_IMODE
from uuid import UUID

import pytest

from merit_assistant.application.ports.document_storage import (
    DocumentAlreadyExistsError,
    DocumentStorage,
    UnsafeStoragePathError,
)
from merit_assistant.config.settings import Settings
from merit_assistant.infrastructure.storage import LocalDocumentStorage

EVALUATION_ID = UUID("11111111-1111-4111-8111-111111111111")
DOCUMENT_ID = UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture
def storage(tmp_path: Path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path / "private")


def test_build_storage_key_uses_canonical_internal_identifiers() -> None:
    key = LocalDocumentStorage.build_storage_key(
        EVALUATION_ID,
        DOCUMENT_ID,
    )

    assert key == (
        "evaluations/"
        "11111111-1111-4111-8111-111111111111/"
        "documents/"
        "22222222-2222-4222-8222-222222222222.pdf"
    )
    assert not PurePosixPath(key).is_absolute()


def test_from_settings_uses_private_data_dir(tmp_path: Path) -> None:
    private_data_dir = tmp_path / "configured-private-data"
    settings = Settings(private_data_dir=private_data_dir)

    storage = LocalDocumentStorage.from_settings(settings)
    key = storage.build_storage_key(EVALUATION_ID, DOCUMENT_ID)
    destination = storage._prepare_destination(key)

    assert destination.is_relative_to(private_data_dir.resolve())
    assert private_data_dir.is_dir()


def test_storage_root_has_private_directory_permissions(tmp_path: Path) -> None:
    root = tmp_path / "private"

    LocalDocumentStorage(root)

    assert S_IMODE(root.stat().st_mode) == 0o700


def test_prepare_destination_creates_private_directories(
    storage: LocalDocumentStorage,
    tmp_path: Path,
) -> None:
    key = storage.build_storage_key(EVALUATION_ID, DOCUMENT_ID)

    destination = storage._prepare_destination(key)

    expected_root = (tmp_path / "private").resolve()
    evaluation_directory = expected_root / "evaluations" / str(EVALUATION_ID)
    documents_directory = evaluation_directory / "documents"

    assert destination == documents_directory / f"{DOCUMENT_ID}.pdf"
    assert S_IMODE((expected_root / "evaluations").stat().st_mode) == 0o700
    assert S_IMODE(evaluation_directory.stat().st_mode) == 0o700
    assert S_IMODE(documents_directory.stat().st_mode) == 0o700


@pytest.mark.parametrize(
    "storage_key",
    [
        "/etc/passwd",
        "../outside.pdf",
        "evaluations/../documents/file.pdf",
        ("evaluations/11111111-1111-4111-8111-111111111111/documents/../outside.pdf"),
    ],
)
def test_storage_path_rejects_absolute_and_traversal_keys(
    storage: LocalDocumentStorage,
    storage_key: str,
) -> None:
    with pytest.raises(UnsafeStoragePathError):
        storage._resolve_storage_key(storage_key)


@pytest.mark.parametrize(
    "storage_key",
    [
        "",
        " ",
        "./evaluations/value/documents/value.pdf",
        "evaluations//value/documents/value.pdf",
        "evaluations\\value\\documents\\value.pdf",
        "other/value/documents/value.pdf",
        "evaluations/value/other/value.pdf",
        "evaluations/not-a-uuid/documents/not-a-uuid.pdf",
        (
            "evaluations/"
            "11111111-1111-4111-8111-111111111111/"
            "documents/"
            "22222222-2222-4222-8222-222222222222.txt"
        ),
    ],
)
def test_storage_key_rejects_noncanonical_structure(
    storage: LocalDocumentStorage,
    storage_key: str,
) -> None:
    with pytest.raises(UnsafeStoragePathError):
        storage._resolve_storage_key(storage_key)


def test_storage_path_rejects_external_symlink(tmp_path: Path) -> None:
    root = tmp_path / "private"
    outside = tmp_path / "outside"
    outside.mkdir()

    storage = LocalDocumentStorage(root)
    (root / "evaluations").symlink_to(outside, target_is_directory=True)

    key = storage.build_storage_key(EVALUATION_ID, DOCUMENT_ID)

    with pytest.raises(UnsafeStoragePathError):
        storage._resolve_storage_key(key)


def test_storage_rejects_symbolic_link_as_configured_root(
    tmp_path: Path,
) -> None:
    real_root = tmp_path / "real-private"
    real_root.mkdir()

    linked_root = tmp_path / "linked-private"
    linked_root.symlink_to(real_root, target_is_directory=True)

    with pytest.raises(UnsafeStoragePathError):
        LocalDocumentStorage(linked_root)


class RecordingBytesIO(BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.requested_sizes: list[int | None] = []

    def read(self, size: int | None = -1) -> bytes:
        self.requested_sizes.append(size)
        return super().read(size)


class FailingBytesIO(BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.read_calls = 0

    def read(self, size: int | None = -1) -> bytes:
        self.read_calls += 1

        if self.read_calls > 1:
            raise OSError("Synthetic source failure.")

        return super().read(size)


def destination_for(
    tmp_path: Path,
    storage_key: str,
) -> Path:
    return (tmp_path / "private").joinpath(*PurePosixPath(storage_key).parts)


def test_store_writes_synthetic_content_with_private_permissions(
    storage: LocalDocumentStorage,
    tmp_path: Path,
) -> None:
    content = b"synthetic document content"

    storage_key = storage.store(
        EVALUATION_ID,
        DOCUMENT_ID,
        BytesIO(content),
    )

    destination = destination_for(tmp_path, storage_key)

    assert destination.read_bytes() == content
    assert S_IMODE(destination.stat().st_mode) == 0o600


def test_store_reads_source_in_controlled_chunks(
    storage: LocalDocumentStorage,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage, "CHUNK_SIZE", 4)
    source = RecordingBytesIO(b"abcdefghijkl")

    storage_key = storage.store(
        EVALUATION_ID,
        DOCUMENT_ID,
        source,
    )

    destination = destination_for(tmp_path, storage_key)

    assert destination.read_bytes() == b"abcdefghijkl"
    assert source.requested_sizes
    assert all(size == 4 for size in source.requested_sizes)


def test_store_rejects_existing_destination_without_overwriting(
    storage: LocalDocumentStorage,
    tmp_path: Path,
) -> None:
    storage_key = storage.store(
        EVALUATION_ID,
        DOCUMENT_ID,
        BytesIO(b"original content"),
    )

    with pytest.raises(DocumentAlreadyExistsError):
        storage.store(
            EVALUATION_ID,
            DOCUMENT_ID,
            BytesIO(b"replacement content"),
        )

    destination = destination_for(tmp_path, storage_key)

    assert destination.read_bytes() == b"original content"
    assert {item.name for item in destination.parent.iterdir()} == {destination.name}


def test_store_removes_temporary_file_after_source_failure(
    storage: LocalDocumentStorage,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage, "CHUNK_SIZE", 4)

    storage_key = storage.build_storage_key(
        EVALUATION_ID,
        DOCUMENT_ID,
    )
    destination = destination_for(tmp_path, storage_key)

    with pytest.raises(OSError, match="Synthetic source failure"):
        storage.store(
            EVALUATION_ID,
            DOCUMENT_ID,
            FailingBytesIO(b"abcdefgh"),
        )

    assert not destination.exists()
    assert destination.parent.is_dir()
    assert list(destination.parent.iterdir()) == []


def test_open_binary_reads_stored_content_in_read_only_mode(
    storage: LocalDocumentStorage,
) -> None:
    content = b"synthetic document for reading"

    storage_key = storage.store(
        EVALUATION_ID,
        DOCUMENT_ID,
        BytesIO(content),
    )

    with storage.open_binary(storage_key) as stored_file:
        assert stored_file.read() == content
        assert stored_file.readable()
        assert not stored_file.writable()


def test_open_binary_raises_when_document_does_not_exist(
    storage: LocalDocumentStorage,
) -> None:
    storage_key = storage.build_storage_key(
        EVALUATION_ID,
        DOCUMENT_ID,
    )

    with pytest.raises(FileNotFoundError):
        storage.open_binary(storage_key)


def test_delete_removes_existing_document_but_preserves_directories(
    storage: LocalDocumentStorage,
    tmp_path: Path,
) -> None:
    storage_key = storage.store(
        EVALUATION_ID,
        DOCUMENT_ID,
        BytesIO(b"synthetic document"),
    )
    destination = destination_for(tmp_path, storage_key)

    removed = storage.delete(storage_key)

    assert removed is True
    assert not destination.exists()
    assert destination.parent.is_dir()


def test_delete_is_idempotent(
    storage: LocalDocumentStorage,
) -> None:
    storage_key = storage.store(
        EVALUATION_ID,
        DOCUMENT_ID,
        BytesIO(b"synthetic document"),
    )

    assert storage.delete(storage_key) is True
    assert storage.delete(storage_key) is False


@pytest.mark.parametrize(
    "storage_key",
    [
        "/etc/passwd",
        "../outside.pdf",
        "evaluations/../documents/file.pdf",
    ],
)
def test_open_binary_rejects_unsafe_storage_keys(
    storage: LocalDocumentStorage,
    storage_key: str,
) -> None:
    with pytest.raises(UnsafeStoragePathError):
        storage.open_binary(storage_key)


@pytest.mark.parametrize(
    "storage_key",
    [
        "/etc/passwd",
        "../outside.pdf",
        "evaluations/../documents/file.pdf",
    ],
)
def test_delete_rejects_unsafe_storage_keys(
    storage: LocalDocumentStorage,
    storage_key: str,
) -> None:
    with pytest.raises(UnsafeStoragePathError):
        storage.delete(storage_key)


def test_open_binary_rejects_document_symlink(
    storage: LocalDocumentStorage,
    tmp_path: Path,
) -> None:
    storage_key = storage.build_storage_key(
        EVALUATION_ID,
        DOCUMENT_ID,
    )
    destination = storage._prepare_destination(storage_key)

    outside_file = tmp_path / "outside-document.pdf"
    outside_file.write_bytes(b"outside content")
    destination.symlink_to(outside_file)

    with pytest.raises(UnsafeStoragePathError):
        storage.open_binary(storage_key)


def test_delete_rejects_document_symlink_without_removing_target(
    storage: LocalDocumentStorage,
    tmp_path: Path,
) -> None:
    storage_key = storage.build_storage_key(
        EVALUATION_ID,
        DOCUMENT_ID,
    )
    destination = storage._prepare_destination(storage_key)

    outside_file = tmp_path / "outside-document.pdf"
    outside_file.write_bytes(b"outside content")
    destination.symlink_to(outside_file)

    with pytest.raises(UnsafeStoragePathError):
        storage.delete(storage_key)

    assert outside_file.read_bytes() == b"outside content"


def test_local_document_storage_satisfies_document_storage_contract(
    storage: LocalDocumentStorage,
) -> None:
    contract: DocumentStorage = storage

    assert contract is storage


def test_store_rejects_external_symlink_without_writing_outside(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private"
    outside = tmp_path / "outside"
    outside.mkdir()

    storage = LocalDocumentStorage(root)
    (root / "evaluations").symlink_to(
        outside,
        target_is_directory=True,
    )

    with pytest.raises(UnsafeStoragePathError):
        storage.store(
            EVALUATION_ID,
            DOCUMENT_ID,
            BytesIO(b"synthetic document"),
        )

    assert list(outside.iterdir()) == []
