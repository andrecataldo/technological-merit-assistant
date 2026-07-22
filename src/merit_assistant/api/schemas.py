from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    external_processing_enabled: bool


class ProfileResponse(BaseModel):
    id: str
    name: str
    version: str
    status: str


class EvaluationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    profile_id: str


class EvaluationResponse(BaseModel):
    id: UUID
    title: str
    profile_id: str
    created_at: datetime
