from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import BinaryIO, Final, Literal, Protocol, cast
from unicodedata import category
from uuid import UUID

import streamlit as st

from ui.api_client import (
    ApiClientError,
    DocumentView,
    EvaluationView,
    MeritAssistantApiClient,
    ProfileView,
)

SELECTED_EVALUATION_KEY: Final = "selected_evaluation_id"
UPLOAD_IN_PROGRESS_KEY: Final = "upload_in_progress"
UPLOAD_WIDGET_GENERATION_KEY: Final = "upload_widget_generation"
FLASH_SUCCESS_KEY: Final = "flash_success"

EVALUATION_CREATED_MESSAGE: Final = "Avaliação criada com sucesso."
DOCUMENT_UPLOADED_MESSAGE: Final = "Documento enviado com sucesso."
EXTERNAL_PROCESSING_BLOCKED_MESSAGE: Final = (
    "Processamento externo habilitado; operação bloqueada."
)
API_AVAILABLE_MESSAGE: Final = (
    "API disponível — processamento externo: desabilitado."
)
NO_PROFILES_MESSAGE: Final = "Nenhum perfil de avaliação disponível."
NO_EVALUATIONS_MESSAGE: Final = "Nenhuma avaliação criada."
NO_DOCUMENTS_MESSAGE: Final = (
    "Nenhum documento associado à avaliação."
)
CREATE_EVALUATION_FIRST_MESSAGE: Final = (
    "Crie uma avaliação antes de enviar documentos."
)
SELECT_EVALUATION_MESSAGE: Final = (
    "Selecione uma avaliação para continuar."
)
EVALUATION_SELECTOR_PLACEHOLDER: Final = (
    "Selecione uma avaliação"
)
SELECT_PDF_MESSAGE: Final = (
    "Selecione um arquivo PDF para enviar."
)
UPLOAD_IN_PROGRESS_MESSAGE: Final = (
    "Envio em andamento. Aguarde."
)
UPLOAD_FAILED_MESSAGE: Final = (
    "Não foi possível concluir o upload do documento."
)

ALLOWED_FLASH_MESSAGES: Final = frozenset(
    {
        EVALUATION_CREATED_MESSAGE,
        DOCUMENT_UPLOADED_MESSAGE,
    }
)

DEFAULT_LABEL_LIMIT: Final = 120
EMPTY_EVALUATION_TITLE: Final = "Sem título"

SessionState = MutableMapping[str, object]
DocumentRow = dict[str, object]
EvaluationRow = dict[str, object]
UploadWorkflowStatus = Literal["success", "error", "blocked"]


class UploadSource(Protocol):
    name: str
    type: str | None

    def read(self, size: int = -1) -> bytes:
        ...

    def seek(self, offset: int, whence: int = 0) -> int:
        ...

    def tell(self) -> int:
        ...


@dataclass(frozen=True, slots=True)
class UploadWorkflowResult:
    status: UploadWorkflowStatus
    public_message: str | None = None


def normalize_display_text(
    value: str,
    *,
    max_length: int = DEFAULT_LABEL_LIMIT,
) -> str:
    """Normalize user-controlled text before passing it to text widgets."""

    if max_length < 2:
        raise ValueError("max_length must be at least 2")

    without_controls = "".join(
        " " if category(character).startswith("C") else character
        for character in value
    )
    normalized = " ".join(without_controls.split())

    if not normalized:
        return EMPTY_EVALUATION_TITLE
    if len(normalized) <= max_length:
        return normalized

    truncated = normalized[: max_length - 1].rstrip()
    return f"{truncated}…"


def evaluation_option_label(evaluation: EvaluationView) -> str:
    title = normalize_display_text(evaluation.title)
    return f"{title} — {evaluation.id}"


def evaluation_option_labels(
    evaluations: Sequence[EvaluationView],
) -> dict[UUID, str]:
    return {
        evaluation.id: evaluation_option_label(evaluation)
        for evaluation in evaluations
    }


def evaluation_id_option_label(
    evaluation_id: UUID,
    *,
    labels_by_id: Mapping[UUID, str],
) -> str:
    return labels_by_id[evaluation_id]


def profile_option_label(
    profile_id: str,
    *,
    profiles_by_id: Mapping[str, ProfileView],
) -> str:
    profile = profiles_by_id[profile_id]
    return normalize_display_text(profile.name)


def resolve_selected_evaluation_id(
    evaluations: Sequence[EvaluationView],
    selected: object,
) -> UUID | None:
    if isinstance(selected, UUID):
        candidate = selected
    elif isinstance(selected, str):
        try:
            candidate = UUID(selected)
        except ValueError:
            return None
    else:
        return None

    available = {evaluation.id for evaluation in evaluations}
    return candidate if candidate in available else None


