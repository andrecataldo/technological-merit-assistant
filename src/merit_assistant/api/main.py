from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from merit_assistant.api.schemas import (
    EvaluationCreate,
    EvaluationResponse,
    HealthResponse,
    ProfileResponse,
)
from merit_assistant.config.settings import get_settings
from merit_assistant.infrastructure.db.models import EvaluationModel, EvaluationProfileModel
from merit_assistant.infrastructure.db.session import get_db_session
from merit_assistant.profiles.loader import ProfileMetadata, load_profile

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
PROFILE_PATH = Path("config/profiles/finep_mais_inovacao_tecnologias_digitais/profile.yaml")

DatabaseSession = Annotated[Session, Depends(get_db_session)]


def configured_profile() -> ProfileMetadata:
    return load_profile(PROFILE_PATH)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        external_processing_enabled=settings.external_processing_enabled,
    )


@app.get("/profiles", response_model=list[ProfileResponse])
def list_profiles() -> list[ProfileResponse]:
    profile = configured_profile()
    return [ProfileResponse(**profile.model_dump())]


@app.post(
    "/evaluations",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation(
    payload: EvaluationCreate,
    session: DatabaseSession,
) -> EvaluationResponse:
    profile = configured_profile()
    if payload.profile_id != profile.id:
        raise HTTPException(status_code=400, detail="Perfil de avaliação desconhecido.")

    stored_profile = session.get(EvaluationProfileModel, profile.id)
    if stored_profile is None:
        stored_profile = EvaluationProfileModel(**profile.model_dump())
        session.add(stored_profile)
        session.flush()

    evaluation = EvaluationModel(
        id=uuid4(),
        title=payload.title,
        profile_id=payload.profile_id,
        created_at=datetime.now(UTC),
    )
    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)
    return EvaluationResponse.model_validate(evaluation, from_attributes=True)


@app.get("/evaluations", response_model=list[EvaluationResponse])
def list_evaluations(
    session: DatabaseSession,
) -> list[EvaluationResponse]:
    evaluations = session.scalars(
        select(EvaluationModel).order_by(EvaluationModel.created_at.desc())
    ).all()
    return [EvaluationResponse.model_validate(item, from_attributes=True) for item in evaluations]
