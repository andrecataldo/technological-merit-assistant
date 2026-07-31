from __future__ import annotations

import sys
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ui.api_client import (  # noqa: E402
    ApiOperationError,
    DocumentView,
    EvaluationView,
    ProfileView,
)
from ui.presentation import (  # noqa: E402
    DOCUMENT_UPLOADED_MESSAGE,
    EMPTY_EVALUATION_TITLE,
    EVALUATION_CREATED_MESSAGE,
    FLASH_SUCCESS_KEY,
    SELECTED_EVALUATION_KEY,
    UPLOAD_IN_PROGRESS_KEY,
    UPLOAD_IN_PROGRESS_MESSAGE,
    UPLOAD_WIDGET_GENERATION_KEY,
    advance_upload_widget_generation,
    consume_success_message,
    document_table_rows,
    evaluation_id_option_label,
    evaluation_option_label,
    evaluation_option_labels,
    evaluation_table_rows,
    execute_document_upload,
    initialize_session_state,
    normalize_display_text,
    profile_option_label,
    queue_success_message,
    resolve_selected_evaluation_id,
    select_evaluation,
    synchronize_selected_evaluation,
    upload_widget_key,
)

FIRST_EVALUATION_ID = UUID("3a3c6bc1-7b2f-4f15-872c-597fd45e8bf3")
SECOND_EVALUATION_ID = UUID("4c841937-f7bf-47a4-a1f4-7230571fc380")
FIRST_DOCUMENT_ID = UUID("f6f13c39-b8ca-4f07-9f23-7583b1be337f")
SECOND_DOCUMENT_ID = UUID("56f940f9-f19f-4dd5-a36c-b57eed07ad4b")
NOW = datetime(2026, 7, 31, 15, 0, tzinfo=UTC)


def _evaluation(
    evaluation_id: UUID,
    *,
    title: str = "Avaliação sintética",
) -> EvaluationView:
    return EvaluationView(
        id=evaluation_id,
        title=title,
        profile_id="finep-technological-merit",
        created_at=NOW,
    )


def _document(
    document_id: UUID,
    *,
    evaluation_id: UUID = FIRST_EVALUATION_ID,
    filename: str = "synthetic.pdf",
) -> DocumentView:
    return DocumentView(
        id=document_id,
        evaluation_id=evaluation_id,
        original_filename=filename,
        content_type="application/pdf",
        size_bytes=32,
        created_at=NOW,
    )


def test_normalize_display_text_removes_controls_and_collapses_space() -> None:
    observed = normalize_display_text(
        "  Avaliação\n\tcom\u0000 controle  "
    )

    assert observed == "Avaliação com controle"


def test_normalize_display_text_preserves_unicode_and_markup_as_text() -> None:
    observed = normalize_display_text(
        "Mérito <script>alert(1)</script> 🚀"
    )

    assert observed == "Mérito <script>alert(1)</script> 🚀"


def test_normalize_display_text_uses_safe_empty_label() -> None:
    assert normalize_display_text("\n\t\u0000") == EMPTY_EVALUATION_TITLE


def test_normalize_display_text_truncates_without_exceeding_limit() -> None:
    observed = normalize_display_text("a" * 200, max_length=20)

    assert observed == f"{'a' * 19}…"
    assert len(observed) == 20


def test_normalize_display_text_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError):
        normalize_display_text("title", max_length=1)


def test_profile_option_label_normalizes_the_public_name() -> None:
    profile = ProfileView(
        id="finep-technological-merit",
        name="Mérito\n tecnológico",
        version="1.0",
        status="active",
    )

    assert profile_option_label(
        profile.id,
        profiles_by_id={profile.id: profile},
    ) == "Mérito tecnológico"


def test_evaluation_option_label_contains_safe_title_and_full_uuid() -> None:
    evaluation = _evaluation(
        FIRST_EVALUATION_ID,
        title="Título\ncontrolado",
    )

    assert evaluation_option_label(evaluation) == (
        f"Título controlado — {FIRST_EVALUATION_ID}"
    )


def test_duplicate_titles_remain_distinguishable_by_uuid() -> None:
    evaluations = [
        _evaluation(FIRST_EVALUATION_ID, title="Mesmo título"),
        _evaluation(SECOND_EVALUATION_ID, title="Mesmo título"),
    ]

    labels = evaluation_option_labels(evaluations)

    assert list(labels) == [FIRST_EVALUATION_ID, SECOND_EVALUATION_ID]
    assert labels[FIRST_EVALUATION_ID] != labels[SECOND_EVALUATION_ID]
    assert str(FIRST_EVALUATION_ID) in labels[FIRST_EVALUATION_ID]
    assert str(SECOND_EVALUATION_ID) in labels[SECOND_EVALUATION_ID]


def test_evaluation_id_option_label_uses_the_precomputed_label() -> None:
    labels = {
        FIRST_EVALUATION_ID: (
            f"Avaliação sintética — {FIRST_EVALUATION_ID}"
        )
    }

    assert evaluation_id_option_label(
        FIRST_EVALUATION_ID,
        labels_by_id=labels,
    ) == labels[FIRST_EVALUATION_ID]


