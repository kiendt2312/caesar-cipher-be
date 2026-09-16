"""Unit coverage for the multipart key grammar."""

from __future__ import annotations

import pytest

from app.api.schemas import MULTIPART_KEY_MAX_LENGTH, parse_multipart_key
from app.errors import messages
from app.errors.exceptions import InvalidKeyError, MissingKeyError


# Scenario 6.1: strip, signs, leading zeroes, and negative zero are accepted.
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("3", 3, id="plain"),
        pytest.param(" 3 ", 3, id="surrounding-whitespace"),
        pytest.param("+3", 3, id="plus-sign"),
        pytest.param("03", 3, id="leading-zero"),
        pytest.param("-0", 0, id="negative-zero"),
        pytest.param("-3", -3, id="negative"),
    ],
)
def test_parse_multipart_key_accepts_decimal_integer_forms(raw: str, expected: int) -> None:
    assert parse_multipart_key(raw) == expected


# Scenario 6.1: grammar uses ASCII digits and rejects ambiguous numeric spellings.
@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("3.0", id="decimal-point"),
        pytest.param("1e3", id="scientific-notation"),
        pytest.param("1_000", id="underscore"),
        pytest.param("٣", id="arabic-indic-digit"),
        pytest.param("abc", id="letters"),
        pytest.param("--3", id="double-sign"),
        pytest.param("9" * 5000, id="pathological-length"),
    ],
)
def test_parse_multipart_key_rejects_non_ascii_or_non_decimal_forms(raw: str) -> None:
    with pytest.raises(InvalidKeyError, match=messages.INVALID_KEY):
        parse_multipart_key(raw)


def test_parse_multipart_key_accepts_the_32_character_boundary() -> None:
    raw = "9" * MULTIPART_KEY_MAX_LENGTH

    assert parse_multipart_key(raw) == int(raw)


def test_parse_multipart_key_rejects_one_character_over_the_limit() -> None:
    raw = "9" * (MULTIPART_KEY_MAX_LENGTH + 1)

    with pytest.raises(InvalidKeyError, match=messages.INVALID_KEY):
        parse_multipart_key(raw)


# Scenario 6.1 and file-cipher-api key presence scenarios: None/blank are missing, not malformed.
@pytest.mark.parametrize(
    "raw",
    [pytest.param(None, id="none"), pytest.param("", id="empty"), pytest.param("   ", id="spaces")],
)
def test_parse_multipart_key_maps_blank_values_to_missing(raw: str | None) -> None:
    with pytest.raises(MissingKeyError, match=messages.MISSING_KEY):
        parse_multipart_key(raw)


def test_parse_multipart_key_rejects_non_string_values_without_500() -> None:
    with pytest.raises(InvalidKeyError, match=messages.INVALID_KEY):
        parse_multipart_key(3.5)
