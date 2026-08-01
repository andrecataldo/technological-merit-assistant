from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ui.api_client import (  # noqa: E402
    API_UNAVAILABLE_MESSAGE,
    INVALID_API_CONFIGURATION_MESSAGE,
    INVALID_API_RESPONSE_MESSAGE,
    INVALID_HTTP_CLIENT_MESSAGE,
    ApiConfigurationError,
    ApiOperationError,
    ApiProtocolError,
    ApiUnavailableError,
    DocumentView,
    EvaluationView,
    HealthView,
    MeritAssistantApiClient,
    ProfileView,
    validate_local_api_base_url,
)

NOW = datetime(2026, 7, 31, 15, 0, tzinfo=UTC)
EVALUATION_ID = UUID("3a3c6bc1-7b2f-4f15-872c-597fd45e8bf3")
DOCUMENT_ID = UUID("f6f13c39-b8ca-4f07-9f23-7583b1be337f")


def _response(
    status_code: int,
    *,
    json: object | None = None,
    text: str | None = None,
) -> httpx.Response:
    request = httpx.Request("GET", "http://localhost:8000/test")
    if text is not None:
        return httpx.Response(
            status_code,
            text=text,
            request=request,
        )
    return httpx.Response(
        status_code,
        json=json,
        request=request,
    )


def _evaluation_payload() -> dict[str, object]:
    return {
        "id": str(EVALUATION_ID),
        "title": "Avaliação sintética",
        "profile_id": "finep-technological-merit",
        "created_at": NOW.isoformat(),
    }


def _document_payload() -> dict[str, object]:
    return {
        "id": str(DOCUMENT_ID),
        "evaluation_id": str(EVALUATION_ID),
        "original_filename": "synthetic.pdf",
        "content_type": "application/pdf",
        "size_bytes": 32,
        "created_at": NOW.isoformat(),
    }


def _mock_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> tuple[MeritAssistantApiClient, httpx.Client]:
    injected = httpx.Client(
        transport=httpx.MockTransport(handler),
        timeout=5.0,
        follow_redirects=False,
    )
    return (
        MeritAssistantApiClient(
            "http://localhost:8000",
            http_client=injected,
        ),
        injected,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("http://localhost:8000", "http://localhost:8000"),
        ("http://localhost:8000/", "http://localhost:8000"),
        ("HTTP://LOCALHOST:8000", "http://localhost:8000"),
        ("http://127.0.0.1:8000", "http://127.0.0.1:8000"),
        ("http://[::1]:8000", "http://[::1]:8000"),
        ("http://api:8000", "http://api:8000"),
    ],
)
def test_validate_local_api_base_url_accepts_only_local_targets(
    value: str,
    expected: str,
) -> None:
    assert validate_local_api_base_url(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        " http://localhost:8000",
        "http://localhost:8000 ",
        "https://localhost:8000",
        "http://example.com:8000",
        "http://localhost",
        "http://localhost:8001",
        "http://user@localhost:8000",
        "http://user:secret@localhost:8000",
        "http://localhost:8000/api",
        "http://localhost:8000?target=external",
        "http://localhost:8000#fragment",
        "file:///tmp/api",
        "http://[::1",
        "http://localhost:not-a-port",
    ],
)
def test_validate_local_api_base_url_rejects_unsafe_targets(
    value: str,
) -> None:
    with pytest.raises(ApiConfigurationError) as captured:
        validate_local_api_base_url(value)

    assert captured.value.public_message == (
        INVALID_API_CONFIGURATION_MESSAGE
    )
    assert str(captured.value) == INVALID_API_CONFIGURATION_MESSAGE


def test_public_models_reject_extra_fields() -> None:
    with pytest.raises(ValidationError):
        HealthView.model_validate(
            {
                "status": "ok",
                "external_processing_enabled": False,
                "internal": "hidden",
            }
        )


def test_public_models_reject_missing_fields() -> None:
    with pytest.raises(ValidationError):
        DocumentView.model_validate(
            {
                "id": str(uuid4()),
                "evaluation_id": str(uuid4()),
                "original_filename": "synthetic.pdf",
                "content_type": "application/pdf",
                "size_bytes": 32,
            }
        )


