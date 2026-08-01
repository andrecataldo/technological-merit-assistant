from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from merit_assistant.application.services.document_listing import (
    DocumentListingService,
)
from merit_assistant.application.services.document_upload import (
    DocumentUploadService,
)
from merit_assistant.application.services.document_validation import (
    DocumentValidationService,
)
from merit_assistant.config.settings import get_settings
from merit_assistant.infrastructure.db.document_persistence import (
    SqlAlchemyDocumentPersistence,
)
from merit_assistant.infrastructure.db.session import get_db_session
from merit_assistant.infrastructure.pdf.pymupdf_inspector import (
    PyMuPdfInspector,
)
from merit_assistant.infrastructure.storage.local_document_storage import (
    LocalDocumentStorage,
)

DatabaseSession = Annotated[Session, Depends(get_db_session)]


def get_document_listing_service(
    session: DatabaseSession,
) -> DocumentListingService:
    persistence = SqlAlchemyDocumentPersistence(session)

    return DocumentListingService(
        persistence=persistence,
    )


def get_document_upload_service(
    session: DatabaseSession,
) -> DocumentUploadService:
    settings = get_settings()
    inspector = PyMuPdfInspector()
    validator = DocumentValidationService.from_settings(
        inspector=inspector,
        settings=settings,
    )
    storage = LocalDocumentStorage.from_settings(settings)
    persistence = SqlAlchemyDocumentPersistence(session)

    return DocumentUploadService(
        validator=validator,
        storage=storage,
        persistence=persistence,
    )


DocumentListingServiceDependency = Annotated[
    DocumentListingService,
    Depends(get_document_listing_service),
]

DocumentUploadServiceDependency = Annotated[
    DocumentUploadService,
    Depends(get_document_upload_service),
]
