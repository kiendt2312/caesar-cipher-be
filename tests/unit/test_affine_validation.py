"""Deterministic request validation tests for the Affine adapters."""

from __future__ import annotations

from io import BytesIO

import pytest
from starlette.datastructures import FormData, UploadFile

from app.api.schemas import (
    decode_affine_text_request,
    validate_affine_file_form,
    validate_affine_text_request,
)
from app.errors.exceptions import (
    EmptyTextError,
    InvalidActionError,
    InvalidAffineMultiplierError,
    InvalidAffineShiftError,
    InvalidRequestBodyError,
    InvalidResponseModeError,
    MissingAffineMultiplierError,
    MissingAffineShiftError,
    MissingFileError,
    NonInvertibleAffineMultiplierError,
)


def _decode(raw: bytes):
    return decode_affine_text_request(raw, "application/json")


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"not-json",
        b"[]",
        b"null",
        b'{"text":"HELLO","a":5,"b":8,"analysis":true}',
        b'{"text":"HELLO","a":5,"a":7,"b":8}',
    ],
)
def test_affine_decoder_requires_an_exact_json_object(raw: bytes) -> None:
    with pytest.raises(InvalidRequestBodyError):
        _decode(raw)


@pytest.mark.parametrize("content_type", [None, "text/plain", "multipart/form-data"])
def test_affine_decoder_requires_a_json_media_type(content_type: str | None) -> None:
    with pytest.raises(InvalidRequestBodyError):
        decode_affine_text_request(b'{"text":"HELLO","a":5,"b":8}', content_type)


def test_affine_decoder_retains_missing_members_for_ordered_validation() -> None:
    payload = _decode(b"{}")

    with pytest.raises(EmptyTextError):
        validate_affine_text_request(payload)


@pytest.mark.parametrize("raw", [b'{"a":5,"b":8}', b'{"text":null,"a":5,"b":8}'])
def test_affine_text_validation_precedes_both_keys(raw: bytes) -> None:
    with pytest.raises(EmptyTextError):
        validate_affine_text_request(_decode(raw))


@pytest.mark.parametrize("raw", [b'{"text":"HELLO","b":8}', b'{"text":"HELLO","a":null,"b":8}'])
def test_missing_affine_multiplier_is_distinct_from_wrong_type(raw: bytes) -> None:
    with pytest.raises(MissingAffineMultiplierError):
        validate_affine_text_request(_decode(raw))


@pytest.mark.parametrize(
    "value",
    [b'"5"', b"5.0", b"true", b"false", b"[]", b"{}", b'""'],
)
def test_affine_multiplier_requires_a_true_json_integer(value: bytes) -> None:
    raw = b'{"text":"HELLO","a":' + value + b',"b":8}'

    with pytest.raises(InvalidAffineMultiplierError):
        validate_affine_text_request(_decode(raw))


def test_affine_multiplier_invertibility_precedes_shift_validation() -> None:
    payload = _decode(b'{"text":"HELLO","a":2}')

    with pytest.raises(NonInvertibleAffineMultiplierError):
        validate_affine_text_request(payload)


@pytest.mark.parametrize("raw", [b'{"text":"HELLO","a":5}', b'{"text":"HELLO","a":5,"b":null}'])
def test_missing_affine_shift_is_distinct_from_wrong_type(raw: bytes) -> None:
    with pytest.raises(MissingAffineShiftError):
        validate_affine_text_request(_decode(raw))


@pytest.mark.parametrize(
    "value",
    [b'"8"', b"8.0", b"true", b"false", b"[]", b"{}", b'""'],
)
def test_affine_shift_requires_a_true_json_integer(value: bytes) -> None:
    raw = b'{"text":"HELLO","a":5,"b":' + value + b"}"

    with pytest.raises(InvalidAffineShiftError):
        validate_affine_text_request(_decode(raw))


def test_affine_large_integer_tokens_reduce_without_python_int_conversion() -> None:
    multiplier = b"26" + b"0" * 5000 + b"5"
    shift = b"26" + b"0" * 5000 + b"8"
    raw = b'{"text":"HELLO","a":' + multiplier + b',"b":' + shift + b"}"

    assert validate_affine_text_request(_decode(raw)) == ("HELLO", 5, 8)


def test_affine_outside_javascript_safe_range_preserves_exact_residues() -> None:
    payload = _decode(b'{"text":"HELLO","a":9007199254741017,"b":9007199254740994}')

    assert validate_affine_text_request(payload) == ("HELLO", 5, 8)


