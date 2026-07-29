from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from merit_assistant.api.dependencies import (
    DocumentUploadServiceDependency,
)
from merit_assistant.api.schemas import DocumentUploadResponse
from merit_assistant.application.ports.document_storage import (
    DocumentStorageError,
)
from merit_assistant.application.services.document_upload import (
    DocumentCompensationError,
    DocumentUploadPersistenceError,
    DuplicateDocumentError,
    EvaluationNotFoundError,
    OriginalFilenameTooLongError,
    StoredContentMismatchError,
)
from merit_assistant.application.services.document_validation import (
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidOriginalFilenameError,
    InvalidPdfError,
    NonSeekableDocumentError,
    UnsupportedContentTypeError,
)

router = APIRouter(tags=["documents"])


@router.post(
    "/evaluations/{evaluation_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    evaluation_id: UUID,
    file: Annotated[UploadFile, File()],
    service: DocumentUploadServiceDependency,
) -> DocumentUploadResponse:
    if file.filename is None or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nome de arquivo inválido.",
        )

    try:
        document = service.upload(
            evaluation_id=evaluation_id,
            original_filename=file.filename,
            declared_content_type=file.content_type,
            source=file.file,
        )
    except (
        InvalidOriginalFilenameError,
        OriginalFilenameTooLongError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nome de arquivo inválido.",
        ) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="O documento está vazio.",
        ) from exc
    except InvalidPdfError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="O arquivo enviado não é um PDF válido.",
        ) from exc
    except NonSeekableDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Não foi possível processar o arquivo enviado.",
        ) from exc
    except UnsupportedContentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de conteúdo não suportado.",
        ) from exc
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="O documento excede o limite permitido.",
        ) from exc
    except EvaluationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avaliação não encontrada.",
        ) from exc
    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Documento já associado à avaliação.",
        ) from exc
    except (
        StoredContentMismatchError,
        DocumentUploadPersistenceError,
        DocumentCompensationError,
        DocumentStorageError,
        OSError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível concluir o upload do documento.",
        ) from exc

    return DocumentUploadResponse.model_validate(
        document,
        from_attributes=True,
    )
