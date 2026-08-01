from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from uuid import UUID

from merit_assistant.application.ports.document_storage import (
    DocumentAlreadyExistsError,
    DocumentStorageError,
    UnsafeStoragePathError,
)
from merit_assistant.config.settings import Settings


class LocalDocumentStorage:
    """Local document storage confined to a configured private directory."""

    DIRECTORY_MODE = 0o700
    FILE_MODE = 0o600
    CHUNK_SIZE = 1024 * 1024

    def __init__(self, root: Path) -> None:
        configured_root = root.expanduser()

        if configured_root.is_symlink():
            raise UnsafeStoragePathError("The configured storage root must not be a symbolic link.")

        configured_root.mkdir(
            mode=self.DIRECTORY_MODE,
            parents=True,
            exist_ok=True,
        )

        if not configured_root.is_dir():
            raise DocumentStorageError("The configured storage root is not a directory.")

        configured_root.chmod(self.DIRECTORY_MODE)
        self._root = configured_root.resolve(strict=True)

    @classmethod
    def from_settings(cls, settings: Settings) -> LocalDocumentStorage:
        """Create storage using the configured private-data directory."""
        return cls(settings.private_data_dir)

    @staticmethod
    def build_storage_key(
        evaluation_id: UUID,
        document_id: UUID,
    ) -> str:
        """Build the canonical relative key for a stored document."""
        return PurePosixPath(
            "evaluations",
            str(evaluation_id),
            "documents",
            f"{document_id}.pdf",
        ).as_posix()

    def store(
        self,
        evaluation_id: UUID,
        document_id: UUID,
        source: BinaryIO,
    ) -> str:
        """Store binary content atomically without replacing existing files."""
        storage_key = self.build_storage_key(evaluation_id, document_id)
        destination = self._prepare_destination(storage_key)

        temporary_path: Path | None = None

        try:
            file_descriptor, temporary_name = tempfile.mkstemp(
                dir=destination.parent,
                prefix=f".{document_id}.",
                suffix=".tmp",
            )
            temporary_path = Path(temporary_name)

            with os.fdopen(file_descriptor, "wb") as temporary_file:
                os.fchmod(temporary_file.fileno(), self.FILE_MODE)

                while True:
                    chunk = source.read(self.CHUNK_SIZE)

                    if not chunk:
                        break

                    temporary_file.write(chunk)

                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            try:
                os.link(
                    temporary_path,
                    destination,
                    follow_symlinks=False,
                )
            except FileExistsError as exc:
                raise DocumentAlreadyExistsError(
                    "The destination document already exists."
                ) from exc

            try:
                temporary_path.unlink()
            except OSError:
                # Roll back the published name if the temporary name cannot
                # be removed, preserving failure semantics for the caller.
                with suppress(FileNotFoundError):
                    destination.unlink()
                raise

            temporary_path = None
            return storage_key

        finally:
            if temporary_path is not None:
                with suppress(FileNotFoundError):
                    temporary_path.unlink()

    def open_binary(self, storage_key: str) -> BinaryIO:
        """Open a stored document for binary reading."""
        source_path = self._resolve_storage_key(storage_key)

        file_descriptor = os.open(
            source_path,
            os.O_RDONLY | os.O_NOFOLLOW,
        )

        try:
            return os.fdopen(file_descriptor, "rb")
        except Exception:
            os.close(file_descriptor)
            raise

    def delete(self, storage_key: str) -> bool:
        """Delete a stored document without removing its parent directories."""
        source_path = self._resolve_storage_key(storage_key)

        try:
            source_path.unlink()
        except FileNotFoundError:
            return False

        return True

    def _validate_storage_key(self, storage_key: str) -> PurePosixPath:
        if not storage_key or storage_key != storage_key.strip():
            raise UnsafeStoragePathError("The storage key is empty or malformed.")

        if "\x00" in storage_key or "\\" in storage_key:
            raise UnsafeStoragePathError("The storage key contains an invalid character.")

        key = PurePosixPath(storage_key)

        if key.is_absolute():
            raise UnsafeStoragePathError("Absolute storage keys are not permitted.")

        if ".." in key.parts:
            raise UnsafeStoragePathError("Parent-directory segments are not permitted.")

        if key.as_posix() != storage_key:
            raise UnsafeStoragePathError("The storage key is not in canonical POSIX format.")

        if len(key.parts) != 4:
            raise UnsafeStoragePathError("The storage key does not follow the approved structure.")

        root_segment, evaluation_segment, document_segment, filename = key.parts

        if root_segment != "evaluations" or document_segment != "documents":
            raise UnsafeStoragePathError("The storage key does not follow the approved structure.")

        if not filename.endswith(".pdf"):
            raise UnsafeStoragePathError(
                "The storage key does not identify the approved file type."
            )

        document_segment_id = filename.removesuffix(".pdf")

        try:
            evaluation_id = UUID(evaluation_segment)
            document_id = UUID(document_segment_id)
        except ValueError as exc:
            raise UnsafeStoragePathError("The storage key contains an invalid identifier.") from exc

        if str(evaluation_id) != evaluation_segment:
            raise UnsafeStoragePathError("The evaluation identifier is not canonical.")

        if f"{document_id}.pdf" != filename:
            raise UnsafeStoragePathError("The document identifier is not canonical.")

        return key

    def _assert_no_symlink_components(self, candidate: Path) -> None:
        try:
            relative_candidate = candidate.relative_to(self._root)
        except ValueError as exc:
            raise UnsafeStoragePathError("The storage path is outside the private root.") from exc

        current = self._root

        for part in relative_candidate.parts:
            current = current / part

            if current.is_symlink():
                raise UnsafeStoragePathError("Symbolic links are not permitted in storage paths.")

    def _resolve_storage_key(self, storage_key: str) -> Path:
        key = self._validate_storage_key(storage_key)
        candidate = self._root.joinpath(*key.parts)

        self._assert_no_symlink_components(candidate)

        resolved_candidate = candidate.resolve(strict=False)

        if not resolved_candidate.is_relative_to(self._root):
            raise UnsafeStoragePathError("The storage path is outside the private root.")

        return resolved_candidate

    def _ensure_private_directory(self, directory: Path) -> None:
        resolved_directory = directory.resolve(strict=False)

        if not resolved_directory.is_relative_to(self._root):
            raise UnsafeStoragePathError("The storage directory is outside the private root.")

        try:
            relative_directory = directory.relative_to(self._root)
        except ValueError as exc:
            raise UnsafeStoragePathError(
                "The storage directory is outside the private root."
            ) from exc

        current = self._root

        for part in relative_directory.parts:
            current = current / part

            if current.is_symlink():
                raise UnsafeStoragePathError("Symbolic links are not permitted in storage paths.")

            current.mkdir(mode=self.DIRECTORY_MODE, exist_ok=True)

            if current.is_symlink():
                raise UnsafeStoragePathError("Symbolic links are not permitted in storage paths.")

            if not current.is_dir():
                raise DocumentStorageError("A storage-directory component is not a directory.")

            current.chmod(self.DIRECTORY_MODE)

            resolved_current = current.resolve(strict=True)

            if not resolved_current.is_relative_to(self._root):
                raise UnsafeStoragePathError("The storage directory is outside the private root.")

    def _prepare_destination(self, storage_key: str) -> Path:
        destination = self._resolve_storage_key(storage_key)
        self._ensure_private_directory(destination.parent)

        # Validate again after directory creation.
        return self._resolve_storage_key(storage_key)
