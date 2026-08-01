from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.api_client import (  # noqa: E402
    UNEXPECTED_OPERATION_MESSAGE,
    ApiClientError,
    MeritAssistantApiClient,
)
from ui.presentation import run_app  # noqa: E402

DEFAULT_API_BASE_URL = "http://localhost:8000"
ClientFactory = Callable[[str], MeritAssistantApiClient]


def main(
    client_factory: ClientFactory = MeritAssistantApiClient,
) -> None:
    st.set_page_config(
        page_title="Avaliação de Mérito Tecnológico",
        layout="wide",
    )

    api_base_url = os.getenv(
        "API_BASE_URL",
        DEFAULT_API_BASE_URL,
    )

    try:
        with client_factory(api_base_url) as client:
            run_app(client)
    except ApiClientError as exc:
        st.error(exc.public_message)
    except Exception:
        st.error(UNEXPECTED_OPERATION_MESSAGE)


if __name__ == "__main__":
    main()
