"""Integration coverage for all 47 file-cipher-api scenarios."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api import routes_file
from app.errors import messages
from app.errors.exceptions import FileReadError
from app.main import app

FILE_PATH = "/api/caesar/file"
_UNSET = object()

# Explicit inventory in the same order as file-cipher-api/spec.md.
FILE_CIPHER_API_SCENARIOS = (
    "01 Yêu cầu hợp lệ đầy đủ trường",
    "02 Bỏ qua response_mode thì mặc định là content",
    "03 Giải mã nội dung file",
    "04 Key âm và key lớn hơn 25 trên luồng file",
    "05 Mode content trả JSON preview",
    "06 Mode content loại BOM khỏi result",
    "07 Mode file trả attachment text/plain",
    "08 Tên file kết quả khi mã hóa",
    "09 Tên file kết quả khi giải mã",
    "10 Đuôi gốc viết hoa được chuẩn hóa về .txt thường",
    "11 Tên gốc có nhiều dấu chấm",
    "12 Chấp nhận mọi biến thể hoa thường của đuôi txt",
    "13 Từ chối file có đuôi khác",
    "14 Từ chối file có đuôi kép nguy hiểm",
    "15 Từ chối file không có đuôi",
    "16 File đúng 5 MiB được chấp nhận",
    "17 File 5 MiB cộng 1 byte bị từ chối",
    "18 Chấp nhận UTF-8 thường",
    "19 Chấp nhận UTF-8 có BOM",
    "20 Từ chối file không decode được bằng UTF-8",
    "21 File đầu vào có BOM thì file tải xuống giữ BOM",
    "22 File đầu vào không có BOM thì kết quả không thêm BOM",
    "23 Thiếu trường file",
    "24 File 0 byte",
    "25 File chỉ chứa whitespace vẫn hợp lệ",
    "26 Thiếu key",
    "27 Key là chuỗi rỗng",
    "28 Key là chữ",
    "29 Key là số thực",
    "30 Key âm có dấu được chấp nhận",
    "31 Action không hợp lệ",
    "32 Response mode không hợp lệ",
    "33 Key sai định dạng được báo trước lỗi đuôi file và dung lượng",
    "34 Lỗi đuôi file được báo trước lỗi dung lượng",
    "35 Lỗi dung lượng được báo trước lỗi bảng mã",
    "36 Response mode sai định dạng được báo trước lỗi file 0 byte",
    "37 Không đọc được luồng dữ liệu của file",
    "38 Lỗi đuôi file trong mode file vẫn trả JSON",
    "39 Lỗi dung lượng trong mode file vẫn trả JSON",
    "40 Lỗi khóa trong mode file vẫn trả JSON",
    "41 Giữ nguyên xuống dòng và số dòng",
    "42 Giữ nguyên tiếng Việt và ký tự đặc biệt",
    "43 Giữ nguyên ký tự kết thúc dòng CRLF",
    "44 Không tự thêm CR vào file dùng LF",
    "45 Mã hóa rồi giải mã cùng khóa khôi phục nội dung gốc",
    "46 Không còn dấu vết sau khi request kết thúc",
    "47 Các request độc lập với nhau",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _post_file(
    client: TestClient,
    *,
    filename: str = "input.txt",
    content: bytes = b"Hello World",
    key: str | None = "3",
    action: str | None = "encrypt",
    response_mode: str | object | None = _UNSET,
    include_file: bool = True,
    include_key: bool = True,
    include_action: bool = True,
) -> object:
    data: dict[str, str] = {}
    if include_key:
        data["key"] = "" if key is None else key
    if include_action:
        data["action"] = "" if action is None else action
    if response_mode is not _UNSET:
        data["response_mode"] = "" if response_mode is None else str(response_mode)

    files = {}
    if include_file:
        files["file"] = (filename, content, "text/plain")
    return client.post(FILE_PATH, data=data, files=files)


def _assert_content_success(response: object, expected: str) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "content-disposition" not in response.headers
    body = response.json()
    assert body == {"success": True, "result": expected}
    assert set(body) == {"success", "result"}


def _assert_attachment_success(response: object, expected: bytes, filename: str) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.content == expected
    assert response.headers["content-disposition"] == f'attachment; filename="{filename}"'


def _assert_error(response: object, status_code: int, message: str) -> None:
    assert response.status_code == status_code
    assert response.headers["content-type"].startswith("application/json")
    assert "content-disposition" not in response.headers
    body = response.json()
    assert body == {"success": False, "message": message}
    assert set(body) == {"success", "message"}
    assert "detail" not in body


def test_file_api_scenario_inventory_is_complete() -> None:
    assert len(FILE_CIPHER_API_SCENARIOS) == 47
    assert [scenario[:2] for scenario in FILE_CIPHER_API_SCENARIOS] == [
        f"{number:02d}" for number in range(1, 48)
    ]


def test_file_endpoint_openapi_describes_both_success_modes(client: TestClient) -> None:
    operation = client.get("/openapi.json").json()["paths"][FILE_PATH]["post"]
    request_schema_ref = operation["requestBody"]["content"]["multipart/form-data"]["schema"][
        "$ref"
    ]
    request_schema = client.get("/openapi.json").json()["components"]["schemas"][
        request_schema_ref.rsplit("/", 1)[-1]
    ]

    assert set(operation["responses"]["200"]["content"]) == {
        "application/json",
        "text/plain",
    }
    assert request_schema["properties"]["response_mode"]["default"] == "content"
    assert set(operation["responses"]["422"]["content"]) == {"application/json"}


def test_malformed_multipart_body_uses_canonical_unreadable_body_contract(
    client: TestClient,
) -> None:
    response = client.post(
        FILE_PATH,
        content=b"not a valid multipart body",
        headers={"content-type": "multipart/form-data; boundary=expected-boundary"},
    )

    _assert_error(response, 422, messages.INVALID_REQUEST_BODY)


@pytest.mark.parametrize(
    "body",
    [
        (
            b"--truncated\r\n"
            b'Content-Disposition: form-data; name="file"; filename="input.txt"\r\n'
            b"Content-Type: text/plain\r\n\r\n"
            b"Hello World\r\n"
            b"--truncated\r\n"
            b'Content-Disposition: form-data; name="key"\r\n\r\n3\r\n'
            b"--truncated\r\n"
            b'Content-Disposition: form-data; name="action"\r\n\r\nencrypt\r\n'
            b"--truncated\r\n"
            b'Content-Disposition: form-data; name="response_mode"\r\n\r\ncontent\r\n'
        ),
        b'--truncated\r\nContent-Disposition: form-data; name="key"\r\n\r\n3',
    ],
)
def test_truncated_multipart_body_fails_before_field_validation(
    client: TestClient,
    body: bytes,
) -> None:
    response = client.post(
        FILE_PATH,
        content=body,
        headers={"content-type": "multipart/form-data; boundary=truncated"},
    )

    _assert_error(response, 422, messages.INVALID_REQUEST_BODY)


def test_field_value_suffix_cannot_impersonate_multipart_closing_boundary(
    client: TestClient,
) -> None:
    body = (
        b"--suffix\r\n"
        b'Content-Disposition: form-data; name="file"; filename="input.txt"\r\n'
        b"Content-Type: text/plain\r\n\r\n"
        b"Hello\r\n"
        b"--suffix\r\n"
        b'Content-Disposition: form-data; name="key"\r\n\r\n3\r\n'
        b"--suffix\r\n"
        b'Content-Disposition: form-data; name="action"\r\n\r\nencrypt\r\n'
        b"--suffix\r\n"
        b'Content-Disposition: form-data; name="response_mode"\r\n\r\n'
        b"content--suffix--"
    )
    response = client.post(
        FILE_PATH,
        content=body,
        headers={"content-type": "multipart/form-data; boundary=suffix"},
    )

    _assert_error(response, 422, messages.INVALID_REQUEST_BODY)


# Scenario 01: all multipart fields produce the exact content success envelope.
def test_file_valid_request_with_all_fields(client: TestClient) -> None:
    _assert_content_success(_post_file(client), "Khoor Zruog")


# Scenario 02: an omitted optional response_mode selects content JSON.
def test_file_missing_response_mode_defaults_to_content(client: TestClient) -> None:
    _assert_content_success(_post_file(client, response_mode=_UNSET), "Khoor Zruog")


# Scenario 03: file action decrypts the supplied ciphertext.
def test_file_decrypts_content(client: TestClient) -> None:
    _assert_content_success(
        _post_file(client, content=b"Khoor Zruog", action="decrypt"),
        "Hello World",
    )


# Scenario 04: equivalent negative and greater-than-25 keys work on the file route.
def test_file_accepts_negative_and_large_keys(client: TestClient) -> None:
    negative = _post_file(client, key="-23")
    large = _post_file(client, key="29")

    _assert_content_success(negative, "Khoor Zruog")
    _assert_content_success(large, "Khoor Zruog")


# Scenario 05: content mode is JSON and has no download header.
def test_file_content_mode_returns_json_preview(client: TestClient) -> None:
    _assert_content_success(
        _post_file(client, response_mode="content"),
        "Khoor Zruog",
    )


# Scenario 06: a leading BOM is not part of the content preview.
def test_file_content_mode_strips_bom(client: TestClient) -> None:
    _assert_content_success(
        _post_file(client, content=b"\xef\xbb\xbfHello"),
        "Khoor",
    )


# Scenario 07: file mode returns one fully-buffered text attachment.
def test_file_mode_returns_text_attachment(client: TestClient) -> None:
    response = _post_file(client, filename="ghi-chu.txt", response_mode="file")

    _assert_attachment_success(response, b"Khoor Zruog", "ghi-chu.encrypted.txt")


# Scenario 08: encryption names use a dot before encrypted.
def test_file_encryption_result_filename(client: TestClient) -> None:
    response = _post_file(client, filename="ghi-chu.txt", response_mode="file")

    assert response.headers["content-disposition"] == (
        'attachment; filename="ghi-chu.encrypted.txt"'
    )
    assert "ghi-chu_encrypted.txt" not in response.headers["content-disposition"]


# Scenario 09: decryption names use the decrypted suffix.
def test_file_decryption_result_filename(client: TestClient) -> None:
    response = _post_file(
        client,
        filename="ghi-chu.txt",
        content=b"Khoor Zruog",
        action="decrypt",
        response_mode="file",
    )

    assert response.headers["content-disposition"] == (
        'attachment; filename="ghi-chu.decrypted.txt"'
    )


# Scenario 10: an uppercase source extension yields a lowercase output extension.
def test_file_uppercase_extension_result_filename(client: TestClient) -> None:
    response = _post_file(client, filename="BaoCao.TXT", response_mode="file")

    assert response.headers["content-disposition"] == (
        'attachment; filename="BaoCao.encrypted.txt"'
    )


# Scenario 11: only the final .txt is removed from a multi-dot source name.
def test_file_multiple_dot_result_filename(client: TestClient) -> None:
    response = _post_file(client, filename="bao.cao.v2.txt", response_mode="file")

    assert response.headers["content-disposition"] == (
        'attachment; filename="bao.cao.v2.encrypted.txt"'
    )


# Scenario 12: .txt extension matching is case-insensitive.
@pytest.mark.parametrize("filename", ["a.txt", "a.TXT", "a.Txt"])
def test_file_accepts_case_variants_of_txt(client: TestClient, filename: str) -> None:
    _assert_content_success(_post_file(client, filename=filename), "Khoor Zruog")


# Scenarios 13-15: non-final or missing .txt extensions are unsupported.
@pytest.mark.parametrize("filename", ["a.md", "a.txt.exe", "readme"])
def test_file_rejects_non_txt_names(client: TestClient, filename: str) -> None:
    _assert_error(
        _post_file(client, filename=filename),
        415,
        messages.UNSUPPORTED_FILE_TYPE,
    )


# Scenario 16: exactly five MiB is accepted (payload is generated in memory only).
def test_file_exactly_five_mib_is_accepted(client: TestClient, exact_limit_bytes: bytes) -> None:
    response = _post_file(
        client,
        filename="limit.txt",
        content=exact_limit_bytes,
        response_mode="file",
    )

    _assert_attachment_success(
        response,
        b"D" * config.MAX_FILE_BYTES,
        "limit.encrypted.txt",
    )


# Scenario 17: the first byte beyond five MiB is rejected.
def test_file_five_mib_plus_one_is_rejected(client: TestClient, over_limit_bytes: bytes) -> None:
    _assert_error(
        _post_file(client, content=over_limit_bytes),
        413,
        messages.FILE_TOO_LARGE,
    )


# Scenario 18: ordinary UTF-8 content passes through and transforms ASCII letters only.
def test_file_accepts_utf8_without_bom(client: TestClient) -> None:
    _assert_content_success(_post_file(client, content="Xin chào".encode()), "Alq fkàr")


# Scenario 19: UTF-8 with BOM is accepted as text content.
def test_file_accepts_utf8_with_bom(client: TestClient) -> None:
    _assert_content_success(_post_file(client, content=b"\xef\xbb\xbfHello"), "Khoor")


# Scenario 20: invalid UTF-8 is rejected with the encoding contract.
def test_file_rejects_invalid_utf8(client: TestClient) -> None:
    _assert_error(
        _post_file(client, content=b"latin-1: \xff"),
        415,
        messages.UNSUPPORTED_ENCODING,
    )


# Scenario 21: an attachment preserves a leading input BOM byte-for-byte.
def test_file_attachment_preserves_input_bom(client: TestClient) -> None:
    response = _post_file(client, content=b"\xef\xbb\xbfHello", response_mode="file")

    assert response.content[:3] == b"\xef\xbb\xbf"
    assert response.content[3:] == b"Khoor"


# Scenario 22: an attachment does not invent a BOM for BOM-less input.
def test_file_attachment_does_not_add_bom(client: TestClient) -> None:
    response = _post_file(client, content=b"Hello", response_mode="file")

    assert not response.content.startswith(b"\xef\xbb\xbf")


# Scenario 23: file presence is checked before the other multipart fields.
def test_file_missing_file(client: TestClient) -> None:
    _assert_error(
        _post_file(client, include_file=False),
        422,
        messages.MISSING_FILE,
    )


# Scenario 24: a zero-byte file is distinct from whitespace content.
def test_file_zero_bytes_are_rejected(client: TestClient) -> None:
    _assert_error(
        _post_file(client, filename="rong.txt", content=b""),
        422,
        messages.EMPTY_FILE,
    )


# Scenario 25: whitespace-only bytes are valid and preserved.
def test_file_whitespace_only_content_is_valid(client: TestClient) -> None:
    content = b" \t\n\r\n"
    response = _post_file(client, content=content, response_mode="file")

    _assert_attachment_success(response, content, "input.encrypted.txt")


# Scenario 26: a missing key gets the missing-key message.
def test_file_missing_key(client: TestClient) -> None:
    _assert_error(
        _post_file(client, include_key=False),
        422,
        messages.MISSING_KEY,
    )


# Scenario 27: an explicitly empty key is still missing, not malformed.
def test_file_empty_key_is_missing(client: TestClient) -> None:
    _assert_error(
        _post_file(client, key=""),
        422,
        messages.MISSING_KEY,
    )


# Scenarios 28-29: present malformed scalar keys are invalid.
@pytest.mark.parametrize("key", ["abc", "3.5"])
def test_file_invalid_key_forms(client: TestClient, key: str) -> None:
    _assert_error(_post_file(client, key=key), 422, messages.INVALID_KEY)


# Scenario 30: a signed negative multipart key is accepted.
def test_file_negative_key_is_accepted(client: TestClient) -> None:
    _assert_content_success(_post_file(client, key="-3"), "Ebiil Tloia")


# Scenario 31: action values are exact and case-sensitive; empty is invalid too.
@pytest.mark.parametrize("action", ["ENCRYPT", "ma-hoa", ""])
def test_file_rejects_invalid_action(client: TestClient, action: str) -> None:
    _assert_error(_post_file(client, action=action), 422, messages.INVALID_ACTION)


def test_file_missing_action_uses_invalid_action_message(client: TestClient) -> None:
    _assert_error(
        _post_file(client, include_action=False),
        422,
        messages.INVALID_ACTION,
    )


# Scenario 32: response_mode values are exact and case-sensitive.
@pytest.mark.parametrize("response_mode", ["", "download", "json", "CONTENT"])
def test_file_rejects_invalid_response_mode(client: TestClient, response_mode: str) -> None:
    _assert_error(
        _post_file(client, response_mode=response_mode),
        422,
        messages.INVALID_RESPONSE_MODE,
    )


# Scenario 33: invalid key wins over both extension and size errors.
def test_file_invalid_key_precedes_extension_and_size(
    client: TestClient,
    over_limit_bytes: bytes,
) -> None:
    _assert_error(
        _post_file(client, filename="a.md", content=over_limit_bytes, key="abc"),
        422,
        messages.INVALID_KEY,
    )


# Scenario 34: extension validation wins over size validation.
def test_file_extension_precedes_size(client: TestClient, over_limit_bytes: bytes) -> None:
    _assert_error(
        _post_file(client, filename="a.md", content=over_limit_bytes),
        415,
        messages.UNSUPPORTED_FILE_TYPE,
    )


# Scenario 35: size validation wins over UTF-8 decoding.
def test_file_size_precedes_encoding(client: TestClient) -> None:
    _assert_error(
        _post_file(client, content=b"\xff" * (config.MAX_FILE_BYTES + 1)),
        413,
        messages.FILE_TOO_LARGE,
    )


# Scenario 36: response-mode format is checked before a zero-byte file.
def test_file_response_mode_precedes_empty_file(client: TestClient) -> None:
    _assert_error(
        _post_file(client, content=b"", response_mode="download"),
        422,
        messages.INVALID_RESPONSE_MODE,
    )


# Scenario 37: a technical read failure becomes a safe JSON 500.
def test_file_read_failure_is_canonical_json(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def fail_read(reader: object) -> bytes:
        del reader
        raise FileReadError()

    monkeypatch.setattr(routes_file, "read_limited_bytes", fail_read)
    caplog.set_level("ERROR", logger="app.errors.handlers")
    response = _post_file(client)

    _assert_error(response, 500, messages.FILE_READ_FAILURE)
    assert "FileReadError" not in response.text
    assert "Traceback" not in response.text
    assert "FileReadError" in caplog.text
    assert "Traceback (most recent call last)" in caplog.text
    assert "method=POST" in caplog.text
    assert f"path={FILE_PATH}" in caplog.text
    assert "time=" in caplog.text
    assert "Hello World" not in caplog.text


# Scenario 38: extension errors stay JSON even when file mode was requested.
def test_file_extension_error_in_file_mode_is_json(client: TestClient) -> None:
    _assert_error(
        _post_file(client, filename="a.md", response_mode="file"),
        415,
        messages.UNSUPPORTED_FILE_TYPE,
    )


# Scenario 39: size errors stay JSON even when file mode was requested.
def test_file_size_error_in_file_mode_is_json(
    client: TestClient,
    over_limit_bytes: bytes,
) -> None:
    _assert_error(
        _post_file(client, content=over_limit_bytes, response_mode="file"),
        413,
        messages.FILE_TOO_LARGE,
    )


# Scenario 40: key errors stay JSON even when file mode was requested.
def test_file_key_error_in_file_mode_is_json(client: TestClient) -> None:
    _assert_error(
        _post_file(client, key="abc", response_mode="file"),
        422,
        messages.INVALID_KEY,
    )


# Scenario 41: line structure survives a file transformation.
def test_file_preserves_line_count_and_positions(client: TestClient) -> None:
    original = b"abc\r\ndef\r\nghi"
    response = _post_file(client, content=original, response_mode="file")

    _assert_attachment_success(response, b"def\r\nghi\r\njkl", "input.encrypted.txt")


# Scenario 42: Vietnamese, digits, and punctuation survive unchanged around ASCII letters.
def test_file_preserves_vietnamese_digits_and_special_characters(client: TestClient) -> None:
    _assert_content_success(
        _post_file(client, content="Xin chào ABC 123 !@#".encode()),
        "Alq fkàr DEF 123 !@#",
    )


# Scenario 43: CRLF bytes remain CRLF in the downloaded result.
def test_file_preserves_crlf_bytes(client: TestClient) -> None:
    original = b"abc\r\ndef\r\n"
    response = _post_file(client, content=original, response_mode="file")

    assert response.content == b"def\r\nghi\r\n"
    assert response.content.count(b"\r\n") == original.count(b"\r\n")
    assert response.content.count(b"\r") == original.count(b"\r")
    assert response.content.count(b"\n") == original.count(b"\n")


# Scenario 44: LF-only input does not gain carriage returns.
def test_file_does_not_add_cr_to_lf_only_input(client: TestClient) -> None:
    original = b"abc\ndef\n"
    response = _post_file(client, content=original, response_mode="file")

    assert response.content == b"def\nghi\n"
    assert response.content.count(b"\r") == original.count(b"\r") == 0


# Scenario 45: encrypting and then decrypting through the file endpoint is a round-trip.
def test_file_encrypt_then_decrypt_round_trip(client: TestClient) -> None:
    original = "Xin chào thế giới\r\n2026!"
    encrypted = _post_file(client, content=original.encode(), key="7")
    _assert_content_success(encrypted, "Epu joàv aoế npớp\r\n2026!")

    decrypted = _post_file(
        client,
        content=encrypted.json()["result"].encode(),
        key="7",
        action="decrypt",
    )
    _assert_content_success(decrypted, original)


# Scenario 46: the route does not expose a retrieval endpoint or persist result state.
def test_file_request_leaves_no_retrievable_result(client: TestClient) -> None:
    response = _post_file(client, content=b"private file payload")
    _assert_content_success(response, "sulydwh iloh sdbordg")

    retrieval = client.get(FILE_PATH)
    assert retrieval.status_code == 405
    assert "result" not in retrieval.json()
    assert "private file payload" not in retrieval.text


# Scenario 47: consecutive requests use only their own input and key.
def test_file_requests_are_independent(client: TestClient) -> None:
    first = _post_file(client, content=b"abc", key="1")
    second = _post_file(client, content=b"xyz", key="2")

    _assert_content_success(first, "bcd")
    _assert_content_success(second, "zab")