@pytest.mark.parametrize(
    "selected",
    [
        FIRST_EVALUATION_ID,
        str(FIRST_EVALUATION_ID),
    ],
)
def test_resolve_selected_evaluation_id_keeps_available_selection(
    selected: object,
) -> None:
    evaluations = [_evaluation(FIRST_EVALUATION_ID)]

    assert resolve_selected_evaluation_id(
        evaluations,
        selected,
    ) == FIRST_EVALUATION_ID


@pytest.mark.parametrize(
    "selected",
    [
        None,
        "not-a-uuid",
        SECOND_EVALUATION_ID,
        123,
    ],
)
def test_resolve_selected_evaluation_id_discards_invalid_selection(
    selected: object,
) -> None:
    evaluations = [_evaluation(FIRST_EVALUATION_ID)]

    assert resolve_selected_evaluation_id(evaluations, selected) is None


def test_initialize_session_state_uses_only_non_document_defaults() -> None:
    state: dict[str, object] = {}

    initialize_session_state(state)

    assert state == {
        SELECTED_EVALUATION_KEY: None,
        UPLOAD_IN_PROGRESS_KEY: False,
        UPLOAD_WIDGET_GENERATION_KEY: 0,
        FLASH_SUCCESS_KEY: None,
    }
    assert not any(
        isinstance(value, (bytes, bytearray, memoryview))
        for value in state.values()
    )


def test_initialize_session_state_repairs_unsafe_values() -> None:
    state: dict[str, object] = {
        SELECTED_EVALUATION_KEY: b"document bytes",
        UPLOAD_IN_PROGRESS_KEY: "yes",
        UPLOAD_WIDGET_GENERATION_KEY: True,
        FLASH_SUCCESS_KEY: "internal trace",
    }

    initialize_session_state(state)

    assert state == {
        SELECTED_EVALUATION_KEY: None,
        UPLOAD_IN_PROGRESS_KEY: False,
        UPLOAD_WIDGET_GENERATION_KEY: 0,
        FLASH_SUCCESS_KEY: None,
    }


def test_synchronize_selected_evaluation_updates_state() -> None:
    state: dict[str, object] = {
        SELECTED_EVALUATION_KEY: str(FIRST_EVALUATION_ID),
    }

    selected = synchronize_selected_evaluation(
        state,
        [_evaluation(FIRST_EVALUATION_ID)],
    )

    assert selected == FIRST_EVALUATION_ID
    assert state[SELECTED_EVALUATION_KEY] == FIRST_EVALUATION_ID


def test_synchronize_selected_evaluation_clears_missing_selection() -> None:
    state: dict[str, object] = {
        SELECTED_EVALUATION_KEY: SECOND_EVALUATION_ID,
    }

    assert synchronize_selected_evaluation(
        state,
        [_evaluation(FIRST_EVALUATION_ID)],
    ) is None
    assert state[SELECTED_EVALUATION_KEY] is None


def test_select_evaluation_stores_only_the_uuid() -> None:
    state: dict[str, object] = {}

    select_evaluation(state, FIRST_EVALUATION_ID)

    assert state == {SELECTED_EVALUATION_KEY: FIRST_EVALUATION_ID}


@pytest.mark.parametrize(
    "message",
    [
        EVALUATION_CREATED_MESSAGE,
        DOCUMENT_UPLOADED_MESSAGE,
    ],
)
def test_success_message_is_consumed_exactly_once(message: str) -> None:
    state: dict[str, object] = {}

    queue_success_message(state, message)

    assert consume_success_message(state) == message
    assert consume_success_message(state) is None
    assert state[FLASH_SUCCESS_KEY] is None


def test_queue_success_message_rejects_unapproved_text() -> None:
    state: dict[str, object] = {}

    with pytest.raises(ValueError):
        queue_success_message(state, "SQL trace")

    assert state == {}


def test_advance_upload_widget_generation_is_monotonic() -> None:
    state: dict[str, object] = {}

    assert advance_upload_widget_generation(state) == 1
    assert upload_widget_key(state) == "document-upload-1"
    assert advance_upload_widget_generation(state) == 2
    assert upload_widget_key(state) == "document-upload-2"


def test_upload_widget_generation_repairs_invalid_state() -> None:
    state: dict[str, object] = {
        UPLOAD_WIDGET_GENERATION_KEY: -5,
    }

    assert upload_widget_key(state) == "document-upload-0"
    assert advance_upload_widget_generation(state) == 1


def test_document_table_rows_use_exact_public_fields_and_order() -> None:
    documents = [
        _document(FIRST_DOCUMENT_ID, filename="first.pdf"),
        _document(SECOND_DOCUMENT_ID, filename="second.pdf"),
    ]

    rows = document_table_rows(documents)

    assert [row["original_filename"] for row in rows] == [
        "first.pdf",
        "second.pdf",
    ]
    assert [set(row) for row in rows] == [
        {
            "id",
            "evaluation_id",
            "original_filename",
            "content_type",
            "size_bytes",
            "created_at",
        },
        {
            "id",
            "evaluation_id",
            "original_filename",
            "content_type",
            "size_bytes",
            "created_at",
        },
    ]
    assert rows[0]["id"] == str(FIRST_DOCUMENT_ID)
    assert rows[0]["evaluation_id"] == str(FIRST_EVALUATION_ID)
    assert rows[0]["created_at"] == NOW


