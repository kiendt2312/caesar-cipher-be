"""Deterministic validation tests for the Columnar adapters."""

from __future__ import annotations

from io import BytesIO

import pytest
from starlette.datastructures import FormData, UploadFile

from app.api.schemas import (
    decode_columnar_text_request,
    validate_columnar_file_form,
    validate_columnar_text_request,
)
from app.errors import messages
from app.errors.exceptions import (
    EmptyTextError,
    InvalidActionError,
    InvalidColumnarKeyError,
    InvalidRequestBodyError,
    InvalidResponseModeError,
    InvalidStringKeyError,
    MissingFileError,
    MissingKeyError,
)


def _decode(raw: bytes, content_type: str | None = "application/json"):
    return decode_columnar_text_request(raw, content_type)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"not-json",
        b"[]",
        b"null",
        b'"text"',
        b'{"text":"ABCDE","key":"3 1 4 2","extra":true}',
        b'{"text":"ABCDE","text":"FGHIJ","key":"3 1 4 2"}',
        b'{"text":"ABCDE","key":"3 1 4 2","key":"AB"}',
    ],
)
def test_columnar_decoder_requires_one_exact_json_object(raw: bytes) -> None:
    with pytest.raises(InvalidRequestBodyError):
        _decode(raw)


@pytest.mark.parametrize("content_type", [None, "text/plain", "multipart/form-data"])
def test_columnar_decoder_rejects_non_json_media_types(content_type: str | None) -> None:
    with pytest.raises(InvalidRequestBodyError):
        _decode(b'{"text":"ABCDE","key":"3 1 4 2"}', content_type)


@pytest.mark.parametrize(
    "content_type",
    ["application/json", "application/json; charset=utf-8", "application/vnd.example+json"],
)
def test_columnar_decoder_accepts_json_and_vendor_json(content_type: str) -> None:
    payload = _decode(b'{"text":"ABCDE","key":"3 1 4 2"}', content_type)
    assert validate_columnar_text_request(payload) == ("ABCDE", (3, 1, 4, 2))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"text":"\\ud83d","key":"AB"}',
        b'{"text":"\\ude00","key":"AB"}',
        b'{"text":"\\ude00\\ud83d","key":"AB"}',
        b'{"text":"ABCDE","key":"\\ud83d"}',
        b'{"\\ud83d":"ABCDE","text":"ABCDE","key":"AB"}',
    ],
)
def test_columnar_decoder_rejects_every_residual_json_surrogate(raw: bytes) -> None:
    with pytest.raises(InvalidRequestBodyError):
        _decode(raw)


def test_columnar_decoder_accepts_valid_surrogate_pair_as_one_code_point() -> None:
    payload = _decode(b'{"text":"\\ud83d\\ude00A","key":"AB"}')

    text, ranks = validate_columnar_text_request(payload)

    assert text == "😀A"
    assert len(text) == 2
    assert ranks == (1, 2)


@pytest.mark.parametrize(
    "raw",
    [
        b"{}",
        b'{"key":"AB"}',
        b'{"text":null,"key":"AB"}',
        b'{"text":"","key":"AB"}',
        b'{"text":123,"key":"AB"}',
        b'{"text":[],"key":"AB"}',
    ],
)
def test_columnar_text_validation_precedes_key_validation(raw: bytes) -> None:
    with pytest.raises(EmptyTextError):
        validate_columnar_text_request(_decode(raw))


def test_columnar_whitespace_text_is_not_trimmed() -> None:
    payload = _decode(b'{"text":" \\t\\r\\n","key":"2 1"}')
    assert validate_columnar_text_request(payload) == (" \t\r\n", (2, 1))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"text":"ABCDE"}',
        b'{"text":"ABCDE","key":null}',
        b'{"text":"ABCDE","key":""}',
        b'{"text":"ABCDE","key":" \\t\\r\\n\\f\\u000b "}',
    ],
)
def test_columnar_missing_key_variants_precede_type_and_content(raw: bytes) -> None:
    with pytest.raises(MissingKeyError):
        validate_columnar_text_request(_decode(raw))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"text":"ABCDE","key":123}',
        b'{"text":"ABCDE","key":true}',
        b'{"text":"ABCDE","key":[]}',
        b'{"text":"ABCDE","key":{}}',
    ],
)
def test_columnar_json_key_requires_a_string_without_coercion(raw: bytes) -> None:
    with pytest.raises(InvalidStringKeyError):
        validate_columnar_text_request(_decode(raw))


