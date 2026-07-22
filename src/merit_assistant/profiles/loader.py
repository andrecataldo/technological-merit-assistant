from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ProfileMetadata(BaseModel):
    id: str
    name: str
    version: str
    status: str


def load_profile(path: Path) -> ProfileMetadata:
    with path.open("r", encoding="utf-8") as source:
        raw = yaml.safe_load(source)
    return ProfileMetadata.model_validate(raw)