def test_existing_caesar_decoder_still_ignores_additional_members() -> None:
    from app.api.schemas import decode_text_request, validate_text_request

    payload = decode_text_request(
        b'{"text":"abc","key":1,"existing_behavior":true}', "application/json"
    )

    assert validate_text_request(payload) == ("abc", 1)


def _upload(filename: str = "input.txt") -> UploadFile:
    return UploadFile(BytesIO(b"HELLO"), filename=filename)


def _form(*items: tuple[str, object]) -> FormData:
    return FormData(items)


def test_affine_file_form_accepts_exact_fields_and_defaults_content() -> None:
    upload = _upload()
    form = _form(("file", upload), ("a", "  +5  "), ("b", " -18 "), ("action", "encrypt"))

    assert validate_affine_file_form(form) == (upload, 5, 8, "encrypt", "content")


@pytest.mark.parametrize(
    "form",
    [
        _form(("file", _upload()), ("a", "5"), ("b", "8"), ("action", "encrypt"), ("x", "1")),
        _form(
            ("file", _upload()),
            ("a", "5"),
            ("a", "7"),
            ("b", "8"),
            ("action", "encrypt"),
        ),
    ],
)
def test_affine_file_form_rejects_unknown_or_duplicate_fields(form: FormData) -> None:
    with pytest.raises(InvalidRequestBodyError):
        validate_affine_file_form(form)


@pytest.mark.parametrize("file_value", [None, "HELLO"])
def test_affine_file_form_validates_file_before_keys(file_value: object | None) -> None:
    items = [("a", ""), ("b", ""), ("action", "bad")]
    if file_value is not None:
        items.insert(0, ("file", file_value))

    expected = MissingFileError if file_value is None else InvalidRequestBodyError
    with pytest.raises(expected):
        validate_affine_file_form(_form(*items))


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_affine_file_form_maps_blank_a_to_missing(raw: str | None) -> None:
    form = _form(("file", _upload()), ("a", raw), ("b", "bad"), ("action", "bad"))

    with pytest.raises(MissingAffineMultiplierError):
        validate_affine_file_form(form)


@pytest.mark.parametrize("raw", ["5.0", "1e3", "٣", "9" * 33])
def test_affine_file_form_rejects_invalid_a_before_b_and_action(raw: str) -> None:
    form = _form(("file", _upload()), ("a", raw), ("b", "bad"), ("action", "bad"))

    with pytest.raises(InvalidAffineMultiplierError):
        validate_affine_file_form(form)


def test_affine_file_form_rejects_noninvertible_a_before_b_and_action() -> None:
    form = _form(("file", _upload("bad.md")), ("a", "2"), ("action", "bad"))

    with pytest.raises(NonInvertibleAffineMultiplierError):
        validate_affine_file_form(form)


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_affine_file_form_maps_blank_b_to_missing(raw: str | None) -> None:
    form = _form(("file", _upload()), ("a", "5"), ("b", raw), ("action", "bad"))

    with pytest.raises(MissingAffineShiftError):
        validate_affine_file_form(form)


@pytest.mark.parametrize("raw", ["8.0", "1e3", "٣", "9" * 33])
def test_affine_file_form_rejects_invalid_b_before_action(raw: str) -> None:
    form = _form(("file", _upload()), ("a", "5"), ("b", raw), ("action", "bad"))

    with pytest.raises(InvalidAffineShiftError):
        validate_affine_file_form(form)


def test_affine_file_form_accepts_32_character_keys() -> None:
    upload = _upload()
    form = _form(
        ("file", upload),
        ("a", "+0000000000000000000000000000005"),
        ("b", "+0000000000000000000000000000008"),
        ("action", "decrypt"),
        ("response_mode", "file"),
    )

    assert validate_affine_file_form(form) == (upload, 5, 8, "decrypt", "file")


def test_affine_file_form_checks_action_before_response_mode() -> None:
    form = _form(
        ("file", _upload()),
        ("a", "5"),
        ("b", "8"),
        ("action", "ENCRYPT"),
        ("response_mode", "FILE"),
    )

    with pytest.raises(InvalidActionError):
        validate_affine_file_form(form)


def test_affine_file_form_rejects_invalid_response_mode_last() -> None:
    form = _form(
        ("file", _upload()),
        ("a", "5"),
        ("b", "8"),
        ("action", "encrypt"),
        ("response_mode", "FILE"),
    )

    with pytest.raises(InvalidResponseModeError):
        validate_affine_file_form(form)