@pytest.mark.parametrize("key", ["312", "1 1", "A B", "\u00a0AB\u00a0", "A" * 2049])
def test_columnar_key_content_uses_one_canonical_domain_error(key: str) -> None:
    payload = _decode((f'{{"text":"ABCDE","key":"{key}"}}').encode())

    with pytest.raises(InvalidColumnarKeyError) as exc_info:
        validate_columnar_text_request(payload)

    assert exc_info.value.message == messages.INVALID_COLUMNAR_KEY
    assert key not in str(exc_info.value)


def test_existing_string_key_decoder_keeps_legacy_extra_field_behavior() -> None:
    from app.api.schemas import decode_string_key_request, validate_additional_text_request

    payload = decode_string_key_request(
        b'{"text":"ABC","key":"KEY","existing_behavior":true}',
        "application/json",
    )
    assert validate_additional_text_request(payload, "vigenere", "encrypt") == ("ABC", "KEY")


def _upload(filename: str = "input.txt", content: bytes = b"ABCDE") -> UploadFile:
    return UploadFile(BytesIO(content), filename=filename)


def _form(*items: tuple[str, object]) -> FormData:
    return FormData(items)


def test_columnar_file_form_accepts_exact_fields_and_defaults_content() -> None:
    upload = _upload()
    form = _form(("file", upload), ("key", " \tBALLOON\r\n"), ("action", "encrypt"))

    assert validate_columnar_file_form(form) == (
        upload,
        (2, 1, 3, 4, 6, 7, 5),
        "encrypt",
        "content",
    )


@pytest.mark.parametrize(
    "form",
    [
        _form(("file", _upload()), ("key", "AB"), ("action", "encrypt"), ("x", "1")),
        _form(
            ("file", _upload()),
            ("key", "AB"),
            ("key", "BA"),
            ("action", "encrypt"),
        ),
    ],
)
def test_columnar_file_form_rejects_unknown_or_duplicate_fields(form: FormData) -> None:
    with pytest.raises(InvalidRequestBodyError):
        validate_columnar_file_form(form)


@pytest.mark.parametrize("file_value", [None, "ABCDE"])
def test_columnar_file_form_checks_file_before_key(file_value: object | None) -> None:
    items: list[tuple[str, object]] = [("key", ""), ("action", "bad")]
    if file_value is not None:
        items.insert(0, ("file", file_value))

    expected = MissingFileError if file_value is None else InvalidRequestBodyError
    with pytest.raises(expected):
        validate_columnar_file_form(_form(*items))


@pytest.mark.parametrize("key", [None, "", " \t\r\n\f\v "])
def test_columnar_file_form_maps_blank_key_to_missing(key: str | None) -> None:
    form = _form(("file", _upload("bad.md")), ("key", key), ("action", "bad"))
    with pytest.raises(MissingKeyError):
        validate_columnar_file_form(form)


def test_columnar_file_form_rejects_key_upload_as_wrong_type() -> None:
    form = _form(("file", _upload()), ("key", _upload("key.txt")), ("action", "encrypt"))
    with pytest.raises(InvalidStringKeyError):
        validate_columnar_file_form(form)


def test_columnar_file_form_checks_key_content_before_action_and_mode() -> None:
    form = _form(
        ("file", _upload("bad.md")),
        ("key", "1 1"),
        ("action", "bad"),
        ("response_mode", "FILE"),
    )
    with pytest.raises(InvalidColumnarKeyError):
        validate_columnar_file_form(form)


def test_columnar_file_form_checks_action_before_response_mode() -> None:
    form = _form(
        ("file", _upload()),
        ("key", "AB"),
        ("action", "ENCRYPT"),
        ("response_mode", "FILE"),
    )
    with pytest.raises(InvalidActionError):
        validate_columnar_file_form(form)


def test_columnar_file_form_rejects_response_mode_last() -> None:
    form = _form(
        ("file", _upload()),
        ("key", "AB"),
        ("action", "encrypt"),
        ("response_mode", "FILE"),
    )
    with pytest.raises(InvalidResponseModeError):
        validate_columnar_file_form(form)
