from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

from streamlit.testing.v1 import AppTest

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

EVALUATION_ID = UUID(
    "3a3c6bc1-7b2f-4f15-872c-597fd45e8bf3"
)
SECOND_EVALUATION_ID = UUID(
    "4c841937-f7bf-47a4-a1f4-7230571fc380"
)

APP_SCRIPT = """
from datetime import UTC, datetime
from uuid import UUID

import streamlit as st

from ui.api_client import (
    API_UNAVAILABLE_MESSAGE,
    ApiOperationError,
    ApiUnavailableError,
    DocumentView,
    EvaluationView,
    HealthView,
    ProfileView,
)
from ui.app import main

EVALUATION_ID = UUID("3a3c6bc1-7b2f-4f15-872c-597fd45e8bf3")
SECOND_EVALUATION_ID = UUID(
    "4c841937-f7bf-47a4-a1f4-7230571fc380"
)
FIRST_DOCUMENT_ID = UUID(
    "f6f13c39-b8ca-4f07-9f23-7583b1be337f"
)
SECOND_DOCUMENT_ID = UUID(
    "56f940f9-f19f-4dd5-a36c-b57eed07ad4b"
)
NOW = datetime(2026, 7, 31, 15, 0, tzinfo=UTC)


class FakeClient:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def health(self):
        scenario = st.session_state.get("_scenario", "ok")
        if scenario == "unavailable":
            raise ApiUnavailableError(API_UNAVAILABLE_MESSAGE)
        if scenario == "unexpected":
            raise RuntimeError("internal secret")
        return HealthView(
            status="ok",
            external_processing_enabled=scenario == "external",
        )

    def list_profiles(self):
        scenario = st.session_state.get("_scenario", "ok")
        if scenario == "profile_error":
            raise ApiOperationError(
                "Não foi possível carregar os perfis."
            )
        if scenario == "no_profiles":
            return []
        return [
            ProfileView(
                id="finep-technological-merit",
                name="Mérito tecnológico",
                version="1.0",
                status="active",
            )
        ]

    def create_evaluation(self, title, profile_id):
        scenario = st.session_state.get("_scenario", "ok")
        if scenario == "create_error":
            raise ApiOperationError(
                "Não foi possível criar a avaliação."
            )
        st.session_state["_created"] = True
        return EvaluationView(
            id=EVALUATION_ID,
            title=title,
            profile_id=profile_id,
            created_at=NOW,
        )

    def list_evaluations(self):
        scenario = st.session_state.get("_scenario", "ok")
        if scenario == "evaluation_error":
            raise ApiOperationError(
                "Não foi possível carregar as avaliações."
            )
        if scenario == "no_evaluations":
            return []
        if scenario == "duplicate_titles":
            return [
                EvaluationView(
                    id=EVALUATION_ID,
                    title="Mesmo título",
                    profile_id="finep-technological-merit",
                    created_at=NOW,
                ),
                EvaluationView(
                    id=SECOND_EVALUATION_ID,
                    title="Mesmo título",
                    profile_id="finep-technological-merit",
                    created_at=NOW,
                ),
            ]
        if st.session_state.get("_created", False):
            title = "Avaliação criada"
        else:
            title = "Avaliação sintética"
        return [
            EvaluationView(
                id=EVALUATION_ID,
                title=title,
                profile_id="finep-technological-merit",
                created_at=NOW,
            )
        ]

    def upload_document(
        self,
        evaluation_id,
        filename,
        content_type,
        source,
    ):
        raise AssertionError(
            "upload called without a selected file"
        )

    def list_documents(self, evaluation_id):
        st.session_state["_document_list_calls"] = (
            st.session_state.get("_document_list_calls", 0) + 1
        )
        scenario = st.session_state.get("_scenario", "ok")
        if scenario == "document_error":
            raise ApiOperationError(
                "Não foi possível listar os documentos."
            )
        if scenario != "documents":
            return []
        return [
            DocumentView(
                id=SECOND_DOCUMENT_ID,
                evaluation_id=evaluation_id,
                original_filename="second.pdf",
                content_type="application/pdf",
                size_bytes=64,
                created_at=NOW,
            ),
            DocumentView(
                id=FIRST_DOCUMENT_ID,
                evaluation_id=evaluation_id,
                original_filename="first.pdf",
                content_type="application/pdf",
                size_bytes=32,
                created_at=NOW,
            ),
        ]


def factory(base_url):
    assert base_url == "http://localhost:8000"
    return FakeClient()


main(client_factory=factory)
"""


def _app(
    scenario: str = "ok",
) -> AppTest:
    app = AppTest.from_string(APP_SCRIPT)
    app.session_state["_scenario"] = scenario
    return app.run()


def _messages(elements: object) -> list[str]:
    return [
        str(element.value)
        for element in elements
    ]


def test_app_renders_health_creation_and_evaluations() -> None:
    app = _app()

    assert not app.exception
    assert app.title[0].value == (
        "Assistente de Avaliação de Mérito Tecnológico"
    )
    assert "API disponível" in app.success[0].value
    assert len(app.text_input) == 1
    assert len(app.selectbox) == 2
    assert app.selectbox[1].value is None
    assert app.selectbox[1].placeholder == (
        "Selecione uma avaliação"
    )
    assert len(app.button) == 1
    assert len(app.dataframe) == 1


def test_app_stops_the_journey_when_api_is_unavailable() -> None:
    app = _app("unavailable")

    assert not app.exception
    assert _messages(app.error) == [
        "API indisponível. Verifique o ambiente local."
    ]
    assert len(app.text_input) == 0
    assert len(app.dataframe) == 0


