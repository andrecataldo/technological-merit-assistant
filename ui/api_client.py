from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from math import isfinite
from types import TracebackType
from typing import BinaryIO, Literal, Self, TypeVar
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

LOCAL_API_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "api"})
LOCAL_API_PORT = 8000

INVALID_API_CONFIGURATION_MESSAGE = "Configuração local da API inválida."
INVALID_HTTP_CLIENT_MESSAGE = "Configuração do cliente HTTP inválida."
API_UNAVAILABLE_MESSAGE = "API indisponível. Verifique o ambiente local."
INVALID_API_RESPONSE_MESSAGE = "A API retornou uma resposta inválida."
UNEXPECTED_OPERATION_MESSAGE = "Não foi possível concluir a operação."

DEFAULT_TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=30.0,
    write=60.0,
    pool=5.0,
)

Operation = Literal[
    "health",
    "list_profiles",
    "create_evaluation",
    "list_evaluations",
    "upload_document",
    "list_documents",
]

OPERATION_FALLBACKS: dict[Operation, str] = {
    "health": API_UNAVAILABLE_MESSAGE,
    "list_profiles": "Não foi possível carregar os perfis.",
    "create_evaluation": "Não foi possível criar a avaliação.",
    "list_evaluations": "Não foi possível carregar as avaliações.",
    "upload_document": "Não foi possível concluir o upload do documento.",
    "list_documents": "Não foi possível listar os documentos.",
}

KNOWN_OPERATION_ERRORS: dict[tuple[Operation, int, str], str] = {
    (
        "create_evaluation",
        400,
        "Perfil de avaliação desconhecido.",
    ): "Perfil de avaliação desconhecido.",
    (
        "upload_document",
        404,
        "Avaliação não encontrada.",
    ): "Avaliação não encontrada.",
    (
        "upload_document",
        409,
        "Documento já associado à avaliação.",
    ): "Documento já associado à avaliação.",
    (
        "upload_document",
        413,
        "O documento excede o limite permitido.",
    ): "O documento excede o limite permitido.",
    (
        "upload_document",
        415,
        "Tipo de conteúdo não suportado.",
    ): "Tipo de conteúdo não suportado.",
    (
        "upload_document",
        422,
        "Nome de arquivo inválido.",
    ): "Nome de arquivo inválido.",
    (
        "upload_document",
        422,
        "O documento está vazio.",
    ): "O documento está vazio.",
    (
        "upload_document",
        422,
        "O arquivo enviado não é um PDF válido.",
    ): "O arquivo enviado não é um PDF válido.",
    (
        "upload_document",
        422,
        "Não foi possível processar o arquivo enviado.",
    ): "Não foi possível processar o arquivo enviado.",
    (
        "list_documents",
        404,
        "Evaluation not found.",
    ): "Avaliação não encontrada.",
}


class StrictApiModel(BaseModel):
    """Base model for strict responses received from the public API."""

    model_config = ConfigDict(extra="forbid")


class HealthView(StrictApiModel):
    status: str
    external_processing_enabled: bool


class ProfileView(StrictApiModel):
    id: str
    name: str
    version: str
    status: str


class EvaluationView(StrictApiModel):
    id: UUID
    title: str
    profile_id: str
    created_at: datetime


class DocumentView(StrictApiModel):
    id: UUID
    evaluation_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class ApiClientError(Exception):
    """Base error containing only a stable message safe for the UI."""

    def __init__(self, public_message: str) -> None:
        self.public_message = public_message
        super().__init__(public_message)


class ApiConfigurationError(ApiClientError):
    """Raised when the local API destination or client is unsafe."""


class ApiUnavailableError(ApiClientError):
    """Raised when the local API cannot be reached within the timeout."""


class ApiProtocolError(ApiClientError):
    """Raised when the API response violates its public contract."""


class ApiOperationError(ApiClientError):
    """Raised when a public API operation does not complete successfully."""


def validate_local_api_base_url(value: str) -> str:
    """Validate and canonicalize the local FastAPI base URL."""

    if not value or value != value.strip():
        raise ApiConfigurationError(INVALID_API_CONFIGURATION_MESSAGE)

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ApiConfigurationError(
            INVALID_API_CONFIGURATION_MESSAGE
        ) from exc

    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname is not None else None

    is_valid = (
        scheme == "http"
        and host in LOCAL_API_HOSTS
        and port == LOCAL_API_PORT
        and parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )
    if not is_valid:
        raise ApiConfigurationError(INVALID_API_CONFIGURATION_MESSAGE)

    netloc = f"[{host}]:{port}" if host == "::1" else f"{host}:{port}"
    return urlunsplit(("http", netloc, "", "", ""))