def test_public_models_validate_the_existing_contracts() -> None:
    health = HealthView.model_validate(
        {
            "status": "ok",
            "external_processing_enabled": False,
        }
    )
    profile = ProfileView.model_validate(
        {
            "id": "technological-merit",
            "name": "Mérito tecnológico",
            "version": "1.0",
            "status": "active",
        }
    )
    evaluation = EvaluationView.model_validate(_evaluation_payload())
    document = DocumentView.model_validate(_document_payload())

    assert health.external_processing_enabled is False
    assert profile.status == "active"
    assert evaluation.id == EVALUATION_ID
    assert document.evaluation_id == EVALUATION_ID


def test_client_canonicalizes_base_url_and_owns_finite_client() -> None:
    client = MeritAssistantApiClient("http://LOCALHOST:8000/")

    owned_http_client = client._http_client

    assert client.base_url == "http://localhost:8000"
    assert owned_http_client.follow_redirects is False
    assert owned_http_client.timeout.connect == 5.0
    assert owned_http_client.timeout.read == 30.0
    assert owned_http_client.timeout.write == 60.0
    assert owned_http_client.timeout.pool == 5.0
    assert owned_http_client.is_closed is False

    client.close()

    assert owned_http_client.is_closed is True


def test_context_manager_closes_only_an_owned_client() -> None:
    client = MeritAssistantApiClient("http://localhost:8000")
    owned_http_client = client._http_client

    with client as entered:
        assert entered is client

    assert owned_http_client.is_closed is True


def test_context_manager_does_not_close_an_injected_client() -> None:
    injected = httpx.Client(
        timeout=5.0,
        follow_redirects=False,
    )

    with MeritAssistantApiClient(
        "http://localhost:8000",
        http_client=injected,
    ):
        pass

    assert injected.is_closed is False
    injected.close()


@pytest.mark.parametrize(
    "client",
    [
        httpx.Client(timeout=None, follow_redirects=False),
        httpx.Client(timeout=5.0, follow_redirects=True),
    ],
)
def test_client_rejects_unsafe_injected_client(
    client: httpx.Client,
) -> None:
    try:
        with pytest.raises(ApiConfigurationError) as captured:
            MeritAssistantApiClient(
                "http://localhost:8000",
                http_client=client,
            )

        assert captured.value.public_message == INVALID_HTTP_CLIENT_MESSAGE
        assert client.is_closed is False
    finally:
        client.close()


def test_health_calls_the_exact_endpoint_and_validates_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == httpx.URL("http://localhost:8000/health")
        return _response(
            200,
            json={
                "status": "ok",
                "external_processing_enabled": False,
            },
        )

    client, injected = _mock_client(handler)
    try:
        assert client.health() == HealthView(
            status="ok",
            external_processing_enabled=False,
        )
    finally:
        injected.close()


def test_list_profiles_preserves_api_order() -> None:
    payload = [
        {
            "id": "first",
            "name": "Primeiro",
            "version": "1.0",
            "status": "active",
        },
        {
            "id": "second",
            "name": "Segundo",
            "version": "1.0",
            "status": "active",
        },
    ]

    client, injected = _mock_client(
        lambda request: _response(200, json=payload)
    )
    try:
        assert [item.id for item in client.list_profiles()] == [
            "first",
            "second",
        ]
    finally:
        injected.close()


def test_create_evaluation_sends_the_exact_public_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == httpx.URL("http://localhost:8000/evaluations")
        assert json.loads(request.read().decode("utf-8")) == {
            "title": "Avaliação sintética",
            "profile_id": "finep-technological-merit",
        }
        return _response(201, json=_evaluation_payload())

    client, injected = _mock_client(handler)
    try:
        result = client.create_evaluation(
            "Avaliação sintética",
            "finep-technological-merit",
        )
        assert result.id == EVALUATION_ID
    finally:
        injected.close()


