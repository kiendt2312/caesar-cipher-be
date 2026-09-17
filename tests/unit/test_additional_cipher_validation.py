"""Deterministic validation tests for Vigenere and Playfair adapters."""

from __future__ import annotations

import json

import pytest

from app.api.schemas import (
    MISSING,
    decode_string_key_request,
    validate_additional_file_form_fields,
    validate_additional_text_request,
    validate_playfair_content,
)
from app.errors.exceptions import (
    DuplicatePlayfairDigraphError,
    EmptyPlayfairTextError,
    EmptyTextError,
    InvalidActionError,
    InvalidPlayfairKeyError,
    InvalidRequestBodyError,
    InvalidResponseModeError,
    InvalidStringKeyError,
    InvalidVigenereKeyError,
    MissingKeyError,
    OddPlayfairCiphertextError,
)


def _decode(payload: bytes):
    return decode_string_key_request(payload, "application/json")


@pytest.mark.parametrize("raw", [b"", b"not-json", b"[]", b"null", b'"text"'])
def test_string_key_json_parser_requires_a_json_object(raw: bytes) -> None:
    with pytest.raises(InvalidRequestBodyError):
        _decode(raw)


@pytest.mark.parametrize("cipher", ["vigenere", "playfair"])
def test_text_presence_precedes_key_validation(cipher: str) -> None:
    payload = _decode(b'{"text":"","key":123}')

    with pytest.raises(EmptyTextError):
        validate_additional_text_request(payload, cipher, "encrypt")


@pytest.mark.parametrize(
    "raw", [b'{"text":"abc"}', b'{"text":"abc","key":null}', b'{"text":"abc","key":""}']
)
def test_missing_string_key_variants_are_distinct_from_wrong_type(raw: bytes) -> None:
    with pytest.raises(MissingKeyError):
        validate_additional_text_request(_decode(raw), "vigenere", "encrypt")


@pytest.mark.parametrize("key", [123, True, 1.5, [], {}])
def test_present_non_string_key_is_rejected_without_coercion(key: object) -> None:
    payload = _decode((f'{{"text":"abc","key":{json.dumps(key)}}}').encode())

    with pytest.raises(InvalidStringKeyError):
        validate_additional_text_request(payload, "vigenere", "encrypt")


def test_arbitrarily_large_json_integer_key_is_rejected_as_wrong_type() -> None:
    raw = ('{"text":"abc","key":' + "1" * 5000 + "}").encode()

    with pytest.raises(InvalidStringKeyError):
        validate_additional_text_request(_decode(raw), "vigenere", "encrypt")


@pytest.mark.parametrize("key", ["LE MON", "KEY1", "KHÓA", " "])
def test_vigenere_key_must_be_ascii_letters_only(key: str) -> None:
    payload = _decode((f'{{"text":"abc","key":"{key}"}}').encode())

    with pytest.raises(InvalidVigenereKeyError):
        validate_additional_text_request(payload, "vigenere", "encrypt")


def test_playfair_key_validation_precedes_normalized_text_validation() -> None:
    payload = _decode(b'{"text":"123","key":"---"}')

    with pytest.raises(InvalidPlayfairKeyError):
        validate_additional_text_request(payload, "playfair", "encrypt")


@pytest.mark.parametrize(
    ("text", "operation", "error"),
    [
        ("123 — ộ", "encrypt", EmptyPlayfairTextError),
        ("ABC", "decrypt", OddPlayfairCiphertextError),
        ("AABC", "decrypt", DuplicatePlayfairDigraphError),
    ],
)
def test_playfair_content_validation_maps_each_contract_error(
    text: str, operation: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        validate_playfair_content(text, operation)


def test_vigenere_whitespace_text_is_valid_but_playfair_is_not() -> None:
    vigenere = _decode(b'{"text":"   ","key":"KEY"}')
    playfair = _decode(b'{"text":"   ","key":"KEY"}')

    assert validate_additional_text_request(vigenere, "vigenere", "encrypt") == ("   ", "KEY")
    with pytest.raises(EmptyPlayfairTextError):
        validate_additional_text_request(playfair, "playfair", "encrypt")


def test_file_field_precedence_checks_presence_before_key_format() -> None:
    with pytest.raises(InvalidActionError):
        validate_additional_file_form_fields("KEY 1", MISSING, MISSING, "vigenere")

    with pytest.raises(InvalidVigenereKeyError):
        validate_additional_file_form_fields("KEY 1", "encrypt", MISSING, "vigenere")


def test_file_field_validation_defaults_content_and_rejects_invalid_mode() -> None:
    assert validate_additional_file_form_fields(
        "PLAYFAIR EXAMPLE", "decrypt", MISSING, "playfair"
    ) == ("PLAYFAIR EXAMPLE", "decrypt", "content")

    with pytest.raises(InvalidResponseModeError):
        validate_additional_file_form_fields("KEY", "encrypt", "FILE", "vigenere")
