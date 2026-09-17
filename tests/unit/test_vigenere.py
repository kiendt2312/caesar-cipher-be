"""Contract tests for the pure repeating-key Vigenere core."""

from __future__ import annotations

import pytest

from app.core.vigenere import normalize_key, transform_text


def test_acceptance_vector_encrypts_and_decrypts() -> None:
    encrypted = transform_text("Attack at dawn!", "LEMON", "encrypt")

    assert encrypted == "Lxfopv ef rnhr!"
    assert transform_text(encrypted, "LEMON", "decrypt") == "Attack at dawn!"


def test_lowercase_and_uppercase_keys_are_equivalent() -> None:
    assert normalize_key("lemon") == "LEMON"
    assert transform_text("Attack", "lemon", "encrypt") == transform_text(
        "Attack", "LEMON", "encrypt"
    )


def test_repeating_key_wraps_for_longer_input() -> None:
    assert transform_text("AAAAAA", "ABC", "encrypt") == "ABCABC"


@pytest.mark.parametrize(
    "text, key, expected",
    [
        pytest.param("A-A", "BC", "B-C", id="punctuation"),
        pytest.param("AéA", "BC", "BéC", id="unicode"),
        pytest.param("A\r\nA", "BC", "B\r\nC", id="crlf"),
        pytest.param("a-A", "BC", "b-C", id="case"),
    ],
)
def test_non_ascii_letters_do_not_advance_key_and_case_is_preserved(
    text: str, key: str, expected: str
) -> None:
    assert transform_text(text, key, "encrypt") == expected


@pytest.mark.parametrize("key", ["", "LE MON", "KEY1", "KHÓA", "🔑"])
def test_invalid_keys_are_rejected_without_silent_normalization(key: str) -> None:
    with pytest.raises(ValueError, match="ASCII letters"):
        normalize_key(key)


@pytest.mark.parametrize("operation", ["ENCRYPT", "decrypt ", "rot13", "", None])
def test_invalid_operation_is_rejected(operation: object) -> None:
    with pytest.raises(ValueError, match="operation"):
        transform_text("ABC", "KEY", operation)  # type: ignore[arg-type]


def test_repeated_calls_are_deterministic_and_stateless() -> None:
    expected = "Lxfopv ef rnhr!"
    for _ in range(5):
        assert transform_text("Attack at dawn!", "LEMON", "encrypt") == expected

    transform_text("AAAAAA", "ABC", "encrypt")
    assert transform_text("Attack at dawn!", "LEMON", "encrypt") == expected