def test_list_evaluations_accepts_an_empty_list() -> None:
    client, injected = _mock_client(
        lambda request: _response(200, json=[])
    )
    try:
        assert client.list_evaluations() == []
    finally:
        injected.close()


def test_upload_document_uses_exact_path_field_and_stream() -> None:
    source = BytesIO(b"%PDF-1.7\nsynthetic")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == httpx.URL(
            f"http://localhost:8000/evaluations/{EVALUATION_ID}/documents"
        )
        body = request.read()
        assert b'name="file"' in body
        assert b'filename="synthetic.pdf"' in body
        assert b"Content-Type: application/pdf" in body
        assert b"%PDF-1.7\nsynthetic" in body
        return _response(201, json=_document_payload())

    client, injected = _mock_client(handler)
    try:
        result = client.upload_document(
            EVALUATION_ID,
            "synthetic.pdf",
            "application/pdf",
            source,
        )
        assert result.id == DOCUMENT_ID
        assert source.closed is False
    finally:
        injected.close()


def test_upload_document_uses_safe_fallback_content_type() -> None:
    source = BytesIO(b"%PDF-1.7\nsynthetic")

    def handler(request: httpx.Request) -> httpx.Response:
        assert b"Content-Type: application/octet-stream" in request.read()
        return _response(201, json=_document_payload())

    client, injected = _mock_client(handler)
    try:
        client.upload_document(
            EVALUATION_ID,
            "synthetic.pdf",
            None,
            source,
        )
    finally:
        injected.close()


def test_list_documents_preserves_api_order() -> None:
    first = _document_payload()
    second = {
        **_document_payload(),
        "id": str(uuid4()),
        "original_filename": "second.pdf",
    }
    client, injected = _mock_client(
        lambda request: _response(200, json=[first, second])
    )
    try:
        assert [
            item.original_filename
            for item in client.list_documents(EVALUATION_ID)
        ] == ["synthetic.pdf", "second.pdf"]
    finally:
        injected.close()


@pytest.mark.parametrize(
    ("method_name", "payload"),
    [
        (
            "health",
            {
                "status": "ok",
                "external_processing_enabled": False,
                "secret": "hidden",
            },
        ),
        (
            "list_profiles",
            [
                {
                    "id": "profile",
                    "name": "Profile",
                    "version": "1.0",
                    "status": "active",
                    "secret": "hidden",
                }
            ],
        ),
    ],
)
def test_success_response_with_extra_fields_is_rejected(
    method_name: str,
    payload: object,
) -> None:
    client, injected = _mock_client(
        lambda request: _response(200, json=payload)
    )
    try:
        with pytest.raises(ApiProtocolError) as captured:
            getattr(client, method_name)()

        assert captured.value.public_message == INVALID_API_RESPONSE_MESSAGE
    finally:
        injected.close()


@pytest.mark.parametrize(
    "payload",
    [
        {"unexpected": "object"},
        "unexpected",
        None,
    ],
)
def test_list_response_requires_an_array(payload: object) -> None:
    client, injected = _mock_client(
        lambda request: _response(200, json=payload)
    )
    try:
        with pytest.raises(ApiProtocolError) as captured:
            client.list_evaluations()

        assert captured.value.public_message == INVALID_API_RESPONSE_MESSAGE
    finally:
        injected.close()


def test_invalid_json_success_response_is_sanitized() -> None:
    client, injected = _mock_client(
        lambda request: _response(
            200,
            text="<html>proxy failure and internal path /private</html>",
        )
    )
    try:
        with pytest.raises(ApiProtocolError) as captured:
            client.health()

        assert str(captured.value) == INVALID_API_RESPONSE_MESSAGE
        assert "proxy" not in str(captured.value)
        assert "/private" not in str(captured.value)
    finally:
        injected.close()