def _has_finite_timeout(client: httpx.Client) -> bool:
    timeout = client.timeout
    values = (
        timeout.connect,
        timeout.read,
        timeout.write,
        timeout.pool,
    )
    return all(
        value is not None
        and value > 0
        and isfinite(value)
        for value in values
    )


def _extract_public_detail(response: httpx.Response) -> str | None:
    try:
        payload: object = response.json()
    except ValueError:
        return None

    if not isinstance(payload, Mapping):
        return None

    detail: object = payload.get("detail")
    return detail if isinstance(detail, str) else None


ModelT = TypeVar("ModelT", bound=StrictApiModel)


class MeritAssistantApiClient:
    """Synchronous and local-only client for the public FastAPI contract."""

    def __init__(
        self,
        base_url: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = validate_local_api_base_url(base_url)
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=False,
        )

        if self._http_client.follow_redirects or not _has_finite_timeout(
            self._http_client
        ):
            if self._owns_http_client:
                self._http_client.close()
            raise ApiConfigurationError(INVALID_HTTP_CLIENT_MESSAGE)

    @property
    def base_url(self) -> str:
        return self._base_url

    def health(self) -> HealthView:
        response = self._request(
            "health",
            "GET",
            "/health",
            expected_status=200,
        )
        return self._validate_model(response, HealthView)

    def list_profiles(self) -> list[ProfileView]:
        response = self._request(
            "list_profiles",
            "GET",
            "/profiles",
            expected_status=200,
        )
        return self._validate_list(response, ProfileView)

    def create_evaluation(
        self,
        title: str,
        profile_id: str,
    ) -> EvaluationView:
        response = self._request(
            "create_evaluation",
            "POST",
            "/evaluations",
            expected_status=201,
            json_payload={
                "title": title,
                "profile_id": profile_id,
            },
        )
        return self._validate_model(response, EvaluationView)

    def list_evaluations(self) -> list[EvaluationView]:
        response = self._request(
            "list_evaluations",
            "GET",
            "/evaluations",
            expected_status=200,
        )
        return self._validate_list(response, EvaluationView)

    def upload_document(
        self,
        evaluation_id: UUID,
        filename: str,
        content_type: str | None,
        source: BinaryIO,
    ) -> DocumentView:
        files: dict[str, tuple[str, BinaryIO, str]] = {
            "file": (
                filename,
                source,
                content_type or "application/octet-stream",
            )
        }
        response = self._request(
            "upload_document",
            "POST",
            f"/evaluations/{evaluation_id}/documents",
            expected_status=201,
            files=files,
        )
        return self._validate_model(response, DocumentView)

    def list_documents(
        self,
        evaluation_id: UUID,
    ) -> list[DocumentView]:
        response = self._request(
            "list_documents",
            "GET",
            f"/evaluations/{evaluation_id}/documents",
            expected_status=200,
        )
        return self._validate_list(response, DocumentView)

    def close(self) -> None:
        if self._owns_http_client and not self._http_client.is_closed:
            self._http_client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _request(
        self,
        operation: Operation,
        method: Literal["GET", "POST"],
        path: str,
        *,
        expected_status: int,
        json_payload: Mapping[str, str] | None = None,
        files: dict[str, tuple[str, BinaryIO, str]] | None = None,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        try:
            if method == "GET":
                response = self._http_client.get(url)
            else:
                response = self._http_client.post(
                    url,
                    json=json_payload,
                    files=files,
                )
        except httpx.RequestError as exc:
            raise ApiUnavailableError(API_UNAVAILABLE_MESSAGE) from exc

        if response.status_code != expected_status:
            detail = _extract_public_detail(response)
            message = KNOWN_OPERATION_ERRORS.get(
                (operation, response.status_code, detail or ""),
                OPERATION_FALLBACKS.get(
                    operation,
                    UNEXPECTED_OPERATION_MESSAGE,
                ),
            )
            raise ApiOperationError(message)

        return response

    @staticmethod
    def _validate_model(
        response: httpx.Response,
        model: type[ModelT],
    ) -> ModelT:
        try:
            payload: object = response.json()
            return model.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise ApiProtocolError(INVALID_API_RESPONSE_MESSAGE) from exc

    @staticmethod
    def _validate_list(
        response: httpx.Response,
        model: type[ModelT],
    ) -> list[ModelT]:
        try:
            payload: object = response.json()
        except ValueError as exc:
            raise ApiProtocolError(INVALID_API_RESPONSE_MESSAGE) from exc

        if not isinstance(payload, list):
            raise ApiProtocolError(INVALID_API_RESPONSE_MESSAGE)

        try:
            return [model.model_validate(item) for item in payload]
        except ValidationError as exc:
            raise ApiProtocolError(INVALID_API_RESPONSE_MESSAGE) from exc