def test_app_blocks_external_processing() -> None:
    app = _app("external")

    assert not app.exception
    assert _messages(app.error) == [
        "Processamento externo habilitado; operação bloqueada."
    ]
    assert len(app.text_input) == 0
    assert len(app.dataframe) == 0


def test_app_handles_missing_profiles_without_hiding_evaluations() -> None:
    app = _app("no_profiles")

    assert not app.exception
    assert "Nenhum perfil de avaliação disponível." in _messages(
        app.info
    )
    assert len(app.text_input) == 0
    assert len(app.dataframe) == 1


def test_app_distinguishes_an_empty_evaluation_list() -> None:
    app = _app("no_evaluations")

    assert not app.exception
    assert "Nenhuma avaliação criada." in _messages(app.info)
    assert (
        "Crie uma avaliação antes de enviar documentos."
        in _messages(app.info)
    )
    assert len(app.dataframe) == 0
    assert len(app.selectbox) == 1


def test_app_sanitizes_profile_and_evaluation_failures() -> None:
    profile_error = _app("profile_error")
    evaluation_error = _app("evaluation_error")

    assert not profile_error.exception
    assert "Não foi possível carregar os perfis." in _messages(
        profile_error.error
    )
    assert not evaluation_error.exception
    assert _messages(evaluation_error.error) == [
        "Não foi possível carregar as avaliações."
    ]


def test_app_sanitizes_an_unexpected_failure() -> None:
    app = _app("unexpected")

    assert not app.exception
    assert _messages(app.error) == [
        "Não foi possível concluir a operação."
    ]
    assert "internal secret" not in str(app)


def test_create_evaluation_error_is_safe_and_does_not_rerun() -> None:
    app = _app("create_error")
    app.text_input[0].input("Avaliação nova").run()
    app.button[0].click().run()

    assert not app.exception
    assert "Não foi possível criar a avaliação." in _messages(
        app.error
    )
    assert "Avaliação criada com sucesso." not in _messages(
        app.success
    )


def test_create_evaluation_queues_one_success_message() -> None:
    app = _app()
    app.text_input[0].input("Avaliação nova").run()
    app.button[0].click().run()

    assert not app.exception
    assert _messages(app.success).count(
        "Avaliação criada com sucesso."
    ) == 1
    assert str(
        app.session_state["selected_evaluation_id"]
    ) == str(EVALUATION_ID)
    assert str(app.selectbox[1].value) == str(EVALUATION_ID)


def test_duplicate_titles_have_distinct_full_uuid_labels() -> None:
    app = _app("duplicate_titles")

    assert not app.exception
    assert app.selectbox[1].options == [
        f"Mesmo título — {EVALUATION_ID}",
        f"Mesmo título — {SECOND_EVALUATION_ID}",
    ]
    assert app.selectbox[1].value is None


def test_explicit_selection_is_persisted_across_reruns() -> None:
    app = _app("duplicate_titles")

    app.selectbox[1].select_index(1).run()

    assert not app.exception
    assert str(
        app.session_state["selected_evaluation_id"]
    ) == str(SECOND_EVALUATION_ID)
    assert str(app.selectbox[1].value) == str(
        SECOND_EVALUATION_ID
    )
    assert "Avaliação selecionada." in _messages(app.success)

    app.run()

    assert str(app.selectbox[1].value) == str(
        SECOND_EVALUATION_ID
    )



def test_upload_form_is_hidden_until_an_evaluation_is_selected() -> None:
    app = _app()

    assert not app.exception
    assert [button.label for button in app.button] == [
        "Criar avaliação"
    ]


def test_upload_form_requires_a_pdf_before_calling_the_client() -> None:
    app = _app()
    app.selectbox[1].select_index(0).run()

    assert not app.exception
    assert [button.label for button in app.button] == [
        "Criar avaliação",
        "Enviar documento",
    ]

    app.button[1].click().run()

    assert not app.exception
    assert "Selecione um arquivo PDF para enviar." in _messages(
        app.info
    )
    assert app.session_state["upload_in_progress"] is False
    assert app.session_state["upload_widget_generation"] == 0



def test_document_listing_is_hidden_without_selection() -> None:
    app = _app()

    assert not app.exception
    assert "Documentos" not in _messages(app.subheader)
    assert "_document_list_calls" not in app.session_state


def test_selected_evaluation_with_no_documents_is_an_empty_success() -> None:
    app = _app()
    app.selectbox[1].select_index(0).run()

    assert not app.exception
    assert "Documentos" in _messages(app.subheader)
    assert (
        "Nenhum documento associado à avaliação."
        in _messages(app.info)
    )
    assert app.session_state["_document_list_calls"] == 1


def test_document_listing_error_is_not_rendered_as_empty() -> None:
    app = _app("document_error")
    app.selectbox[1].select_index(0).run()

    assert not app.exception
    assert "Não foi possível listar os documentos." in _messages(
        app.error
    )
    assert (
        "Nenhum documento associado à avaliação."
        not in _messages(app.info)
    )


def test_document_listing_preserves_order_and_six_public_fields() -> None:
    app = _app("documents")
    app.selectbox[1].select_index(0).run()

    assert not app.exception
    assert len(app.dataframe) == 2

    documents = app.dataframe[1].value
    assert list(documents.columns) == [
        "id",
        "evaluation_id",
        "original_filename",
        "content_type",
        "size_bytes",
        "created_at",
    ]
    assert list(documents["original_filename"]) == [
        "second.pdf",
        "first.pdf",
    ]
