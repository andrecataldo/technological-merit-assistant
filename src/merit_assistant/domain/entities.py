from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EvaluationProfile:
    id: str
    name: str
    version: str
    status: str


@dataclass(frozen=True, slots=True)
class Evaluation:
    id: UUID
    title: str
    profile_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Document:
    id: UUID
    evaluation_id: UUID
    original_filename: str
    storage_key: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.size_bytes <= 0:
            raise ValueError("size_bytes must be greater than zero")

        if len(self.sha256) != 64:
            raise ValueError("sha256 must contain exactly 64 characters")

        storage_path = PurePosixPath(self.storage_key)

        if storage_path.is_absolute():
            raise ValueError("storage_key must be a relative path")

        if ".." in storage_path.parts:
            raise ValueError("storage_key must not contain parent directory segments")