def initialize_session_state(state: SessionState) -> None:
    selected = state.get(SELECTED_EVALUATION_KEY)
    if not isinstance(selected, (UUID, str)):
        state[SELECTED_EVALUATION_KEY] = None

    in_progress = state.get(UPLOAD_IN_PROGRESS_KEY)
    if not isinstance(in_progress, bool):
        state[UPLOAD_IN_PROGRESS_KEY] = False

    generation = state.get(UPLOAD_WIDGET_GENERATION_KEY)
    if (
        not isinstance(generation, int)
        or isinstance(generation, bool)
        or generation < 0
    ):
        state[UPLOAD_WIDGET_GENERATION_KEY] = 0

    flash = state.get(FLASH_SUCCESS_KEY)
    if flash not in ALLOWED_FLASH_MESSAGES:
        state[FLASH_SUCCESS_KEY] = None


def synchronize_selected_evaluation(
    state: SessionState,
    evaluations: Sequence[EvaluationView],
) -> UUID | None:
    selected = resolve_selected_evaluation_id(
        evaluations,
        state.get(SELECTED_EVALUATION_KEY),
    )
    state[SELECTED_EVALUATION_KEY] = selected
    return selected


def select_evaluation(
    state: SessionState,
    evaluation_id: UUID,
) -> None:
    state[SELECTED_EVALUATION_KEY] = evaluation_id


def queue_success_message(
    state: SessionState,
    message: str,
) -> None:
    if message not in ALLOWED_FLASH_MESSAGES:
        raise ValueError("unsupported success message")
    state[FLASH_SUCCESS_KEY] = message


def consume_success_message(state: SessionState) -> str | None:
    message = state.get(FLASH_SUCCESS_KEY)
    state[FLASH_SUCCESS_KEY] = None
    return message if message in ALLOWED_FLASH_MESSAGES else None


def advance_upload_widget_generation(state: SessionState) -> int:
    generation = state.get(UPLOAD_WIDGET_GENERATION_KEY)
    current = (
        generation
        if isinstance(generation, int)
        and not isinstance(generation, bool)
        and generation >= 0
        else 0
    )
    updated = current + 1
    state[UPLOAD_WIDGET_GENERATION_KEY] = updated
    return updated


def upload_widget_key(state: SessionState) -> str:
    generation = state.get(UPLOAD_WIDGET_GENERATION_KEY)
    safe_generation = (
        generation
        if isinstance(generation, int)
        and not isinstance(generation, bool)
        and generation >= 0
        else 0
    )
    return f"document-upload-{safe_generation}"


def execute_document_upload(
    client: MeritAssistantApiClient,
    evaluation_id: UUID,
    source: UploadSource,
    state: SessionState,
) -> UploadWorkflowResult:
    if state.get(UPLOAD_IN_PROGRESS_KEY) is True:
        return UploadWorkflowResult(
            status="blocked",
            public_message=UPLOAD_IN_PROGRESS_MESSAGE,
        )

    state[UPLOAD_IN_PROGRESS_KEY] = True
    try:
        client.upload_document(
            evaluation_id=evaluation_id,
            filename=source.name,
            content_type=source.type,
            source=cast(BinaryIO, source),
        )
    except ApiClientError as exc:
        return UploadWorkflowResult(
            status="error",
            public_message=exc.public_message,
        )
    finally:
        state[UPLOAD_IN_PROGRESS_KEY] = False

    advance_upload_widget_generation(state)
    queue_success_message(state, DOCUMENT_UPLOADED_MESSAGE)
    return UploadWorkflowResult(status="success")


def document_table_rows(
    documents: Sequence[DocumentView],
) -> list[DocumentRow]:
    return [
        {
            "id": str(document.id),
            "evaluation_id": str(document.evaluation_id),
            "original_filename": document.original_filename,
            "content_type": document.content_type,
            "size_bytes": document.size_bytes,
            "created_at": document.created_at,
        }
        for document in documents
    ]


def evaluation_table_rows(
    evaluations: Sequence[EvaluationView],
) -> list[EvaluationRow]:
    return [
        {
            "id": str(evaluation.id),
            "title": evaluation.title,
            "profile_id": evaluation.profile_id,
            "created_at": evaluation.created_at,
        }
        for evaluation in evaluations
    ]


def render_evaluation_creation(
    client: MeritAssistantApiClient,
    profiles: Sequence[ProfileView],
    state: SessionState,
) -> None:
    st.subheader("Nova avaliação")

    if not profiles:
        st.info(NO_PROFILES_MESSAGE)
        return

    profiles_by_id = {
        profile.id: profile
        for profile in profiles
    }
    profile_ids = list(profiles_by_id)

    with st.form("create-evaluation"):
        title = st.text_input("Título da avaliação")
        selected_profile_id = st.selectbox(
            "Perfil",
            options=profile_ids,
            format_func=partial(
                profile_option_label,
                profiles_by_id=profiles_by_id,
            ),
        )
        submitted = st.form_submit_button("Criar avaliação")

    if not submitted:
        return

    try:
        evaluation = client.create_evaluation(
            title=title,
            profile_id=selected_profile_id,
        )
    except ApiClientError as exc:
        st.error(exc.public_message)
        return

    select_evaluation(state, evaluation.id)
    queue_success_message(state, EVALUATION_CREATED_MESSAGE)
    st.rerun()