def test_document_table_rows_accept_an_empty_sequence() -> None:
    assert document_table_rows([]) == []


def test_evaluation_table_rows_preserve_order_and_public_fields() -> None:
    evaluations = [
        _evaluation(FIRST_EVALUATION_ID, title="Primeira"),
        _evaluation(SECOND_EVALUATION_ID, title="Segunda"),
    ]

    rows = evaluation_table_rows(evaluations)

    assert [row["title"] for row in rows] == [
        "Primeira",
        "Segunda",
    ]
    assert [set(row) for row in rows] == [
        {
            "id",
            "title",
            "profile_id",
            "created_at",
        },
        {
            "id",
            "title",
            "profile_id",
            "created_at",
        },
    ]


class SyntheticUpload(BytesIO):
    name: str
    type: str | None

    def __init__(
        self,
        content: bytes,
        *,
        name: str = "synthetic.pdf",
        content_type: str | None = "application/pdf",
    ) -> None:
        super().__init__(content)
        self.name = name
        self.type = content_type


class FakeUploadClient:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str, str | None, object]] = []
        self.error: Exception | None = None

    def upload_document(
        self,
        evaluation_id: UUID,
        filename: str,
        content_type: str | None,
        source: object,
    ) -> DocumentView:
        self.calls.append(
            (
                evaluation_id,
                filename,
                content_type,
                source,
            )
        )
        if self.error is not None:
            raise self.error
        return _document(
            FIRST_DOCUMENT_ID,
            evaluation_id=evaluation_id,
            filename=filename,
        )


def test_execute_document_upload_calls_the_client_once() -> None:
    client = FakeUploadClient()
    source = SyntheticUpload(b"%PDF-1.7\n%%EOF")
    state: dict[str, object] = {}

    result = execute_document_upload(
        client,  # type: ignore[arg-type]
        FIRST_EVALUATION_ID,
        source,
        state,
    )

    assert result.status == "success"
    assert result.public_message is None
    assert client.calls == [
        (
            FIRST_EVALUATION_ID,
            "synthetic.pdf",
            "application/pdf",
            source,
        )
    ]
    assert state[UPLOAD_IN_PROGRESS_KEY] is False
    assert state[UPLOAD_WIDGET_GENERATION_KEY] == 1
    assert state[FLASH_SUCCESS_KEY] == DOCUMENT_UPLOADED_MESSAGE
    assert source.closed is False
    assert source not in state.values()
    assert not any(
        isinstance(value, (bytes, bytearray, memoryview))
        for value in state.values()
    )


def test_execute_document_upload_forwards_missing_content_type() -> None:
    client = FakeUploadClient()
    source = SyntheticUpload(
        b"%PDF-1.7\n%%EOF",
        content_type=None,
    )
    state: dict[str, object] = {}

    result = execute_document_upload(
        client,  # type: ignore[arg-type]
        FIRST_EVALUATION_ID,
        source,
        state,
    )

    assert result.status == "success"
    assert client.calls[0][2] is None


def test_execute_document_upload_blocks_an_active_submission() -> None:
    client = FakeUploadClient()
    source = SyntheticUpload(b"%PDF-1.7\n%%EOF")
    state: dict[str, object] = {
        UPLOAD_IN_PROGRESS_KEY: True,
    }

    result = execute_document_upload(
        client,  # type: ignore[arg-type]
        FIRST_EVALUATION_ID,
        source,
        state,
    )

    assert result.status == "blocked"
    assert result.public_message == UPLOAD_IN_PROGRESS_MESSAGE
    assert client.calls == []
    assert state == {UPLOAD_IN_PROGRESS_KEY: True}


def test_execute_document_upload_returns_a_safe_api_error() -> None:
    client = FakeUploadClient()
    client.error = ApiOperationError(
        "O arquivo enviado não é um PDF válido."
    )
    source = SyntheticUpload(b"not-a-pdf")
    state: dict[str, object] = {}

    result = execute_document_upload(
        client,  # type: ignore[arg-type]
        FIRST_EVALUATION_ID,
        source,
        state,
    )

    assert result.status == "error"
    assert result.public_message == (
        "O arquivo enviado não é um PDF válido."
    )
    assert len(client.calls) == 1
    assert state == {UPLOAD_IN_PROGRESS_KEY: False}


def test_execute_document_upload_restores_flag_on_unexpected_error() -> None:
    client = FakeUploadClient()
    client.error = RuntimeError("internal path")
    source = SyntheticUpload(b"%PDF-1.7\n%%EOF")
    state: dict[str, object] = {}

    with pytest.raises(RuntimeError, match="internal path"):
        execute_document_upload(
            client,  # type: ignore[arg-type]
            FIRST_EVALUATION_ID,
            source,
            state,
        )

    assert state == {UPLOAD_IN_PROGRESS_KEY: False}
    assert source not in state.values()
