from __future__ import annotations

import ast
from pathlib import Path

UI_ROOT = Path("ui")

ALLOWED_UI_MODULES = {
    "__init__.py",
    "api_client.py",
    "app.py",
    "presentation.py",
}

FORBIDDEN_IMPORT_PREFIXES = (
    "alembic",
    "psycopg",
    "sqlalchemy",
    "merit_assistant.application",
    "merit_assistant.domain",
    "merit_assistant.infrastructure",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)

    return modules


def test_ui_python_surface_is_restricted_to_the_approved_modules() -> None:
    observed = {
        path.name
        for path in UI_ROOT.glob("*.py")
        if path.is_file()
    }

    assert observed <= ALLOWED_UI_MODULES


def test_ui_does_not_import_backend_internal_layers() -> None:
    violations: list[str] = []

    for path in sorted(UI_ROOT.glob("*.py")):
        for module in sorted(_imported_modules(path)):
            if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                violations.append(f"{path}:{module}")

    assert violations == []


def test_api_client_does_not_reference_private_storage_or_write_files() -> None:
    path = UI_ROOT / "api_client.py"
    source = path.read_text(encoding="utf-8")

    forbidden_fragments = (
        "data/private",
        "storage_key",
        "sha256",
        "Path.write_",
        "open(",
    )

    assert [
        fragment
        for fragment in forbidden_fragments
        if fragment in source
    ] == []


def test_presentation_does_not_use_document_bytes_or_unsafe_rendering() -> None:
    path = UI_ROOT / "presentation.py"
    source = path.read_text(encoding="utf-8")

    forbidden_fragments = (
        "UploadedFile",
        ".getvalue(",
        "unsafe_allow_html=True",
        "response.text",
        "data/private",
        "storage_key",
        "sha256",
        "Path.write_",
        "open(",
        "st.markdown(",
    )

    assert [
        fragment
        for fragment in forbidden_fragments
        if fragment in source
    ] == []


def test_entrypoint_is_thin_and_does_not_call_httpx_directly() -> None:
    path = UI_ROOT / "app.py"
    source = path.read_text(encoding="utf-8")
    imported = _imported_modules(path)

    forbidden_fragments = (
        "response.text",
        "unsafe_allow_html=True",
        "/evaluations",
        "/profiles",
        "/health",
        "httpx.",
    )

    assert "httpx" not in imported
    assert [
        fragment
        for fragment in forbidden_fragments
        if fragment in source
    ] == []



def test_upload_is_an_explicit_single_pdf_workflow() -> None:
    path = UI_ROOT / "presentation.py"
    source = path.read_text(encoding="utf-8")

    required_fragments = (
        'with st.form("document-upload"):',
        "st.file_uploader(",
        'type=["pdf"]',
        "accept_multiple_files=False",
        'st.form_submit_button("Enviar documento")',
        "key=upload_widget_key(state)",
        "execute_document_upload(",
    )

    assert [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ] == []

    forbidden_fragments = (
        ".getvalue(",
        "UploadedFile",
        "state[uploaded_file]",
        "bytes(uploaded_file)",
    )

    assert [
        fragment
        for fragment in forbidden_fragments
        if fragment in source
    ] == []



def test_streamlit_entrypoint_bootstraps_project_root() -> None:
    from pathlib import Path

    source = Path("ui/app.py").read_text(
        encoding="utf-8",
    )

    root_definition = (
        "PROJECT_ROOT = "
        "Path(__file__).resolve().parents[1]"
    )
    path_insertion = (
        "sys.path.insert(0, str(PROJECT_ROOT))"
    )
    package_import = "from ui.api_client import"

    assert root_definition in source
    assert path_insertion in source
    assert package_import in source

    assert source.index(root_definition) < source.index(
        package_import
    )
    assert source.index(path_insertion) < source.index(
        package_import
    )