@pytest.mark.parametrize(
    ("status_code", "detail", "expected"),
    [
        (404, "Avaliação não encontrada.", "Avaliação não encontrada."),
        (
            409,
            "Documento já associado à avaliação.",
            "Documento já associado à avaliação.",
        ),
        (
            413,
            "O documento excede o limite permitido.",
            "O documento excede o limite permitido.",
        ),
        (
            415,
            "Tipo de conteúdo não suportado.",
            "Tipo de conteúdo não suportado.",
        ),
        (422, "Nome de arquivo inválido.", "Nome de arquivo inválido."),
        (422, "O documento está vazio.", "O documento está vazio."),
        (
            422,
            "O arquivo enviado não é um PDF válido.",
            "O arquivo enviado não é um PDF válido.",
        ),
        (
            422,
            "Não foi possível processar o arquivo enviado.",
            "Não foi possível processar o arquivo enviado.",
        ),
    ],
)
def test_upload_maps_only_known_status_and_detail_combinations(
    status_code: int,
    detail: str,
    expected: str,
) -> None:
    client, injected = _mock_client(
        lambda request: _response(
            status_code,
            json={"detail": detail},
        )
    )
    try:
        with pytest.raises(ApiOperationError) as captured:
            client.upload_document(
                EVALUATION_ID,
                "synthetic.pdf",
                "application/pdf",
                BytesIO(b"%PDF"),
            )

        assert captured.value.public_message == expected
    finally:
        injected.close()


def test_unknown_upload_detail_uses_generic_fallback() -> None:
    client, injected = _mock_client(
        lambda request: _response(
            422,
            json={"detail": "SQL constraint and /private/path"},
        )
    )
    try:
        with pytest.raises(ApiOperationError) as captured:
            client.upload_document(
                EVALUATION_ID,
                "synthetic.pdf",
                "application/pdf",
                BytesIO(b"%PDF"),
            )

        assert str(captured.value) == (
            "Não foi possível concluir o upload do documento."
        )
        assert "SQL" not in str(captured.value)
        assert "/private" not in str(captured.value)
    finally:
        injected.close()


def test_list_documents_maps_the_approved_english_404() -> None:
    client, injected = _mock_client(
        lambda request: _response(
            404,
            json={"detail": "Evaluation not found."},
        )
    )
    try:
        with pytest.raises(ApiOperationError) as captured:
            client.list_documents(EVALUATION_ID)

        assert str(captured.value) == "Avaliação não encontrada."
    finally:
        injected.close()


def test_create_evaluation_maps_only_the_known_profile_error() -> None:
    client, injected = _mock_client(
        lambda request: _response(
            400,
            json={"detail": "Perfil de avaliação desconhecido."},
        )
    )
    try:
        with pytest.raises(ApiOperationError) as captured:
            client.create_evaluation("Título", "unknown")

        assert str(captured.value) == "Perfil de avaliação desconhecido."
    finally:
        injected.close()


def test_error_body_that_is_not_json_uses_operation_fallback() -> None:
    client, injected = _mock_client(
        lambda request: _response(
            500,
            text="<html>database password and stack trace</html>",
        )
    )
    try:
        with pytest.raises(ApiOperationError) as captured:
            client.list_documents(EVALUATION_ID)

        assert str(captured.value) == "Não foi possível listar os documentos."
        assert "password" not in str(captured.value)
        assert "stack" not in str(captured.value)
    finally:
        injected.close()


@pytest.mark.parametrize(
    "exception",
    [
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("timeout"),
    ],
)
def test_transport_failures_are_sanitized(
    exception: httpx.RequestError,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    client, injected = _mock_client(handler)
    try:
        with pytest.raises(ApiUnavailableError) as captured:
            client.health()

        assert str(captured.value) == API_UNAVAILABLE_MESSAGE
        assert "refused" not in str(captured.value)
        assert "timeout" not in str(captured.value).lower()
        assert captured.value.__cause__ is exception
    finally:
        injected.close()


def test_client_does_not_follow_redirects() -> None:
    client, injected = _mock_client(
        lambda request: _response(
            307,
            json={"detail": "redirect"},
        )
    )
    try:
        with pytest.raises(ApiOperationError) as captured:
            client.health()

        assert str(captured.value) == API_UNAVAILABLE_MESSAGE
    finally:
        injected.close()
