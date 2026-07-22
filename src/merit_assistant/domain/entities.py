from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