def render_evaluation_list(
    evaluations: Sequence[EvaluationView],
) -> None:
    st.subheader("Avaliações")

    if not evaluations:
        st.info(NO_EVALUATIONS_MESSAGE)
        return

    st.dataframe(
        evaluation_table_rows(evaluations),
        width="stretch",
        hide_index=True,
    )


def render_evaluation_selection(
    evaluations: Sequence[EvaluationView],
    state: SessionState,
) -> UUID | None:
    st.subheader("Avaliação ativa")

    if not evaluations:
        state[SELECTED_EVALUATION_KEY] = None
        st.info(CREATE_EVALUATION_FIRST_MESSAGE)
        return None

    selected = synchronize_selected_evaluation(
        state,
        evaluations,
    )
    evaluation_ids = [
        evaluation.id
        for evaluation in evaluations
    ]
    selected_index = (
        evaluation_ids.index(selected)
        if selected is not None
        else None
    )
    labels_by_id = evaluation_option_labels(evaluations)

    selected_option: object = st.selectbox(
        "Avaliação",
        options=evaluation_ids,
        index=selected_index,
        format_func=partial(
            evaluation_id_option_label,
            labels_by_id=labels_by_id,
        ),
        placeholder=EVALUATION_SELECTOR_PLACEHOLDER,
    )
    resolved = resolve_selected_evaluation_id(
        evaluations,
        selected_option,
    )

    if resolved is None:
        state[SELECTED_EVALUATION_KEY] = None
        st.info(SELECT_EVALUATION_MESSAGE)
        return None

    select_evaluation(state, resolved)
    st.success("Avaliação selecionada.")
    return resolved


def render_document_upload(
    client: MeritAssistantApiClient,
    evaluation_id: UUID,
    state: SessionState,
) -> None:
    st.subheader("Enviar documento")

    with st.form("document-upload"):
        uploaded_file = st.file_uploader(
            "Documento PDF",
            type=["pdf"],
            accept_multiple_files=False,
            key=upload_widget_key(state),
        )
        submitted = st.form_submit_button("Enviar documento")

    if not submitted:
        return

    if uploaded_file is None:
        st.info(SELECT_PDF_MESSAGE)
        return

    result = execute_document_upload(
        client,
        evaluation_id,
        cast(UploadSource, uploaded_file),
        state,
    )

    if result.status == "blocked":
        st.info(result.public_message or UPLOAD_IN_PROGRESS_MESSAGE)
        return

    if result.status == "error":
        st.error(result.public_message or UPLOAD_FAILED_MESSAGE)
        return

    st.rerun()


def render_document_listing(
    client: MeritAssistantApiClient,
    evaluation_id: UUID,
) -> None:
    st.subheader("Documentos")

    try:
        documents = client.list_documents(evaluation_id)
    except ApiClientError as exc:
        st.error(exc.public_message)
        return

    if not documents:
        st.info(NO_DOCUMENTS_MESSAGE)
        return

    st.dataframe(
        document_table_rows(documents),
        width="stretch",
        hide_index=True,
    )


def run_app(client: MeritAssistantApiClient) -> None:
    st.title("Assistente de Avaliação de Mérito Tecnológico")
    st.caption("Iteração I-001 — fundação local, sem IA generativa")

    state = cast(SessionState, st.session_state)
    initialize_session_state(state)

    success_message = consume_success_message(state)
    if success_message is not None:
        st.success(success_message)

    try:
        health = client.health()
    except ApiClientError as exc:
        st.error(exc.public_message)
        return

    if health.external_processing_enabled:
        st.error(EXTERNAL_PROCESSING_BLOCKED_MESSAGE)
        return

    st.success(API_AVAILABLE_MESSAGE)

    try:
        profiles = client.list_profiles()
    except ApiClientError as exc:
        st.error(exc.public_message)
        profiles = []

    render_evaluation_creation(
        client,
        profiles,
        state,
    )

    try:
        evaluations = client.list_evaluations()
    except ApiClientError as exc:
        st.error(exc.public_message)
        return

    render_evaluation_list(evaluations)
    selected_evaluation_id = render_evaluation_selection(
        evaluations,
        state,
    )
    if selected_evaluation_id is not None:
        render_document_upload(
            client,
            selected_evaluation_id,
            state,
        )
        render_document_listing(
            client,
            selected_evaluation_id,
        )
