"""Integration contract for the strict Columnar multipart endpoint."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import config
from app.errors import messages
from app.errors.exceptions import FileReadError
from app.main import app
from app.services.file_processing import UTF8_BOM

FILE_PATH = "/api/columnar/file"
_UNSET = object()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _post_file(
    client: TestClient,
    *,
    filename: str = "input.txt",
    content: bytes = b"ABCDE",
    mime: str = "text/plain",
    key: object = "3 1 4 2",
    action: object = "encrypt",
    response_mode: object = "content",
    include_file: bool = True,
):
    data: dict[str, object] = {}
    if key is not _UNSET:
        data["key"] = key
    if action is not _UNSET:
        data["action"] = action
    if response_mode is not _UNSET:
        data["response_mode"] = response_mode
    files = {"file": (filename, content, mime)} if include_file else None
    return client.post(FILE_PATH, data=data, files=files)


def _assert_content(response, result: str) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "content-disposition" not in response.headers
    assert response.json() == {"success": True, "result": result}
    assert set(response.json()) == {"success", "result"}


def _assert_error(response, status: int, message: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/json")
    assert "content-disposition" not in response.headers
    assert response.json() == {"success": False, "message": message}
    assert set(response.json()) == {"success", "message"}


@pytest.mark.parametrize(
    ("content", "key", "action", "expected"),
    [
        (b"ABCDE", "3 1 4 2", "encrypt", "BDAEC"),
        (b"BDAEC", "3 1 4 2", "decrypt", "ABCDE"),
        (b"MEET ME AT NOON", "BALLOON", "encrypt", "EAM NETT EO NMO"),
        (b"EAM NETT EO NMO", "BALLOON", "decrypt", "MEET ME AT NOON"),
    ],
)
def test_columnar_file_content_matches_text_contract(
    client: TestClient,
    content: bytes,
    key: str,
    action: str,
    expected: str,
) -> None:
    _assert_content(
        _post_file(client, content=content, key=key, action=action),
        expected,
    )


def test_columnar_file_keyword_and_equivalent_numeric_key_have_parity(
    client: TestClient,
) -> None:
    keyword = _post_file(client, content=b"ABCDE", key="BACA")
    numeric = _post_file(client, content=b"ABCDE", key="3 1 4 2")
    assert keyword.json() == numeric.json()


def test_columnar_file_omitted_response_mode_defaults_to_content(client: TestClient) -> None:
    _assert_content(_post_file(client, response_mode=_UNSET), "BDAEC")


def test_columnar_file_validation_precedence_is_deterministic(client: TestClient) -> None:
    missing_file = client.post(
        FILE_PATH,
        files=[("key", (None, "bad")), ("action", (None, "bad"))],
    )
    _assert_error(missing_file, 422, messages.MISSING_FILE)
    _assert_error(
        _post_file(client, filename="bad.md", key="bad key", action="bad"),
        422,
        messages.INVALID_COLUMNAR_KEY,
    )
    _assert_error(
        _post_file(client, filename="bad.md", action="bad", response_mode="FILE"),
        422,
        messages.INVALID_ACTION,
    )
    _assert_error(
        _post_file(client, filename="bad.md", response_mode="FILE"),
        422,
        messages.INVALID_RESPONSE_MODE,
    )


def test_columnar_file_rejects_unknown_and_duplicate_fields(client: TestClient) -> None:
    unknown = client.post(
        FILE_PATH,
        files={"file": ("input.txt", b"ABCDE", "text/plain")},
        data={"key": "AB", "action": "encrypt", "extra": "x"},
    )
    duplicate = client.post(
        FILE_PATH,
        files=[
            ("file", ("input.txt", b"ABCDE", "text/plain")),
            ("key", (None, "AB")),
            ("key", (None, "BA")),
            ("action", (None, "encrypt")),
        ],
    )
    _assert_error(unknown, 422, messages.INVALID_REQUEST_BODY)
    _assert_error(duplicate, 422, messages.INVALID_REQUEST_BODY)


def test_columnar_file_requires_upload_part_and_scalar_key(client: TestClient) -> None:
    scalar_file = client.post(
        FILE_PATH,
        data={"file": "ABCDE", "key": "AB", "action": "encrypt"},
    )
    upload_key = client.post(
        FILE_PATH,
        files=[
            ("file", ("input.txt", b"ABCDE", "text/plain")),
            ("key", ("key.txt", b"AB", "text/plain")),
            ("action", (None, "encrypt")),
        ],
    )
    _assert_error(scalar_file, 422, messages.INVALID_REQUEST_BODY)
    _assert_error(upload_key, 422, messages.INVALID_STRING_KEY)


def test_columnar_file_empty_filename_uses_extension_error(client: TestClient) -> None:
    body = (
        b"--empty-name\r\n"
        b'Content-Disposition: form-data; name="file"; filename=""\r\n'
        b"Content-Type: text/plain\r\n\r\nABCDE\r\n"
        b'--empty-name\r\nContent-Disposition: form-data; name="key"\r\n\r\nAB\r\n'
        b"--empty-name\r\n"
        b'Content-Disposition: form-data; name="action"\r\n\r\nencrypt\r\n'
        b"--empty-name--\r\n"
    )
    response = client.post(
        FILE_PATH,
        content=body,
        headers={"content-type": "multipart/form-data; boundary=empty-name"},
    )
    _assert_error(response, 415, messages.UNSUPPORTED_FILE_TYPE)


@pytest.mark.parametrize("key", [_UNSET, "", " \t\r\n\f\v "])
def test_columnar_file_missing_key_variants(client: TestClient, key: object) -> None:
    _assert_error(_post_file(client, key=key), 422, messages.MISSING_KEY)


@pytest.mark.parametrize("key", ["A", "01 2", "1 1", "A B", "A" * 2049])
def test_columnar_file_invalid_key_content(client: TestClient, key: str) -> None:
    _assert_error(
        _post_file(client, filename="bad.md", key=key, action="bad"),
        422,
        messages.INVALID_COLUMNAR_KEY,
    )


@pytest.mark.parametrize("action", [_UNSET, "", "ENCRYPT", "bad"])
def test_columnar_file_action_is_required_and_case_sensitive(
    client: TestClient,
    action: object,
) -> None:
    _assert_error(_post_file(client, action=action), 422, messages.INVALID_ACTION)


@pytest.mark.parametrize("response_mode", ["", "FILE", "bad"])
def test_columnar_file_response_mode_is_case_sensitive(
    client: TestClient,
    response_mode: str,
) -> None:
    _assert_error(
        _post_file(client, response_mode=response_mode),
        422,
        messages.INVALID_RESPONSE_MODE,
    )


@pytest.mark.parametrize("filename", ["bad.md", "data.txt.exe", "readme"])
def test_columnar_file_requires_final_txt_extension(
    client: TestClient,
    filename: str,
) -> None:
    _assert_error(_post_file(client, filename=filename), 415, messages.UNSUPPORTED_FILE_TYPE)


def test_columnar_file_accepts_uppercase_txt_and_ignores_mime(client: TestClient) -> None:
    _assert_content(
        _post_file(client, filename="DATA.TXT", mime="application/octet-stream"),
        "BDAEC",
    )


def test_columnar_file_zero_byte_bom_only_and_invalid_utf8(client: TestClient) -> None:
    _assert_error(_post_file(client, content=b""), 422, messages.EMPTY_FILE)
    _assert_content(_post_file(client, content=UTF8_BOM), "")
    _assert_error(_post_file(client, content=b"\xff\xfe"), 415, messages.UNSUPPORTED_ENCODING)


def test_columnar_file_exact_five_mib_including_bom_is_accepted(client: TestClient) -> None:
    content = UTF8_BOM + b"A" * (config.MAX_FILE_BYTES - len(UTF8_BOM))
    response = _post_file(client, content=content, key="AB", response_mode="file")
    assert response.status_code == 200
    assert len(response.content) == config.MAX_FILE_BYTES
    assert response.content.startswith(UTF8_BOM)


@pytest.mark.parametrize("had_bom", [False, True])
def test_columnar_file_first_byte_over_five_mib_is_rejected(
    client: TestClient,
    had_bom: bool,
) -> None:
    prefix = UTF8_BOM if had_bom else b""
    _assert_error(
        _post_file(
            client,
            content=prefix + b"A" * (config.MAX_FILE_BYTES + 1 - len(prefix)),
            key="AB",
        ),
        413,
        messages.FILE_TOO_LARGE,
    )


def test_columnar_file_preserves_crlf_combining_non_bmp_and_nonleading_bom(
    client: TestClient,
) -> None:
    text = "A\r\nB e\u0301😀\ufeffZ"
    encrypted = _post_file(client, content=text.encode(), key="2 1 3")
    decrypted = _post_file(
        client,
        content=encrypted.json()["result"].encode(),
        key="2 1 3",
        action="decrypt",
    )
    _assert_content(decrypted, text)


@pytest.mark.parametrize("had_bom", [False, True])
def test_columnar_attachment_preserves_exact_bom_state(
    client: TestClient,
    had_bom: bool,
) -> None:
    response = _post_file(
        client,
        content=(UTF8_BOM if had_bom else b"") + b"ABCDE",
        response_mode="file",
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.content == (UTF8_BOM if had_bom else b"") + b"BDAEC"


def test_columnar_content_mode_strips_leading_bom_metadata(client: TestClient) -> None:
    _assert_content(_post_file(client, content=UTF8_BOM + b"ABCDE"), "BDAEC")


@pytest.mark.parametrize(
    ("filename", "action", "content", "expected_fragment"),
    [
        ("note.txt", "encrypt", b"ABCDE", "note.encrypted.txt"),
        ("secret.txt", "decrypt", b"BDAEC", "secret.decrypted.txt"),
        ("bao.cao.TXT", "encrypt", b"ABCDE", "bao.cao.encrypted.txt"),
        ("../nested/input.txt", "encrypt", b"ABCDE", "input.encrypted.txt"),
        (
            "dữ liệu.txt",
            "encrypt",
            b"ABCDE",
            "filename*=UTF-8''d%E1%BB%AF%20li%E1%BB%87u.encrypted.txt",
        ),
    ],
)
def test_columnar_attachment_filename_is_server_owned_and_safe(
    client: TestClient,
    filename: str,
    action: str,
    content: bytes,
    expected_fragment: str,
) -> None:
    response = _post_file(
        client,
        filename=filename,
        content=content,
        action=action,
        response_mode="file",
    )
    assert response.status_code == 200
    assert expected_fragment in response.headers["content-disposition"]
    assert "columnar" not in response.headers["content-disposition"].lower()


def test_columnar_file_mode_error_is_json_without_attachment(client: TestClient) -> None:
    _assert_error(
        _post_file(client, key="bad key", response_mode="file"),
        422,
        messages.INVALID_COLUMNAR_KEY,
    )


def test_columnar_truncated_multipart_is_rejected_before_field_validation(
    client: TestClient,
) -> None:
    response = client.post(
        FILE_PATH,
        content=(
            b'--cut\r\nContent-Disposition: form-data; name="file"; filename="input.txt"\r\n'
            b"Content-Type: text/plain\r\n\r\nABCDE"
        ),
        headers={"content-type": "multipart/form-data; boundary=cut"},
    )
    _assert_error(response, 422, messages.INVALID_REQUEST_BODY)


def test_columnar_malformed_multipart_uses_canonical_invalid_body(
    client: TestClient,
) -> None:
    response = client.post(
        FILE_PATH,
        content=b"not multipart",
        headers={"content-type": "multipart/form-data; boundary=broken"},
    )
    _assert_error(response, 422, messages.INVALID_REQUEST_BODY)


def test_columnar_file_openapi_is_exact(client: TestClient) -> None:
    operation = client.get("/openapi.json").json()["paths"][FILE_PATH]["post"]
    schema = operation["requestBody"]["content"]["multipart/form-data"]["schema"]
    assert operation["tags"] == ["Columnar Transposition"]
    assert set(schema["required"]) == {"file", "key", "action"}
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {"file", "key", "action", "response_mode"}
    assert schema["properties"]["file"]["format"] == "binary"
    key_schema = schema["properties"]["key"]
    assert key_schema["type"] == "string"
    assert key_schema["examples"] == ["3 1 4 2", "BALLOON"]
    assert "ASCII" in key_schema["description"]
    assert "2.048" in key_schema["description"]
    assert not ({"pattern", "oneOf", "maxLength"} & set(key_schema))
    assert schema["properties"]["action"]["enum"] == ["encrypt", "decrypt"]
    assert schema["properties"]["response_mode"] == {
        "type": "string",
        "enum": ["content", "file"],
        "default": "content",
    }
    assert set(operation["responses"]) == {"200", "413", "415", "422", "500"}
    assert set(operation["responses"]["200"]["content"]) == {
        "application/json",
        "text/plain",
    }
    for status in ("413", "415", "422", "500"):
        error_schema = operation["responses"][status]["content"]["application/json"]["schema"]
        assert set(error_schema["required"]) == {"success", "message"}
        assert set(error_schema["properties"]) == {"success", "message"}


def test_columnar_file_requests_are_stateless(client: TestClient) -> None:
    first = _post_file(client)
    _post_file(client, content=b"secret", key="BA")
    second = _post_file(client)
    assert first.json() == second.json() == {"success": True, "result": "BDAEC"}


def test_columnar_unexpected_file_failure_is_sanitized_without_payload_log(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_key = "3 1 4 2"

    def fail_after_transform(*args: object) -> bytes:
        del args
        raise RuntimeError("technical attachment failure")

    monkeypatch.setattr("app.api.routes_columnar_file.build_attachment_body", fail_after_transform)
    caplog.set_level("ERROR", logger="app.errors.handlers")
    response = _post_file(
        client,
        content=b"PRIVATE-ABCDE",
        key=raw_key,
        response_mode="file",
    )
    _assert_error(response, 500, messages.UNEXPECTED_FAILURE)
    assert "RuntimeError" in caplog.text
    assert "PRIVATE-ABCDE" not in caplog.text
    assert "RTBV-DPAAEIEC" not in caplog.text
    assert raw_key not in caplog.text


def test_columnar_file_read_failure_uses_canonical_safe_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def fail_read(reader: object) -> bytes:
        del reader
        raise FileReadError()

    monkeypatch.setattr("app.api.routes_columnar_file.read_limited_bytes", fail_read)
    caplog.set_level("ERROR", logger="app.errors.handlers")
    response = _post_file(client, content=b"private-content", response_mode="file")
    _assert_error(response, 500, messages.FILE_READ_FAILURE)
    assert "FileReadError" in caplog.text
    assert "private-content" not in caplog.text
