"""Static and rendered guards for the approved same-origin web UI."""

from pathlib import Path

from fastapi.testclient import TestClient

from app import config
from app.main import app

ROOT = Path(__file__).parents[2]
SCRIPT = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")


def test_root_renders_ui_with_server_injected_file_limit() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert f'data-max-bytes="{config.MAX_FILE_BYTES}"' in response.text
    assert 'lang="vi"' in response.text
    assert "/static/styles.css" in response.text
    assert "/static/app.js" in response.text


def test_static_assets_are_served_by_the_application() -> None:
    with TestClient(app) as client:
        script = client.get("/static/app.js")
        styles = client.get("/static/styles.css")

    assert script.status_code == 200
    assert script.headers["content-type"].startswith("text/javascript")
    assert styles.status_code == 200
    assert styles.headers["content-type"].startswith("text/css")


def test_script_has_no_mock_cross_origin_or_embedded_business_limit() -> None:
    forbidden = (
        "mockApi",
        "USE_MOCK",
        "API_BASE",
        "localhost:8080",
        str(config.MAX_FILE_BYTES),
        "1024 * 1024;",
        "1 MB",
    )
    assert all(token not in SCRIPT for token in forbidden)
    assert "document.body.dataset.maxBytes" in SCRIPT
    assert "fetchWithTimeout(`/api/caesar/${operation}`" in SCRIPT
    assert 'fetchWithTimeout("/api/caesar/file"' in SCRIPT


def test_only_shift_table_contains_client_side_caesar_mapping() -> None:
    assert "function shiftAlphabet" in SCRIPT
    assert "charCodeAt" in SCRIPT  # Highlighting and analysis only.
    assert "String.fromCharCode" not in SCRIPT
    assert ".encrypt(" not in SCRIPT
    assert ".decrypt(" not in SCRIPT


def test_file_flow_requests_both_preview_and_download_modes() -> None:
    assert '"response_mode", responseMode' in SCRIPT
    assert 'state.file, key, "content"' in SCRIPT
    assert 'elements.keyInput.value.trim(),\n        "file"' in SCRIPT
    assert "response.blob()" in SCRIPT
    assert "content-disposition" in SCRIPT


def test_ui_keeps_required_controls_and_vietnamese_labels() -> None:
    for label in (
        "Sao chép",
        "Xóa",
        "Đổi file",
        "Gỡ file",
        "Tải kết quả",
        "Tạo ví dụ",
        "Làm mới",
        "Phân tích",
        "Mã hóa",
        "Giải mã",
    ):
        assert label in TEMPLATE
    assert "5 MiB" in TEMPLATE


def test_ui_has_no_out_of_scope_navigation_or_mock_notes() -> None:
    forbidden = ("CAESAR.IO", "Share feedback", "Report issue", "backend giả lập")
    combined = f"{TEMPLATE}\n{SCRIPT}"
    assert all(token not in combined for token in forbidden)
    assert "<nav" not in TEMPLATE
    assert "<footer" not in TEMPLATE


def test_ui_supports_whitespace_plus_keys_download_and_full_locking() -> None:
    assert "if (text.length === 0)" in SCRIPT
    assert "^[+-]?[0-9]+$" in SCRIPT
    assert "ket-qua.encrypted.txt" in SCRIPT
    assert "ket-qua.decrypted.txt" in SCRIPT
    assert 'querySelectorAll("[data-lockable]")' in SCRIPT
    assert "control.disabled = state.loading" in SCRIPT
    assert "elements.dropZone.tabIndex = state.loading ? -1 : 0" in SCRIPT
    assert (
        'elements.dropZone.addEventListener("click", (event) => {\n  if (state.loading) return;'
    ) in SCRIPT
    assert (
        'elements.dropZone.addEventListener("keydown", (event) => {\n'
        '  if (event.key === "Enter" || event.key === " ") {\n'
        "    event.preventDefault();\n"
        "    if (state.loading) return;"
    ) in SCRIPT


def test_real_api_distinguishes_server_errors_from_network_failures() -> None:
    assert 'response.headers.get("content-type")' in SCRIPT
    assert "response.ok" in SCRIPT
    assert "error.isApiError" in SCRIPT
    assert "Lỗi kết nối" in SCRIPT
    assert "catch {}" not in SCRIPT


def test_ui_resets_result_tab_times_out_requests_and_ignores_stale_file_reads() -> None:
    clear_result = SCRIPT.split("function clearResult", 1)[1].split("function render", 1)[0]
    render = SCRIPT.split("function render", 1)[1].split("function selectMode", 1)[0]
    assert 'state.view = "result"' in clear_result
    assert "tab.dataset.view === state.view" in render
    assert "new AbortController()" in SCRIPT
    assert "controller.abort()" in SCRIPT
    assert "window.clearTimeout(timeout)" in SCRIPT
    assert "fileReadVersion !== state.fileReadVersion || state.file !== file" in SCRIPT
